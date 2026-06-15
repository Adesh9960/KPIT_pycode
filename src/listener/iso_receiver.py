import time
import listener.main as main
from data_structures.CANFrame import CANFrame
# def is_UDS(can_id: int) -> bool:
#     return False 

# def receiver():
#     print("receiver started")
#     while main.running:
#         raw_frame = main.adapter.receive()
#         monitor = main.message_monitor_list.get(raw_frame.can_id)
#         if monitor is not None:
#             monitor.last_rx_time = time.monotonic()
#         if not raw_frame.is_error:
#             write_log(raw_frame)
#             print(raw_frame)
#             if is_UDS(raw_frame.can_id):
#                 main.uds_queue.put(raw_frame)
#             else:
#                 main.can_queue.put(raw_frame)
#         else: 
#             error_frame = decode_error(raw_frame)
#             if error_frame is not None:
#                 print(raw_frame)
#                 write_log(error_frame)


def iso_receiver():
    while True:
        if main.stack.available():
            payload = main.stack.recv()   # Reads from ISO-TP buffer, NOT the CAN bus
            uds_message = CANFrame(
                timestamp_ns= time.time_ns(),
                can_id=main.rxid,
                dlc = len(payload),
                data=bytes(payload),
                is_extended=main.last_is_extended,
                is_fd=main.last_is_fd
            )
            main.uds_queue.put(uds_message)
