from data_structures.MessageMonitor import MessageMonitor
from .driver.SocketCANAdapter import SocketCANAdapter
import custom_types
from threading import Thread
from queue import Queue, PriorityQueue
from .TxRequest import RetryHeap
import isotp
running: bool = False
message_monitor_list: dict[custom_types.can_id, MessageMonitor] = {}
adapter: SocketCANAdapter = None

# rx queues
logger_queue: Queue = None
can_queue: Queue = None

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
rxid = 0x62
txid = 0x22
last_is_fd = False
last_is_extended = False

stack: isotp.NotifierBasedCanStack
isotpTXCallback: function | None = None

