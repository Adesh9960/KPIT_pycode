from dataclasses import dataclass
import time

@dataclass
class DTC:
    code: int
    description: str
    status: int
    timestamp: float
    snapshot: dict