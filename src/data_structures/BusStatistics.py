from dataclasses import dataclass
@dataclass
class BusStatistics:
    rx_frames: int = 0
    tx_frames: int = 0
    error_frames: int = 0
    tx_error_frames: int = 0
    bus_off_count: int = 0