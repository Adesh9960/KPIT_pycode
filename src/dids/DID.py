from dataclasses import dataclass

@dataclass
class DID:
    did: int
    value: bytes
    is_writable: bool
    security_level: int