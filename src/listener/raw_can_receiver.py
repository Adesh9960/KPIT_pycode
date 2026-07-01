import can
import listener.main as main
from data_structures.CANFrame import CANFrame
from logger.logger import write_log
from .error_decoder import decode_error
import time

class RawReceiver(can.Listener):
    """
    A custom CAN network interface listener that processes raw incoming messages.

    Inherits from `can.Listener`. This class acts as a callback interface attached 
    to the hardware notifier loop. It intercepts every physical layer frame, normalizes 
    it into an application-specific `CANFrame`, updates bus telemetry metrics, and 
    routes the frame based on its protocol properties (Error, ISO-TP, or Generic CAN).
    """

    def on_message_received(self, msg: can.Message):
        """
        Callback handler invoked automatically whenever a new CAN frame is read from the bus.

        Processes the raw hardware frame through three sequential architectural steps:
        1. Normalizes the hardware parameters into an application `CANFrame` object, 
           converting seconds to nanosecond timestamps.
        2. Increments global telemetry diagnostics metrics tracking total packets and errors.
        3. Triages the message routing logic:
           - **Error Frames:** Intercepted and handed off to a protocol decoder before logging.
           - **ISO-TP Traffic:** Identified by matching target reception IDs, logged, and used 
             to dynamically update frame properties (Extended IDs vs. Flexible Data-rate).
           - **Generic/Raw Traffic:** Triggers activity watchdogs/monitors, logs the payload, 
             and pushes the frame onto the shared system application queue.

        Args:
            msg (can.Message): The raw hardware encapsulation packet received from the 
                               underlying python-can interface driver layer.
        """
        # Step 1: Normalize python-can fields into the unified application frame structure
        frame = CANFrame(
                timestamp_ns=int(msg.timestamp * 1_000_000_000), # Hardware float seconds to integer nanoseconds
                can_id=msg.arbitration_id,
                dlc=msg.dlc,
                data=msg.data,
                is_extended=msg.is_extended_id,
                is_fd=msg.is_fd,
                is_error=msg.is_error_frame
        )

        # Step 2: Track global bus statistics via the underlying hardware adapter instance
        main.adapter.stats.rx_frames += 1
        
        # Step 3: Route messages based on frame properties
        if msg.is_error_frame:
            main.adapter.stats.error_frames += 1
            error_frame = decode_error(frame)
            # If the frame contains decoded error data and logging is globally enabled, record it
            if error_frame is not None and main.listener_enabled:
                write_log(error_frame)

        elif msg.arbitration_id == main.rxid:
            # Matches the targeted network transport layer ID (ISO-TP payload traffic)
            print("Frame is isotp")
            print(frame)
            if main.listener_enabled:
                write_log(frame)
            # Cache the physical wire state parameters to maintain historical context for responses
            main.last_is_extended = msg.is_extended_id
            main.last_is_fd = msg.is_fd

        else:
            # Standard Application Data Handling
            if main.listener_enabled:
                write_log(frame)
                
            # Reset the timeout watchdog monitor assigned to track this specific CAN ID's arrival intervals
            monitor = main.message_monitor_list.get(frame.can_id)
            if monitor is not None:
                monitor.last_rx_time = time.monotonic()
                
            # Deliver the frame payload directly into the consumer thread's processing queue
            if main.can_queue is not None:
                main.can_queue.put(frame)