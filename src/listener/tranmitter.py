import time
import listener.main as main
from errors.TransmissionError import TransmissionError 
from .TxRequest import TxRequest,TxRequestType
from logger.logger import write_log
from utils.sendFrameToCANFrame import sendFrameToCANFrame
from listener.driver.SocketCANAdapter import BusState
import heapq


def transmit(msg: TxRequest):
    try:
        if(msg.request_type == TxRequestType.RAWCAN):
            main.adapter.send(msg.payload)
        else:
            start = time.monotonic()
            print("transmitting isotp")
            while main.stack.transmitting():
                if time.monotonic() >= start + 3:
                    print("ISO-TP stuck for too long please restart...")
            if main.isotpTXCallback is not None:
                main.isotpTXCallback()
            main.stack.send(msg.payload)
            print("transmitted istop successfully")

    except TransmissionError as e:
        error_log = sendFrameToCANFrame(msg.payload)
        error_log.details = "Transmission Error"
        if main.listener_enabled:
            write_log(error_log)

        if(msg.request_type == TxRequestType.RAWCAN and msg.retry_count < msg.max_retries):
            timeout = ((msg.retry_count + 1) * 10)**2 
            msg.timeout_ms = timeout
            msg.next_retry_time = (time.monotonic() * 1000) + msg.timeout_ms 
            heapq.heappush(main.retry_queue, (msg.next_retry_time, msg))

        if(msg.request_type == TxRequestType.UDS and msg.retry_count < msg.max_retries):
            msg.uds_error_callback()

def transmitter():
    while main.running:
        # if main.adapter.get_bus_state() == BusState.ERROR: 
            # print("CAN Bus is off")
            # time.sleep(2)
            # continue
        msg = main.tx_queue.get()
        if isinstance(msg, bytes):
            print(msg)
        transmit(msg)
        if len(main.retry_queue) > 0 and main.retry_queue[0][0] <= (time.monotonic() * 1000):
            _, msg = heapq.heappop(main.retry_queue)
            msg.retry_count += 1
            transmit(msg)
        time.sleep(0.001)