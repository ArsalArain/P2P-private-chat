import inspect
import json
import socket
import struct
import threading
from abc import abstractmethod


FORMAT = "utf-8"
MAX_MESSAGE_SIZE = 1024 * 1024
MESSAGE_HEADER_SIZE = 4


class Base:
    def __init__(self, serverhost="localhost", serverport=10000, listen_num=100):
        self.serverhost = socket.gethostbyname(serverhost)
        self.serverport = int(serverport)

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.serverhost, self.serverport))
        self.socket.listen(listen_num)

        self.peerlist = {}
        self.handlers = {}

    def add_handler(self, msgtype, function):
        accepts_address = len(inspect.signature(function).parameters) >= 2
        self.handlers[msgtype] = (function, accepts_address)

    def function_mapper(self, message, address=None):
        msgtype = message.get("msgtype")
        handler_info = self.handlers.get(msgtype)
        if handler_info is None:
            raise ValueError(f"Unknown message type: {msgtype!r}")

        function, accepts_address = handler_info
        if accepts_address:
            function(message.get("msgdata", {}), address)
        else:
            function(message.get("msgdata", {}))

    @staticmethod
    def recv_exact(conn, size):
        chunks = bytearray()
        while len(chunks) < size:
            chunk = conn.recv(size - len(chunks))
            if not chunk:
                raise ConnectionError("Connection closed before the message was complete")
            chunks.extend(chunk)
        return bytes(chunks)

    @classmethod
    def send_frame(cls, conn, payload):
        if len(payload) > MAX_MESSAGE_SIZE:
            raise ValueError("Message exceeds the maximum allowed size")
        conn.sendall(struct.pack("!I", len(payload)) + payload)

    @classmethod
    def recv_frame(cls, conn):
        length = struct.unpack("!I", cls.recv_exact(conn, MESSAGE_HEADER_SIZE))[0]
        if length > MAX_MESSAGE_SIZE:
            raise ValueError("Message exceeds the maximum allowed size")
        return cls.recv_exact(conn, length)

    @classmethod
    def send_json(cls, conn, message):
        cls.send_frame(conn, json.dumps(message).encode(FORMAT))

    @classmethod
    def recv_json(cls, conn):
        payload = cls.recv_frame(conn)
        return json.loads(payload.decode(FORMAT))

    def recv_input_stream(self, conn, address):
        try:
            conn.settimeout(10)
            message = self.recv_json(conn)
            if not isinstance(message, dict):
                raise ValueError("Message must be a JSON object")
            self.function_mapper(message, address)
        except Exception as error:
            print(f"Protocol error from {address}: {error}")
        finally:
            conn.close()

    def input_recv(self):
        while True:
            conn, address = self.socket.accept()
            input_stream = threading.Thread(
                target=self.recv_input_stream,
                args=(conn, address),
                daemon=True,
            )
            input_stream.start()

    @abstractmethod
    def run(self):
        pass

    @classmethod
    def client_send(cls, address, msgtype, msgdata):
        message = {"msgtype": msgtype, "msgdata": msgdata}
        with socket.create_connection(address, timeout=5) as connection:
            cls.send_json(connection, message)
