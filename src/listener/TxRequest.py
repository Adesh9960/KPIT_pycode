from enum import Enum
from dataclasses import dataclass
class TxRequestType(Enum):
    UDS = "uds"
    RAWCAN = "raw_can"
@dataclass
class TxRequest:
    priority: int #Used by priority Queue
    enqueue_timestamp_ns: int
    request_id: int 
    request_type: TxRequestType
    payload: dict
    retry_count: int = 0
    max_retries: int
    next_retry_time: float = 0
    timeout_ms: int
    uds_error_callback: function | None
    confirmation_callback: function | None

type RetryHeap = list[tuple[int, TxRequest]]