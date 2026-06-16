from data_structures.MessageMonitor import MessageMonitor
from .driver.SocketCANAdapter import SocketCANAdapter
import custom_types
from threading import Lock, Thread
from queue import Queue, PriorityQueue
from .TxRequest import RetryHeap
import isotp
running: bool = False
message_monitor_list: dict[custom_types.can_id, MessageMonitor] = {}
adapter: SocketCANAdapter = None

# rx queues
logger_queue: Queue
uds_queue: Queue
can_queue: Queue

# tx queues
tx_queue: PriorityQueue
retry_queue: RetryHeap = []

#threads
timeout_thread: Thread
rx_thread: Thread
tx_thread: Thread

#raw can
raw_can_receiver: None
#isotp
rxid = 0x7E8
txid = 0x7E0
last_is_fd = False
last_is_extended = False
address = isotp.Address(
    isotp.AddressingMode.Normal_11bits,
    txid=txid,
    rxid=rxid
)
stack: isotp.NotifierBasedCanStack
isotpTXCallback: function | None = None

