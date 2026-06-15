from data_structures.MessageMonitor import MessageMonitor
from .driver.SocketCANAdapter import SocketCANAdapter
import custom_types
from threading import Lock, Thread
from queue import Queue, PriorityQueue
from .TxRequest import RetryHeap

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

