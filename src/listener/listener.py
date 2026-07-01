import listener.main as main
from .driver.SocketCANAdapter import SocketCANAdapter
from .driver.CANconfig import CANConfig
from .tranmitter import transmitter
from .iso_receiver import iso_receiver
from .raw_can_receiver import RawReceiver
from .timeout import monitor_timeouts
import threading
from .TxRequest import TxRequest
import logger.logger as logger 
import queue
import can
import time
import isotp
from listener.iso_tp_error_decoder import IsoTpErrorHandler
from data_structures.BusStatistics import BusStatistics

def start(address, uds_response_event = None, channel = "can0", enable_logger = True):
    """
    Initializes and boots up the complete CAN network subsystem.

    This configures and opens the SocketCAN adapter interface, spins up the 
    ISO-TP network transport layer, prepares message transmission/reception 
    queues, and launches background thread workers to handle network processing.

    Args:
        address (isotp.Address): The ISO-TP addressing scheme (tx/rx IDs) used for 
            segmented network messaging.
        uds_response_event (threading.Event, optional): A synchronization primitive 
            passed to the receiver loop to signal the arrival of an expected UDS frame.
        channel (str, optional): The name of the Linux network interface to bind to. 
            Defaults to "can0".
        enable_logger (bool, optional): Determines if frame logging should be activated 
            globally within the manager state. Defaults to True.
    """
    adapter_config = CANConfig(
    "socketcan",
    channel,
    500_000,
    restart_ms=100,
    )
    main.listener_enabled = enable_logger
    main.raw_can_receiver = RawReceiver()
    main.adapter = SocketCANAdapter(adapter_config, listeners=[main.raw_can_receiver])
    main.adapter.open()

    #Setting ISO
    iso_error_handler = IsoTpErrorHandler()
    main.stack = isotp.NotifierBasedCanStack(
        bus=main.adapter.bus,
        notifier = main.adapter.notifier,
        address=address,
        error_handler = iso_error_handler,
        params = {
    'rx_flowcontrol_timeout': 5000,        # N_Bs: Wait up to 5s for Flow Control frame (Default: 1000)
    'rx_consecutive_frame_timeout': 5000,  # N_Cs: Wait up to 5s for the next Consecutive Frame (Default: 1000)
    'wftmax': 10,                          # Max number of Wait Flow Control frames allowed (Default: 0/4)
    'stmin': 10,                           # Separation Time (ms) to tell the sender to slow down
    'tx_data_length': 8,                   # Standard 8-byte CAN frame data length
}
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


def get_stats() -> BusStatistics:
    """
    Retrieves the current physical layer bus performance metadata.

    Returns:
        BusStatistics: An object tracking error metrics, total frame counts, 
                       dropped frames, and network statistics.
    """
    return main.adapter.stats


def stop():
    """
    Gracefully halts network activity and releases physical interface bindings.

    Signaled by lowering the module execution flag, letting all background 
    workers (transmitters, receivers, and monitors) unwind and terminate before 
    closing the hardware abstraction adapter layer safely.
    """
    print("Stopping listener...")
    main.running = False
    main.tx_thread.join()
    main.rx_thread.join()
    main.timeout_thread.join()
    print("Threads closed")
    main.adapter.close()
    print("Listener Stopped")


def send_to_tx_queue(request: TxRequest):
    """
    Schedules an outbound frame request for network delivery.

    Appends the target transaction into the system priority queue where the 
    transmitter thread handles it based on its defined sequence order.

    Args:
        request (TxRequest): The structured encapsulation container holding the payload 
                             and transaction metadata to be broadcasted.
    """
    main.tx_queue.put(request)


def test_transmission():
    """
    Runs a diagnostic simulation pipeline to verify CAN physical and transport loops.

    Asynchronously pushes several raw standard CAN frame transmission requests onto the 
    scheduling queue spaced by short delay parameters, followed by an ISO-TP encoded 
    UDS request payload, before systematically winding down system subsystems.
    """
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