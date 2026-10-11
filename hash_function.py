import base64
import hashlib
import hmac
import os


PASSWORD_ALGORITHM = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 600_000
MAX_PASSWORD_ITERATIONS = 1_000_000
PASSWORD_SALT_BYTES = 16


def _encode(value):
    return base64.b64encode(value).decode("ascii")


def _decode(value):
    return base64.b64decode(value.encode("ascii"), validate=True)


def derive_password_key(password, salt, iterations=PASSWORD_ITERATIONS):
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
        dklen=32,
    )


def hash_password(password):
    salt = os.urandom(PASSWORD_SALT_BYTES)
    digest = derive_password_key(password, salt)
    return f"{PASSWORD_ALGORITHM}${PASSWORD_ITERATIONS}${_encode(salt)}${_encode(digest)}"


def parse_password_hash(encoded):
    try:
        algorithm, iterations, salt, digest = encoded.split("$")
        if algorithm != PASSWORD_ALGORITHM:
            return None
        iterations = int(iterations)
        salt = _decode(salt)
        digest = _decode(digest)
    except (AttributeError, ValueError, UnicodeError):
        return None

    if (
        iterations < 100_000
        or iterations > MAX_PASSWORD_ITERATIONS
        or not salt
        or not digest
        or len(digest) != 32
    ):
        return None
    return algorithm, iterations, salt, digest


def password_key_from_hash(encoded):
    parsed = parse_password_hash(encoded)
    if parsed is None:
        return None
    _, _, _, digest = parsed
    return digest


def is_password_hash(encoded):
    return parse_password_hash(encoded) is not None


def build_login_proof(key, nonce):
    return hmac.new(key, nonce.encode("ascii"), hashlib.sha256).hexdigest()


def constant_time_equal(left, right):
    return hmac.compare_digest(str(left), str(right))
