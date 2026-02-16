"""加密工具模块：提供基于 AES-256-GCM 的加解密能力。"""

from __future__ import annotations

import os
from typing import Tuple

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def _derive_key(password: str, salt: bytes) -> bytes:
    """基于口令和盐派生 32 字节对称密钥。"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=390000,
        backend=default_backend(),
    )
    return kdf.derive(password.encode())


def encrypt(data: bytes, password: str) -> Tuple[bytes, bytes, bytes]:
    """使用 AES-256-GCM 加密，返回 (salt, iv, payload)。"""
    salt = os.urandom(16)
    iv = os.urandom(12)
    key = _derive_key(password, salt)
    encryptor = Cipher(
        algorithms.AES(key), modes.GCM(iv), backend=default_backend()
    ).encryptor()
    ciphertext = encryptor.update(data) + encryptor.finalize()
    return salt, iv, encryptor.tag + ciphertext


def decrypt(salt: bytes, iv: bytes, payload: bytes, password: str) -> bytes:
    """解密由 encrypt 生成的密文载荷。"""
    tag, ciphertext = payload[:16], payload[16:]
    key = _derive_key(password, salt)
    decryptor = Cipher(
        algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend()
    ).decryptor()
    return decryptor.update(ciphertext) + decryptor.finalize()
