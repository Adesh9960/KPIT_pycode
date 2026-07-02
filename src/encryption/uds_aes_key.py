"""
uds_aes_key.py

Single source of truth for the AES-128 key used to encrypt/decrypt UDS
payloads. Both the tester (uds_client.py) and the ECU (uds.py) import
this so the key never gets out of sync between the two sides.

PROTOTYPE NOTE:
This is a static, hardcoded key for development/demo purposes only.
It is NOT derived from SecurityAccess (0x27) -- that key proves the
tester is authorized; this key protects confidentiality/integrity of
the bytes on the wire. They are deliberately separate concerns.

Before this goes anywhere near a real vehicle network:
  - move this into core/config_manager.py (config.yaml) rather than
    a hardcoded Python constant
  - consider deriving a session key from the SecurityAccess exchange
    instead of using one static key for the whole platform's lifetime
"""

# 16 bytes = AES-128. Generated once for this prototype; replace freely.
UDS_AES_KEY = bytes.fromhex("e2997b1a1deb7f16160ca8df64fe6ad3")
