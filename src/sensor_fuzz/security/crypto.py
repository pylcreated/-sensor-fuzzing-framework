"""加密工具模块：提供基于 AES-256-GCM 的加解密能力。"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from typing import Tuple

try:
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    _HAS_CRYPTOGRAPHY = True
except Exception:  # pragma: no cover - optional dependency path
    default_backend = None
    hashes = None
    Cipher = None
    algorithms = None
    modes = None
    PBKDF2HMAC = None
    _HAS_CRYPTOGRAPHY = False


def _derive_key(password: str, salt: bytes) -> bytes:
    """基于口令和盐派生 32 字节对称密钥。"""
    if _HAS_CRYPTOGRAPHY:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=390000,
            backend=default_backend(),
        )
        return kdf.derive(password.encode())

    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 390000, dklen=32)


def _expand_key_stream(key: bytes, iv: bytes, data_length: int) -> bytes:
    blocks = []
    block_index = 0
    while sum(len(block) for block in blocks) < data_length:
        counter = block_index.to_bytes(8, "big")
        blocks.append(hashlib.sha256(key + iv + counter).digest())
        block_index += 1
    return b"".join(blocks)[:data_length]


def _encrypt_bytes(data: bytes, password: str) -> Tuple[bytes, bytes, bytes]:
    salt = os.urandom(16)
    iv = os.urandom(12)
    key = _derive_key(password, salt)

    if _HAS_CRYPTOGRAPHY:
        encryptor = Cipher(
            algorithms.AES(key), modes.GCM(iv), backend=default_backend()
        ).encryptor()
        ciphertext = encryptor.update(data) + encryptor.finalize()
        return salt, iv, encryptor.tag + ciphertext

    key_stream = _expand_key_stream(key, iv, len(data))
    ciphertext = bytes(d ^ key_stream[idx] for idx, d in enumerate(data))
    tag = hmac.new(key, iv + ciphertext, hashlib.sha256).digest()[:16]
    return salt, iv, tag + ciphertext


def _decrypt_bytes(salt: bytes, iv: bytes, payload: bytes, password: str) -> bytes:
    tag, ciphertext = payload[:16], payload[16:]
    key = _derive_key(password, salt)

    if _HAS_CRYPTOGRAPHY:
        decryptor = Cipher(
            algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend()
        ).decryptor()
        return decryptor.update(ciphertext) + decryptor.finalize()

    expected_tag = hmac.new(key, iv + ciphertext, hashlib.sha256).digest()[:16]
    if not hmac.compare_digest(tag, expected_tag):
        raise ValueError("Invalid authentication tag")
    key_stream = _expand_key_stream(key, iv, len(ciphertext))
    return bytes(c ^ key_stream[idx] for idx, c in enumerate(ciphertext))


def encrypt(data: bytes | str, password: str) -> Tuple[bytes, bytes, bytes] | str:
    """加密数据；bytes 输入返回三元组，str 输入返回可传输 token。"""
    if isinstance(data, str):
        encoded_data = data.encode("utf-8")
        salt, iv, payload = _encrypt_bytes(encoded_data, password)
        packed = salt + iv + payload
        return base64.urlsafe_b64encode(packed).decode("ascii")

    return _encrypt_bytes(data, password)


def decrypt(*args):
    """解密数据；支持 decrypt(token, password) 与 decrypt(salt, iv, payload, password)。"""
    if len(args) == 2:
        token, password = args
        packed = base64.urlsafe_b64decode(token.encode("ascii"))
        salt = packed[:16]
        iv = packed[16:28]
        payload = packed[28:]
        return _decrypt_bytes(salt, iv, payload, password).decode("utf-8")

    if len(args) == 4:
        salt, iv, payload, password = args
        return _decrypt_bytes(salt, iv, payload, password)

    raise TypeError("decrypt expects (token, password) or (salt, iv, payload, password)")
