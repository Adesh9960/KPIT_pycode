import time 
import listener.main as main
from logger.logger import write_log
def check_timeouts():
    for _, message_monitor in main.message_monitor_list.items():
        now = time.monotonic()
        elapsed = (now - message_monitor.last_rx_time)
        if elapsed > message_monitor.timeout_ms:
            message_monitor.callback()

def monitor_timeouts():
    while True:
        check_timeouts()
        time.sleep(0.01)
