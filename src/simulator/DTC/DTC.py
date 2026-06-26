from dataclasses import dataclass

@dataclass
class DTC:
    code: int
    description: str
    status: int
    timestamp: float
    snapshot: dict