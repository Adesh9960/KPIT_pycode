"""
uds_crypto.py

AES-128-GCM encryption/decryption for UDS payloads.

This sits between the UDS layer (SID + data) and whatever transport
carries the bytes (ISO-TP -> CAN). Transport layers are not touched —
they just carry whatever bytes they're handed.

Wire format produced by encrypt_uds_payload():
    [ nonce (12 bytes) | ciphertext (N bytes) | tag (16 bytes) ]

This is a separate concern from UDS SecurityAccess (0x27). SecurityAccess
proves the tester is *authorized*. This module protects the *confidentiality
and integrity* of the bytes on the wire. Do not reuse the SecurityAccess
seed-key as the AES key -- that key is derived with a deliberately weak
demo algorithm meant for the unlock handshake, not for encryption.
"""

import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

NONCE_SIZE = 12   # bytes, GCM standard nonce size
TAG_SIZE = 16     # bytes, full-length GCM auth tag
KEY_SIZE = 16     # bytes, AES-128


class UDSCryptoError(Exception):
    """Raised when decryption or authentication of a UDS payload fails."""
    pass


def encrypt_uds_payload(key: bytes, uds_payload: bytes) -> bytes:
    """
    Encrypt a UDS payload (SID + data) with AES-128-GCM.

    Args:
        key: 16-byte AES-128 key.
        uds_payload: raw bytes, e.g. b'\\x2E\\xF1\\x90\\x01\\x02'
            (SID + DID + data).

    Returns:
        bytes: nonce || ciphertext || tag. Hand this whole blob to
            whatever sends bytes over ISO-TP/CAN -- treat it as opaque.

    Raises:
        ValueError: if key is not 16 bytes.
    """
    if len(key) != KEY_SIZE:
        raise ValueError(f"AES-128 key must be {KEY_SIZE} bytes, got {len(key)}")

    nonce = os.urandom(NONCE_SIZE)
    aesgcm = AESGCM(key)
    # AESGCM.encrypt() appends the tag to the ciphertext automatically
    ciphertext_and_tag = aesgcm.encrypt(nonce, uds_payload, associated_data=None)

    return nonce + ciphertext_and_tag


def decrypt_uds_payload(key: bytes, wire_bytes: bytes) -> bytes:
    """
    Decrypt a wire-format blob (nonce || ciphertext || tag) back into the
    original UDS payload (SID + data).

    Args:
        key: 16-byte AES-128 key.
        wire_bytes: bytes as received from the transport
            (nonce || ciphertext || tag).

    Returns:
        bytes: the original UDS payload (SID + data).

    Raises:
        ValueError: if key is not 16 bytes, or wire_bytes is too short
            to contain a nonce and tag.
        UDSCryptoError: if authentication fails -- tampered/corrupted
            payload, or wrong key.
    """
    if len(key) != KEY_SIZE:
        raise ValueError(f"AES-128 key must be {KEY_SIZE} bytes, got {len(key)}")

    if len(wire_bytes) < NONCE_SIZE + TAG_SIZE:
        raise ValueError(
            f"wire_bytes too short ({len(wire_bytes)} bytes) to contain "
            f"a {NONCE_SIZE}-byte nonce and {TAG_SIZE}-byte tag"
        )

    nonce = wire_bytes[:NONCE_SIZE]
    ciphertext_and_tag = wire_bytes[NONCE_SIZE:]

    aesgcm = AESGCM(key)
    try:
        uds_payload = aesgcm.decrypt(nonce, ciphertext_and_tag, associated_data=None)
    except InvalidTag as e:
        raise UDSCryptoError(
            "UDS payload decryption/authentication failed -- payload may be "
            "corrupted, tampered with, or the AES key is wrong"
        ) from e

    return uds_payload
