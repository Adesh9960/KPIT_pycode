"""
pc_diagnostic.py  —  PC Diagnostic Tool
Receives CAN frames from Raspberry Pi ECU via PCAN-USB.
Simple terminal print + CSV logging. No dashboard.
"""

import can
import csv
import struct
from datetime import datetime

# ── Config ─────────────────────────────────────────────────────
CAN_INTERFACE = "pcan"
CAN_CHANNEL   = "PCAN_USBBUS1"
BITRATE       = 500_000
LOG_FILE      = "pc_received.csv"

# CAN Message IDs
MSG_VEHICLE_SPEED = 0x100
MSG_ENGINE_RPM    = 0x101
MSG_ENGINE_TEMP   = 0x102
MSG_SENSOR_DATA   = 0x200
MSG_HEARTBEAT     = 0x7FF

# Diagnostic thresholds
THRESHOLDS = {
    "speed_kph": (0,    160),
    "rpm":       (600,  7000),
    "temp_c":    (-20,  120),
    "voltage_v": (10.5, 15.5),
    "accel_x_g": (-1.5, 1.5),
    "accel_y_g": (-1.0, 1.0),
}

DTC_TABLE = {
    "speed_kph": "P0500",
    "rpm":       "P0335",
    "temp_c":    "P0115",
    "voltage_v": "P0560",
    "accel_x_g": "P0170",
    "accel_y_g": "P0170",
}

# ── CSV Setup ───────────────────────────────────────────────────
csv_file = open(LOG_FILE, "w", newline="")
writer   = csv.writer(csv_file)
writer.writerow([
    "timestamp",      # str   — date and time of received frame
    "can_id_hex",     # str   — CAN message ID in hex  e.g. 0x100
    "can_id_dec",     # int   — CAN message ID in decimal e.g. 256
    "signal_name",    # str   — human readable signal name
    "value",          # float — decoded signal value
    "unit",           # str   — unit of the value
    "status",         # str   — OK or FAULT
    "dtc",            # str   — DTC code if fault, else empty
    "raw_data_hex",   # str   — raw bytes of CAN frame in hex
])

# ── Decoders (Fixed for explicit bounds handling) ─────────────────────────────
def decode_speed(data):
    if len(data) < 8: return 0.0
    raw, _ = struct.unpack(">HxxxxH", data[:8])
    return raw / 10.0

def decode_rpm(data):
    if len(data) < 8: return 0.0
    raw, = struct.unpack(">Hxxxxxx", data[:8])
    return raw / 4.0

def decode_temp(data):
    if len(data) < 1: return 0.0
    return data[0] - 40

def decode_sensor(data):
    if len(data) < 8: return 0.0, 0.0, 0.0
    ax, ay, vv = struct.unpack(">hhHxx", data[:8])
    return ax / 1000.0, ay / 1000.0, vv / 1000.0

def decode_heartbeat(data):
    if len(data) < 8: return 0
    count, = struct.unpack(">Ixxxx", data[:8])
    return count

# ── Fault Check ─────────────────────────────────────────────────
def check_fault(signal, value):
    if signal not in THRESHOLDS:
        return "OK", ""
    lo, hi = THRESHOLDS[signal]
    if value < lo or value > hi:
        return "FAULT", DTC_TABLE.get(signal, "P9999")
    return "OK", ""

# ── Log one signal row ──────────────────────────────────────────
def log_row(ts, msg_id, signal, value, unit, raw_hex):
    status, dtc = check_fault(signal, value)
    writer.writerow([ts, hex(msg_id), msg_id, signal, round(value, 3), unit, status, dtc, raw_hex])
    csv_file.flush()
    fault_tag = f"   *** FAULT {dtc} ***" if status == "FAULT" else ""
    print(f"[{ts}]  ID={hex(msg_id)}  {signal:<14} = {value:>10.3f} {unit:<6}  {status}{fault_tag}")

# ── Main ────────────────────────────────────────────────────────
print("Starting PC Diagnostic Tool")
print(f"Interface : {CAN_CHANNEL} @ {BITRATE // 1000} kbps")
print(f"CSV log   : {LOG_FILE}")
print("-" * 70)

try:
    bus = can.interface.Bus(interface=CAN_INTERFACE,
                            channel=CAN_CHANNEL,
                            bitrate=BITRATE)
except can.CanError as e:
    print(f"ERROR: Cannot open PCAN-USB: {e}")
    print("Check: PCAN drivers installed? Dongle connected?")
    csv_file.close()
    exit(1)

# --- NEW: Aggressive Buffer Flush ---
print("Flushing old messages from the PCAN buffer...")
while True:
    # Read with a tiny timeout. If it returns None, the buffer is empty.
    if bus.recv(timeout=0.1) is None:
        break

print("Buffer cleared. Waiting for live frames from Raspberry Pi ECU...\n")

try:
    for msg in bus:
        ts      = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        msg_id  = msg.arbitration_id
        data    = bytes(msg.data)
        raw_hex = data.hex(" ").upper()

        # Check frame size minimums before executing decode sequences
        if len(data) < 8:
            print(f"[{ts}]  ID={hex(msg_id)} Warning: Dropping malformed short frame ({len(data)} bytes).")
            continue

        if msg_id == MSG_VEHICLE_SPEED:
            log_row(ts, msg_id, "speed_kph", decode_speed(data),      "km/h",  raw_hex)

        elif msg_id == MSG_ENGINE_RPM:
            log_row(ts, msg_id, "rpm",        decode_rpm(data),        "rpm",   raw_hex)

        elif msg_id == MSG_ENGINE_TEMP:
            log_row(ts, msg_id, "temp_c",     decode_temp(data),       "C",     raw_hex)

        elif msg_id == MSG_SENSOR_DATA:
            ax, ay, vv = decode_sensor(data)
            log_row(ts, msg_id, "accel_x_g",  ax,                      "g",     raw_hex)
            log_row(ts, msg_id, "accel_y_g",  ay,                      "g",     raw_hex)
            log_row(ts, msg_id, "voltage_v",  vv,                      "V",     raw_hex)

        elif msg_id == MSG_HEARTBEAT:
            count = decode_heartbeat(data)
            print(f"[{ts}]  ID={hex(msg_id)}  heartbeat_count  = {count:>10}        ---")
            writer.writerow([ts, hex(msg_id), msg_id, "heartbeat_count", count, "count", "OK", "", raw_hex])
            csv_file.flush()

        else:
            print(f"[{ts}]  ID={hex(msg_id)}  unknown frame    raw={raw_hex}")

except KeyboardInterrupt:
    print("\nStopped.")
finally:
    bus.shutdown()
    csv_file.close()
    print(f"CSV saved to {LOG_FILE}")