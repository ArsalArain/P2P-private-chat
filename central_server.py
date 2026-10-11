import base64
import hashlib
import hmac
import os
import secrets
import socket
import threading
import time

from base import Base
from hash_function import (
    PASSWORD_ITERATIONS,
    build_login_proof,
    constant_time_equal,
    password_key_from_hash,
    parse_password_hash,
)
from persistence import (
    add_new_user,
    get_all_users,
    get_user_password,
    initialize_database,
    update_user_address_port,
)


MAX_USERNAME_LENGTH = 32
MAX_PORT = 55535
LOGIN_CHALLENGE_TTL = 60
MAX_LOGIN_FAILURES = 5
LOGIN_FAILURE_WINDOW = 60
LOGIN_BLOCK_TIME = 60
MAX_PENDING_LOGINS = 1_000
MAX_REGISTERED_USERS = 10_000
FAKE_SALT_BYTES = 16
FAKE_SALT_SECRET = os.environ.get(
    "P2P_LOGIN_FAKE_SALT_SECRET",
).encode("utf-8") if os.environ.get("P2P_LOGIN_FAKE_SALT_SECRET") else secrets.token_bytes(32)


class CentralServer(Base):
    def __init__(self, serverhost="0.0.0.0", serverport=40000):
        initialize_database()
        super().__init__(serverhost, serverport)

        self.peerlist = set(get_all_users())
        self.onlinelist = {}
        self.sessions = {}
        self.pending_logins = {}
        self.login_failures = {}
        self.state_lock = threading.RLock()

        handlers = {
            "PEER_REGISTER": self.peer_register,
            "PEER_LOGIN": self.peer_login,
            "PEER_LOGIN_RESPONSE": self.peer_login_response,
            "PEER_LIST": self.peer_list,
            "PEER_LOGOUT": self.peer_logout,
            "PUBLIC_CHAT": self.peer_broadcast_chat,
        }
        for msgtype, function in handlers.items():
            self.add_handler(msgtype, function)

    @staticmethod
    def _valid_username(username):
        return (
            isinstance(username, str)
            and 1 <= len(username.strip()) <= MAX_USERNAME_LENGTH
            and username.strip() == username
            and username.isascii()
            and all(character.isalnum() or character in "._-" for character in username)
        )

    @staticmethod
    def _valid_port(port):
        return isinstance(port, int) and 1 <= port <= MAX_PORT

    @staticmethod
    def _reply_host(address):
        return address[0] if address else None

    def _send_reply(self, address, port, msgtype, msgdata):
        if not self._reply_host(address) or not self._valid_port(port):
            print(f"Cannot send {msgtype}: invalid peer address")
            return
        try:
            self.client_send((self._reply_host(address), port), msgtype, msgdata)
        except OSError as error:
            print(f"Could not send {msgtype} to {address[0]}:{port}: {error}")

    def peer_register(self, msgdata, address):
        peer_name = msgdata.get("peername")
        peer_port = msgdata.get("port")
        password_verifier = msgdata.get("password_verifier")

        if (
            not self._valid_username(peer_name)
            or not self._valid_port(peer_port)
            or not is_password_hash(password_verifier)
        ):
            self._send_reply(address, peer_port, "REGISTER_ERROR", {"reason": "invalid_input"})
            return

        with self.state_lock:
            if peer_name in self.peerlist:
                self._send_reply(address, peer_port, "REGISTER_ERROR", {"reason": "username_exists"})
                return
            if len(self.peerlist) >= MAX_REGISTERED_USERS:
                self._send_reply(address, peer_port, "REGISTER_ERROR", {"reason": "registration_unavailable"})
                return

            if not add_new_user(peer_name, password_verifier):
                self._send_reply(address, peer_port, "REGISTER_ERROR", {"reason": "username_exists"})
                return
            self.peerlist.add(peer_name)

        self._send_reply(address, peer_port, "REGISTER_SUCCESS", {})
        print(f"{peer_name} has been added to the central server's managed user list")

    def peer_login(self, msgdata, address):
        peer_name = msgdata.get("peername")
        peer_port = msgdata.get("port")
        if not self._valid_username(peer_name) or not self._valid_port(peer_port):
            self._send_reply(address, peer_port, "LOGIN_ERROR", {"reason": "invalid_credentials"})
            return

        failure_key = (self._reply_host(address), peer_name)
        now = time.monotonic()
        with self.state_lock:
            failure = self.login_failures.get(failure_key)
            if failure and failure["blocked_until"] > now:
                self._send_reply(address, peer_port, "LOGIN_ERROR", {"reason": "invalid_credentials"})
                return
            if failure and failure["window_started"] + LOGIN_FAILURE_WINDOW <= now:
                self.login_failures.pop(failure_key, None)

        stored_password = get_user_password(peer_name)
        nonce = secrets.token_urlsafe(32)
        parsed = parse_password_hash(stored_password) if stored_password else None
        challenge_salt = hmac.new(
            FAKE_SALT_SECRET,
            peer_name.encode("ascii"),
            hashlib.sha256,
        ).digest()[:FAKE_SALT_BYTES]
        challenge_iterations = PASSWORD_ITERATIONS
        if parsed:
            _, challenge_iterations, challenge_salt, _ = parsed
        challenge = {
            "username": peer_name,
            "host": self._reply_host(address),
            "port": peer_port,
            "stored_password": stored_password,
            "expires_at": time.monotonic() + LOGIN_CHALLENGE_TTL,
        }
        with self.state_lock:
            now = time.monotonic()
            self.pending_logins = {
                key: value
                for key, value in self.pending_logins.items()
                if value["expires_at"] >= now
            }
            if len(self.pending_logins) >= MAX_PENDING_LOGINS:
                self._send_reply(address, peer_port, "LOGIN_ERROR", {"reason": "temporarily_unavailable"})
                return
            self.pending_logins[nonce] = challenge

        challenge_data = {
            "nonce": nonce,
            "algorithm": "pbkdf2_sha256",
            "iterations": challenge_iterations,
            "salt": base64.b64encode(challenge_salt).decode("ascii"),
        }
        self._send_reply(address, peer_port, "LOGIN_CHALLENGE", challenge_data)

    def peer_login_response(self, msgdata, address):
        nonce = msgdata.get("nonce")
        peer_name = msgdata.get("peername")
        peer_port = msgdata.get("port")
        proof = msgdata.get("proof")
        with self.state_lock:
            challenge = self.pending_logins.pop(nonce, None)

        valid = (
            challenge is not None
            and challenge["expires_at"] >= time.monotonic()
            and challenge["username"] == peer_name
            and challenge["host"] == self._reply_host(address)
            and challenge["port"] == peer_port
            and isinstance(proof, str)
        )

        stored_password = challenge["stored_password"] if challenge else None
        key = password_key_from_hash(stored_password) if stored_password else None

        if valid and stored_password and key is not None:
            expected = build_login_proof(key, nonce)
            valid = constant_time_equal(expected, proof)

        if not valid:
            self._record_login_failure((self._reply_host(address), peer_name))
            self._send_reply(address, peer_port, "LOGIN_ERROR", {"reason": "invalid_credentials"})
            print(f"{peer_name!r} has been refused for login")
            return

        token = secrets.token_urlsafe(32)
        with self.state_lock:
            self.login_failures.pop((self._reply_host(address), peer_name), None)
            for old_token, session in list(self.sessions.items()):
                if session["username"] == peer_name:
                    del self.sessions[old_token]
            self.sessions[token] = {
                "username": peer_name,
                "host": self._reply_host(address),
                "port": peer_port,
            }
            self.onlinelist[peer_name] = (self._reply_host(address), peer_port)

        update_user_address_port(peer_name, self._reply_host(address), peer_port)
        self._send_reply(address, peer_port, "LOGIN_SUCCESS", {"token": token})
        print(f"{peer_name} has been added to the central server's online user list")

    def _record_login_failure(self, failure_key):
        now = time.monotonic()
        with self.state_lock:
            failure = self.login_failures.get(failure_key)
            if failure is None or failure["window_started"] + LOGIN_FAILURE_WINDOW <= now:
                failure = {"count": 0, "window_started": now, "blocked_until": 0}
                self.login_failures[failure_key] = failure
            failure["count"] += 1
            if failure["count"] >= MAX_LOGIN_FAILURES:
                failure["blocked_until"] = now + LOGIN_BLOCK_TIME

    def _authenticated_session(self, msgdata, address):
        token = msgdata.get("token")
        peer_name = msgdata.get("peername")
        with self.state_lock:
            session = self.sessions.get(token)
            if (
                session is None
                or session["username"] != peer_name
                or session["host"] != self._reply_host(address)
            ):
                return None
            return session

    def peer_list(self, msgdata, address):
        session = self._authenticated_session(msgdata, address)
        if session is None:
            self._send_reply(address, msgdata.get("port"), "LOGIN_ERROR", {"reason": "session_expired"})
            return

        with self.state_lock:
            online_users = dict(self.onlinelist)
        self._send_reply(address, session["port"], "LIST_ONLINE_USER", {"online_user_list": online_users})

    def peer_logout(self, msgdata, address):
        session = self._authenticated_session(msgdata, address)
        if session is None:
            return

        token = msgdata["token"]
        with self.state_lock:
            self.sessions.pop(token, None)
            if self.onlinelist.get(session["username"]) == (session["host"], session["port"]):
                self.onlinelist.pop(session["username"], None)
        print(f"{session['username']} has been removed from the central server's online user list")

    def peer_broadcast_chat(self, msgdata, address):
        session = self._authenticated_session(msgdata, address)
        message = msgdata.get("message")
        if session is None or not isinstance(message, str) or not message.strip() or len(message) > 4096:
            return

        with self.state_lock:
            recipients = list(self.onlinelist.values())
        broadcast = {"name": session["username"], "message": message}
        for recipient in recipients:
            try:
                self.client_send(recipient, "CHAT_PUBLIC", broadcast)
            except OSError as error:
                print(f"Could not broadcast public message to {recipient}: {error}")
        print("Message has been broadcasted to all online users")


if __name__ == "__main__":
    CentralServer().input_recv()
