import listener.main as main
from driver.SocketCANAdapter import SocketCANAdapter
from driver.CANconfig import CANConfig
from tranmitter import transmitter
from receiver import receiver
from timeout import monitor_timeouts
import threading
from TxRequest import TxRequest
import queue

def start():
    adapter_config = CANConfig(
    "socketcan",
    "can0",
    500_000,
    restart_ms=100
    )
    main.adapter = SocketCANAdapter(adapter_config)
    
    main.uds_queue = queue.Queue()
    main.can_queue = queue.Queue()
    
    main.tx_queue = queue.PriorityQueue()

    main.tx_thread = threading.Thread(target=transmitter)
    main.rx_thread = threading.Thread(target=receiver)
    main.timeout_thread = threading.Thread(target=monitor_timeouts)
    main.tx_thread.start()
    main.rx_thread.start()
    main.timeout_thread.start()


def send_to_tx_queue(request: TxRequest):
    main.tx_queue.put(request)
