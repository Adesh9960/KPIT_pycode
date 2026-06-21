from dataclasses import dataclass

@dataclass
class DID:
    did: int
    is_writable: bool
    security_level: int