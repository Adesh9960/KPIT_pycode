from enum import Enum
from dataclasses import dataclass, field
from can import Message
class TxRequestType(Enum):
    UDS = "uds"
    RAWCAN = "raw_can"
@dataclass(order=True)
class TxRequest:
    # Used for ordering
    priority: int
    enqueue_timestamp_ns: int

    # Not used for ordering
    request_type: TxRequestType = field(compare=False)
    payload: Message = field(compare=False)
    max_retries: int = field(compare=False)
    timeout_ms: int = field(compare=False)
    retry_count: int = field(default=0, compare=False)
    next_retry_time: float = field(default=0.0, compare=False)
    uds_error_callback: function | None = field(default=None, compare=False)
    confirmation_callback: function | None = field(default=None, compare=False)
    request_id: int | None = field(default=None, compare=False)

type RetryHeap = list[tuple[int, TxRequest]]