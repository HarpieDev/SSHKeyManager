"""Clés OpenSSH : passphrases uniquement en mémoire, jamais dans un processus."""
import base64
import hashlib
import struct

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa


def load_private(data: bytes, passphrase: str = ""):
    password = passphrase.encode("utf-8") if passphrase else None
    loader = serialization.load_ssh_private_key if b"BEGIN OPENSSH PRIVATE KEY" in data else serialization.load_pem_private_key
    try:
        return loader(data, password=password)
    except TypeError:
        if password:
            return loader(data, password=None)
        raise ValueError("Passphrase requise pour cette clé.") from None
    except ValueError:
        raise ValueError("Clé privée invalide ou passphrase incorrecte.") from None


def public_bytes(key) -> bytes:
    return key.public_key().public_bytes(serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH)


def generate(kind: str, passphrase: str) -> tuple[bytes, bytes]:
    if kind == "ed25519":
        key = ed25519.Ed25519PrivateKey.generate()
    elif kind == "rsa":
        key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
    else:
        raise ValueError("Type de clé inconnu.")
    return serialize_private(key, passphrase), public_bytes(key)


def serialize_private(key, passphrase: str) -> bytes:
    if len(passphrase.encode("utf-8")) > 72:
        raise ValueError("La nouvelle passphrase est limitée à 72 octets UTF-8.")
    encryption = serialization.BestAvailableEncryption(passphrase.encode("utf-8")) if passphrase else serialization.NoEncryption()
    return key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.OpenSSH, encryption)


def parse_public(text: str) -> tuple[str, str, str]:
    lines = text.strip().splitlines()
    if len(lines) != 1:
        raise ValueError("Le fichier public doit contenir une seule clé.")
    parts = lines[0].split(maxsplit=2)
    if len(parts) < 2:
        raise ValueError("Format de clé publique invalide.")
    serialization.load_ssh_public_key(lines[0].encode("utf-8"))
    blob = base64.b64decode(parts[1], validate=True)
    fingerprint = "SHA256:" + base64.b64encode(hashlib.sha256(blob).digest()).decode("ascii").rstrip("=")
    return parts[0], parts[2] if len(parts) > 2 else "", fingerprint


def inspect_private(data: bytes) -> tuple[bytes | None, bool]:
    """Lit la partie publique du conteneur OpenSSH, même si le secret est chiffré."""
    if b"BEGIN OPENSSH PRIVATE KEY" not in data:
        try:
            return public_bytes(load_private(data)), False
        except ValueError as exc:
            if "Passphrase requise" in str(exc):
                return None, True
            raise
    lines = data.strip().splitlines()
    if lines[0] != b"-----BEGIN OPENSSH PRIVATE KEY-----" or lines[-1] != b"-----END OPENSSH PRIVATE KEY-----":
        raise ValueError("Conteneur de clé privée invalide.")
    raw = base64.b64decode(b"".join(lines[1:-1]), validate=True)
    if not raw.startswith(b"openssh-key-v1\0"):
        raise ValueError("Conteneur de clé privée invalide.")
    offset = 15
    def field():
        nonlocal offset
        if offset + 4 > len(raw):
            raise ValueError("Clé privée tronquée.")
        length = struct.unpack_from(">I", raw, offset)[0]
        offset += 4
        if offset + length > len(raw):
            raise ValueError("Clé privée tronquée.")
        value = raw[offset:offset + length]
        offset += length
        return value
    cipher, kdf, options = field(), field(), field()
    if offset + 4 > len(raw) or struct.unpack_from(">I", raw, offset)[0] != 1:
        raise ValueError("Nombre de clés privées invalide.")
    offset += 4
    blob = field()
    secret = field()
    if offset != len(raw) or not secret:
        raise ValueError("Clé privée tronquée.")
    type_length = struct.unpack_from(">I", blob, 0)[0]
    key_type = blob[4:4 + type_length]
    public = key_type + b" " + base64.b64encode(blob)
    serialization.load_ssh_public_key(public)
    encrypted = cipher != b"none"
    if not encrypted:
        if kdf != b"none" or options:
            raise ValueError("Conteneur de clé privée invalide.")
        if public_bytes(load_private(data)) != public:
            raise ValueError("Parties privée et publique incohérentes.")
    return public, encrypted
