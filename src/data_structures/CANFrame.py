from dataclasses import dataclass
import custom_types
@dataclass
class CANFrame:
    timestamp_ns: int
    can_id: custom_types.can_id
    dlc: int
    data: bytes
    is_extended: bool
    is_fd: bool
    is_error: bool
    details: str = None
