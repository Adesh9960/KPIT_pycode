import listener.main as main
from .driver.SocketCANAdapter import SocketCANAdapter
from .driver.CANconfig import CANConfig
from .tranmitter import transmitter
from .iso_receiver import iso_receiver
from .raw_can_receiver import RawReceiver
from .timeout import monitor_timeouts
import threading
from .TxRequest import TxRequest, TxRequestType
import logger.logger as logger 
import queue
import can
import time
import isotp
from listener.iso_tp_error_decoder import IsoTpErrorHandler

def start(uds_response_event = None):
    adapter_config = CANConfig(
    "socketcan",
    "can0",
    500_000,
    restart_ms=100,
    # fd_enabled=True
    )
    main.raw_can_receiver = RawReceiver()
    main.adapter = SocketCANAdapter(adapter_config, listeners=[main.raw_can_receiver])
    main.adapter.open()

    #Setting ISO
    iso_error_handler = IsoTpErrorHandler()
    main.stack = isotp.NotifierBasedCanStack(
        bus=main.adapter.bus,
        notifier = main.adapter.notifier,
        address=main.address,
        error_handler = iso_error_handler
    )
    main.stack.start()

    #Setting Queues
    main.can_queue = queue.Queue()
    main.tx_queue = queue.PriorityQueue()

    #Setting Threads
    main.running = True
    main.tx_thread = threading.Thread(target=transmitter)
    main.rx_thread = threading.Thread(target=iso_receiver, args = (uds_response_event,))
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
    iso_test_frame = can.Message(
        arbitration_id=0x7E0,
        data = b"\x62\xF1\x90\x12\x34\x56",
        dlc = 8,
        is_extended_id= False,
        is_fd = False
    )
    count = 1
   
    while(count < 10):
        test_request = TxRequest(
            priority=1,
            enqueue_timestamp_ns=time.time_ns(),
            request_type="raw_can",
            request_id=count,
            payload=test_frame,
            max_retries=0,
            timeout_ms=100,
        )
        send_to_tx_queue(test_request)
        count+= 1
        time.sleep(3)
    iso_test = TxRequest(
        priority=1,
        enqueue_timestamp_ns=time.time_ns(),
        request_type="uds",
        request_id=count,
        payload=iso_test_frame,
        max_retries=0,
        timeout_ms=100
    )
    send_to_tx_queue(iso_test)
    logger.stop()
    stop()

# start()
# test_transmission()