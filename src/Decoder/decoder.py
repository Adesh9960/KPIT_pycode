import cantools
import can
import time
from Decoder.validate import validate_signals
from Decoder.dlc_guards import validate_dlc
from Decoder.hit_misses import lookup_message_definition
import listener.main as main

# load dbc file to ram
db= cantools.database.load_file("encoder/Vehicle.dbc")
mask = 0x80000000



#Lookup Signal   
message_map = {}

for msg in db.messages:
    if msg.frame_id & mask:       
        message_map[msg.frame_id & ~mask] = msg  
    else:
        message_map[msg.frame_id] = msg
    

def run_decoder(notify_callback: function = None):
    while True:
        msg = main.can_queue.get()

        try:

            print(
                f"\nReceived Frame "
                f"ID={hex(msg.can_id)} "
                f"Extended={msg.is_extended} "
                f"FD={msg.is_fd}"
            )

        # Hit/miss cases
            msg_def = lookup_message_definition(
                msg.can_id,
                message_map
            )

            if msg_def is None:
                continue

        # DLC Validation
            validate_dlc(
                msg,
                msg_def
            )

        # Decode Signals
            decoded_signals = db.decode_message(
                msg.can_id,
                msg.data,
                allow_truncated = True
            )

            print(
                f"Decoded Signals: "
                f"{decoded_signals}"
            )

        # Signal Validation
            frame_valid, signal_errors = (
                validate_signals(
                    msg_def,
                    decoded_signals
                )
            )

            print(
                f"Frame Valid: "
                f"{frame_valid}"
            )

            if signal_errors:

                print(
                    f"Signal Errors: "
                    f"{signal_errors}"
                )

            decoded_packet = {
                "timestamp_ns": msg.timestamp_ns,
                "can_id": hex(msg.can_id),
                "message_name": msg_def.name,
                "signals": decoded_signals,
                "valid": frame_valid,
                "errors": signal_errors
            }

            print(decoded_packet)
            if(notify_callback is not None):
                notify_callback(decoded_packet)
        except Exception as e:

            print(
                f"[DECODE ERROR] {e}"
            )

        finally:

            rx_queue.task_done()