from dataclasses import dataclass
@dataclass
class MessageMonitor:
    can_id: str
    timeout_ms: float
    last_rx_time: float
    callback: function | None

     