import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

NONCE_SIZE = 12
TAG_SIZE = 16
KEY_SIZE = 16

class UDSCryptoError(Exception):
    """Raised when decryption or authentication of a UDS payload fails."""
    pass

def encrypt_uds_payload(key: bytes, uds_payload: bytes) -> bytes:
    if len(key) != KEY_SIZE:
        raise ValueError(f"AES-128 key must be {KEY_SIZE} bytes, got {len(key)}")

    # nonce = os.urandom(NONCE_SIZE)
    nonce = b"\x00" * 12
    aesgcm = AESGCM(key)
    ciphertext_and_tag = aesgcm.encrypt(nonce, uds_payload, associated_data=None)

    # Combine nonce and ciphertext+tag
    core_payload = nonce + ciphertext_and_tag
    
    # Prepend a 2-byte length header. This prevents CAN/ISO-TP padding 
    # from shifting the 16-byte auth tag during decryption.
    length_prefix = len(core_payload).to_bytes(2, byteorder='big')
    
    return length_prefix + core_payload


def decrypt_uds_payload(key: bytes, wire_bytes: bytes) -> bytes:
    if len(key) != KEY_SIZE:
        raise ValueError(f"AES-128 key must be {KEY_SIZE} bytes, got {len(key)}")

    # Need at least 2 (len) + 12 (nonce) + 16 (tag) = 30 bytes minimum
    if len(wire_bytes) < 2 + NONCE_SIZE + TAG_SIZE:
        raise ValueError(f"wire_bytes too short ({len(wire_bytes)} bytes)")

    # 1. Extract the true length of the crypto payload
    expected_len = int.from_bytes(wire_bytes[:2], byteorder='big')
    
    # 2. Slice off any trailing CAN/ISO-TP padding
    core_payload = wire_bytes[2:2+expected_len]
    
    if len(core_payload) != expected_len:
        raise UDSCryptoError("Payload length mismatch. Data may be fragmented.")

    nonce = core_payload[:NONCE_SIZE]
    ciphertext_and_tag = core_payload[NONCE_SIZE:]

    aesgcm = AESGCM(key)
    try:
        uds_payload = aesgcm.decrypt(nonce, ciphertext_and_tag, associated_data=None)
    except InvalidTag as e:
        raise UDSCryptoError(
            "UDS payload decryption failed -- payload tampered, padded improperly, or wrong key"
        ) from e

    return uds_payload