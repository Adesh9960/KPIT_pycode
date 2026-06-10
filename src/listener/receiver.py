import time
import listener.main as main
from logger.logger import write_log
from error_decoder import decode_error
def is_UDS(): pass

def receiver():
    while True:
        raw_frame = main.adapter.receive()
        monitor = main.message_monitor_list[raw_frame.can_id]

        if monitor:
            monitor = time.monotonic()
        if not raw_frame.is_error:
            write_log(raw_frame)
            if is_UDS(raw_frame.can_id):
                main.uds_queue.put(raw_frame)
            else:
                main.can_queue.put(raw_frame)
        else: 
            write_log(decode_error(raw_frame))
            