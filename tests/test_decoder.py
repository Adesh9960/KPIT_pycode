"""
test_decoder.py
---------------
Standalone test injector for decoder.py.
Run this instead of listener.py when you have no real CAN hardware.
 
Usage:
    python test_decoder.py
"""
 
import cantools
import time
import threading
from queue import Queue
from dataclasses import dataclass
 
from Decoder.validate import validate_signals
from Decoder.dlc_guards import validate_dlc
from Decoder.hit_misses import lookup_message_definition
from typing import TypeAlias
from data_structures.CANFrame import CANFrame


 
# ── Minimal CANFrame stub (same shape listener.py would produce) ──────────────
# @dataclass 
# class CANFrame:
#     timestamp_ns: int
#     can_id: TypeAlias = int
#     dlc: int
#     data: bytes
#     is_extended: bool
#     is_fd: bool
#     is_error: bool
 
 
# ── Load DBC ──────────────────────────────────────────────────────────────────
db = cantools.database.load_file("encoder/Vehicle.dbc")
 
# Extended ID fix applied here
message_map = {}
for msg in db.messages:
    if msg.frame_id & 0x80000000:
        message_map[msg.frame_id & ~0x80000000] = msg   # strip the bit
    else:
        message_map[msg.frame_id] = msg
 
# Print what's available
print("=== Messages in Vehicle.dbc ===")
for fid, msg in message_map.items():
    print(f"  ID={hex(fid)} ({fid})  name={msg.name}  dlc={msg.length}")
print()
 
 
# ── Build test frames from real DBC entries ───────────────────────────────────
def make_test_frames():
    frames = []
    for fid, msg_def in message_map.items():
        frames.append(CANFrame(
            timestamp_ns=time.time_ns(),
            can_id=fid,
            dlc=msg_def.length,
            data=bytes(msg_def.length),
            is_extended=bool(fid & 0x80000000),   # correct flag now
            is_fd=False,
            is_error=False,
        ))
    # Unknown ID to test Miss path
    # Truncated FD frame — only 8 bytes instead of 32
    frames.append(CANFrame(
        timestamp_ns=time.time_ns(),
        can_id=0x200,
        dlc=32,                  # DLC says 32
        data=bytes(8),           # but only 8 bytes present
        is_extended=False,
        is_fd=True,
        is_error=False,
    ))
    return frames
 
 
# ── Decoder loop ──────────────────────────────────────────────────────────────
def decoder_loop(rx_queue: Queue):
    while True:
        msg = rx_queue.get()
        try:
            print(
                f"\nReceived Frame "
                f"ID={hex(msg.can_id)} "
                f"Extended={msg.is_extended} "
                f"FD={msg.is_fd}"
            )
 
            msg_def = lookup_message_definition(msg.can_id, message_map)
            if msg_def is None:
                continue
 
            validate_dlc(msg, msg_def)
 
            decoded_signals = db.decode_message(msg.can_id, msg.data,allow_truncated=True)
            print(f"Decoded Signals: {decoded_signals}")
 
            frame_valid, signal_errors = validate_signals(msg_def, decoded_signals)
            print(f"Frame Valid: {frame_valid}")
 
            if signal_errors:
                print(f"Signal Errors: {signal_errors}")
 
            decoded_packet = {
                "timestamp_ns": msg.timestamp_ns,
                "can_id": hex(msg.can_id),
                "message_name": msg_def.name,
                "signals": decoded_signals,
                "valid": frame_valid,
                "errors": signal_errors,
            }
            print(decoded_packet)
 
        except Exception as e:
            print(f"[DECODE ERROR] {e}")
        finally:
            rx_queue.task_done()
 
 
# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    rx_queue = Queue()
 
    t = threading.Thread(target=decoder_loop, args=(rx_queue,), daemon=True)
    t.start()
 
    frames = make_test_frames()
    print(f"Injecting {len(frames)} test frame(s)...\n")
 
    for frame in frames:
        rx_queue.put(frame)
 
    rx_queue.join()
    print("\n=== All frames processed. Decoder is working correctly. ===")
