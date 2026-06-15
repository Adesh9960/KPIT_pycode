import time
import listener.main as main
from logger.logger import write_log
from .error_decoder import decode_error
def is_UDS(can_id: int) -> bool:
    return False 

def receiver():
    print("receiver started")
    while main.running:
        raw_frame = main.adapter.receive()
        monitor = main.message_monitor_list.get(raw_frame.can_id)
        if monitor is not None:
            monitor.last_rx_time = time.monotonic()
        if not raw_frame.is_error:
            write_log(raw_frame)
            print(raw_frame)
            if is_UDS(raw_frame.can_id):
                main.uds_queue.put(raw_frame)
            else:
                main.can_queue.put(raw_frame)
        else: 
            error_frame = decode_error(raw_frame)
            if error_frame is not None:
                print(raw_frame)
                write_log(error_frame)
            
