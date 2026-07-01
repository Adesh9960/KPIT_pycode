import time
import listener.main as main
from errors.TransmissionError import TransmissionError 
from .TxRequest import TxRequest, TxRequestType
from logger.logger import write_log
from utils.sendFrameToCANFrame import sendFrameToCANFrame
from listener.driver.SocketCANAdapter import BusState
import heapq

# Counter to track the total number of ISO-TP payloads transmitted
iso_count = 0

def transmit(msg: TxRequest):
    """
    Executes the direct physical or transport layer network transmission of a message.

    This function attempts to send the message payload. If the message is categorized 
    as `RAWCAN`, it hooks directly into the driver adapter. If it is a `UDS` or segmented 
    payload, it routes it through the ISO-TP network layer stack—including a watchdog 
    loop that prevents a stuck or blocked stack from blocking the thread. If a transmission 
    failure occurs, it captures it, logs the error, and updates the retry schedule.

    Args:
        msg (TxRequest): The prioritized frame transaction object containing payloads, 
                         protocol type, and retry state.
    """
    global iso_count
    try:
        if msg.request_type == TxRequestType.RAWCAN:
            # Route directly to the physical interface for standard CAN frames
            main.adapter.send(msg.payload)
        else:
            start = time.monotonic()
            print("transmitting isotp")
            
            # Watchdog Loop: Prevent the transmitter from locking up indefinitely if the stack stalls
            while main.stack.transmitting():
                if time.monotonic() >= start + 3:
                    print("ISO-TP stuck for too long please restart...")
                    # Note: Consider adding a break or raising an exception here to actively handle the stall
            
            if main.isotpTXCallback is not None:
                main.isotpTXCallback()
                
            print("Tx Count: ", bytes([iso_count & 0xff]) )
            print("STACK SEND:", msg.payload)
            
            # Hand payload off to the reassembly and transport layer stack
            main.stack.send(msg.payload)
            iso_count += 1 # Fixed typo in original code (=+)
            print("transmitted istop successfully")

    except TransmissionError as e:
        # Normalize the network frame payload into a logging instance upon failure
        error_log = sendFrameToCANFrame(msg.payload)
        error_log.details = "Transmission Error"
        if main.listener_enabled:
            write_log(error_log)

        # Retry scheduling logic for standard raw CAN frames using an exponential backoff formula
        if msg.request_type == TxRequestType.RAWCAN and msg.retry_count < msg.max_retries:
            # Exponential Backoff Formula: ((attempts + 1) * 10)^2 milliseconds
            timeout = ((msg.retry_count + 1) * 10)**2 
            msg.timeout_ms = timeout
            # Map out exact target time in milliseconds relative to monotonic clock
            msg.next_retry_time = (time.monotonic() * 1000) + msg.timeout_ms 
            # Push into the priority queue heap sorted by the earliest scheduled time
            heapq.heappush(main.retry_queue, (msg.next_retry_time, msg))

        # Fault handling logic for complex diagnostic UDS requests
        if msg.request_type == TxRequestType.UDS and msg.retry_count < msg.max_retries:
            msg.uds_error_callback()


def transmitter():
    """
    Continuous worker loop that coordinates outbound message scheduling.

    Runs on a dedicated background thread while `main.running` is True. It performs 
    the following sequence:
    1. Fetches and blocks on ready requests from the principal priority thread-safe queue (`tx_queue`).
    2. Dispatches it to the physical or transport network adapter (`transmit`).
    3. Evaluates the local binary heap tracking failed requests (`retry_queue`). If a frame has 
       outlived its backoff timeout schedule, it increments its internal retry tally and re-transmits.
    4. Sleeps for 1 millisecond at the tail of each cycle to release execution contexts.
    """
    while main.running:
        # Pull the highest priority or sequentially next item from the thread-safe queue
        msg = main.tx_queue.get()
        if isinstance(msg, bytes):
            print(msg)
            
        transmit(msg)
        
        # Chronological evaluations of backoff queues
        if len(main.retry_queue) > 0 and main.retry_queue[0][0] <= (time.monotonic() * 1000):
            # Extract the message whose target backoff timestamp has passed
            _, msg = heapq.heappop(main.retry_queue)
            msg.retry_count += 1
            transmit(msg)
            
        # Minor delay tick to mitigate high CPU polling
        time.sleep(0.001)