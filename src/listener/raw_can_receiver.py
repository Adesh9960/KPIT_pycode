import can
import listener.main as main
from data_structures.CANFrame import CANFrame
from logger.logger import write_log
from .error_decoder import decode_error
import time
class RawReceiver(can.Listener):
    def on_message_received(self, msg: can.Message):
        frame = CANFrame(
                timestamp_ns=int(msg.timestamp * 1_000_000_000),
                can_id=msg.arbitration_id,
                dlc=msg.dlc,
                data=msg.data,
                is_extended=msg.is_extended_id,
                is_fd=msg.is_fd,
                is_error=msg.is_error_frame
        )

        main.adapter.stats.rx_frames += 1
        if msg.is_error_frame:
            main.adapter.stats.error_frames += 1
            error_frame = decode_error(frame)
            if error_frame is not None:
                write_log(error_frame)

        elif msg.arbitration_id == main.rxid:
            print("Frame is isotp")
            print(frame)
            write_log(frame)
            main.last_is_extended = msg.is_extended_id
            main.last_is_fd = msg.is_fd

        else:
            print(frame)
            write_log(frame)
            monitor = main.message_monitor_list.get(frame.can_id)
            if monitor is not None:
                monitor.last_rx_time = time.monotonic()
            main.can_queue.put(frame)

  