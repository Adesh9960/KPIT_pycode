import listener.main as main
from .driver.SocketCANAdapter import SocketCANAdapter
from .driver.CANconfig import CANConfig
from .tranmitter import transmitter
from .receiver import receiver
from .timeout import monitor_timeouts
import threading
from .TxRequest import TxRequest, TxRequestType
import logger.logger as logger 
import queue
import can
import time

def start():
    adapter_config = CANConfig(
    "socketcan",
    "can0",
    500_000,
    restart_ms=100
    )
    main.adapter = SocketCANAdapter(adapter_config)
    main.adapter.open()
    main.uds_queue = queue.Queue()
    main.can_queue = queue.Queue()
    main.tx_queue = queue.PriorityQueue()
    main.running = True
    main.tx_thread = threading.Thread(target=transmitter)
    main.rx_thread = threading.Thread(target=receiver)
    main.timeout_thread = threading.Thread(target=monitor_timeouts)
    main.tx_thread.start()
    main.rx_thread.start()
    main.timeout_thread.start()
    print("Listener Started")
    print("Ready to receive and send messages")
def stop():
    print("Stopping listener...")
    main.running = False
    main.tx_thread.join()
    main.rx_thread.join()
    main.timeout_thread.join()
    print("Threads closed")
    main.adapter.close()
    print("Listener Stopped")

def send_to_tx_queue(request: TxRequest):
    main.tx_queue.put(request)
def test_transmission():
    test_frame = can.Message(
        arbitration_id=102,      # ← still use the raw ID here
        data=b'\x01\x02\x03',
        dlc=3,
        is_extended_id=False,
        is_fd=False
    )
    count = 1
   
    while(count < 10):
        test_request = TxRequest(
            priority=1,
            enqueue_timestamp_ns=time.time_ns(),
            request_type=TxRequestType.RAWCAN,
            request_id=count,
            payload=test_frame,
            max_retries=0,
            timeout_ms=100,
        )
        send_to_tx_queue(test_request)
        count+= 1
        time.sleep(3)
    logger.stop()
    stop()

# start()
# test_transmission()