from enum import Enum
from dataclasses import dataclass
from can import Message
class TxRequestType(Enum):
    UDS = "uds"
    RAWCAN = "raw_can"
@dataclass
class TxRequest:
    priority: int #Used by priority Queue
    enqueue_timestamp_ns: int
    request_id: int 
    request_type: TxRequestType
    payload: Message
    max_retries: int
    timeout_ms: int
    retry_count: int = 0
    next_retry_time: float = 0
    uds_error_callback: function | None = None
    confirmation_callback: function | None= None

type RetryHeap = list[tuple[int, TxRequest]]