import time
import listener.main as main
from errors import TransmissionError
from .TxRequest import TxRequest
from logger.logger import write_log
from utils.sendFrameToCANFrame import sendFrameToCANFrame
import heapq
def transmit(msg: TxRequest):
    try:
        main.adapter.send(msg.payload)
    except TransmissionError as e:
        error_log = sendFrameToCANFrame(msg.payload)
        error_log.details = "Transmission Error"
        write_log(error_log)
        
        if(msg.request_type == 'raw_can' and msg.retry_count < msg.max_retries):
            timeout = ((msg.retry_count + 1) * 10)**2 
            msg.timeout_ms = timeout
            msg.next_retry_time = (time.monotonic() * 1000) + msg.timeout_ms 
            heapq.heappush(main.retry_queue, (msg.next_retry_time, msg))
        if(msg.request_type == 'uds' and msg.retry_count < msg.max_retries):
            msg.uds_error_callback()

def transmitter():
    while True:
        msg = main.tx_queue.remove()
        transmit(msg)
        if main.retry_queue[0][0] <= (time.monotonic() * 1000):
            _, msg = heapq.heappop(main.retry_queue)
            msg.retry_count += 1
            transmit(msg)

    