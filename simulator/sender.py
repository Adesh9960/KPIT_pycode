"""
in_out.py  —  Raspberry Pi ECU Simulator
Transmits CAN frames via can0 (MCP2515) at 500 kbps.
Simple terminal print + CSV logging. No dashboard.
"""

import can
import csv
import time
import struct
import random
from datetime import datetime

# ── Config ─────────────────────────────────────────────────────
CAN_INTERFACE = "socketcan"
CAN_CHANNEL   = "can0"
BITRATE       = 500_000
SEND_INTERVAL = 0.1          # send every 100 ms
LOG_FILE      = "ecu_transmitted.csv"

# CAN Message IDs
MSG_VEHICLE_SPEED = 0x100
MSG_ENGINE_RPM    = 0x101
MSG_ENGINE_TEMP   = 0x102
MSG_SENSOR_DATA   = 0x200
MSG_HEARTBEAT     = 0x7FF

# ── CSV Setup ───────────────────────────────────────────────────
csv_file = open(LOG_FILE, "w", newline="")
writer   = csv.writer(csv_file)
# Fixed header mapping to support direct per-frame entry tracking cleanly
writer.writerow([
    "timestamp",          # str      — date and time
    "can_id_hex",         # str      — CAN message ID in hex
    "can_id_dec",         # int      — CAN message ID in decimal
    "speed_kph",          # float    — vehicle speed in km/h (or empty)
    "rpm",                # float    — engine RPM (or empty)
    "temp_c",             # float    — coolant temperature in Celsius (or empty)
    "accel_x_g",          # float    — acceleration X axis in g (or empty)
    "accel_y_g",          # float    — acceleration Y axis in g (or empty)
    "voltage_v",          # float    — battery voltage in Volts (or empty)
    "heartbeat_count",    # int      — rolling counter (or empty)
    "raw_data_hex",       # str      — raw CAN frame bytes in hex
])

# ── Message Builders ────────────────────────────────────────────
def build_speed(speed):
    return struct.pack(">HxxxxH", int(speed * 10), 0xAAAA)

def build_rpm(rpm):
    return struct.pack(">Hxxxxxx", int(rpm * 4))

def build_temp(temp):
    return bytes([int(temp + 40) & 0xFF, 0, 0, 0, 0, 0, 0, 0])

def build_sensor(ax, ay, voltage):
    return struct.pack(">hhHxx", int(ax * 1000), int(ay * 1000), int(voltage * 1000))

def build_heartbeat(count):
    return struct.pack(">Ixxxx", count & 0xFFFFFFFF)

# ── ECU State ───────────────────────────────────────────────────
speed   = 0.0
rpm     = 800.0
temp    = 20.0
voltage = 12.6
tick    = 0
hb      = 0

# ── Main ────────────────────────────────────────────────────────
print("Starting Raspberry Pi ECU Simulator")
print(f"CAN interface : {CAN_CHANNEL} @ {BITRATE // 1000} kbps")
print(f"CSV log       : {LOG_FILE}")
print("-" * 60)

try:
    bus = can.interface.Bus(interface=CAN_INTERFACE,
                            channel=CAN_CHANNEL,
                            bitrate=BITRATE)
except Exception as e:
    print(f"ERROR: Cannot open {CAN_CHANNEL}: {e}")
    print("Run: sudo ip link set can0 type can bitrate 500000 && sudo ip link set up can0")
    csv_file.close()
    exit(1)

print("CAN bus open. Transmitting...\n")

try:
    while True:
        tick += 1
        now   = datetime.now()
        ts    = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        cycle = (tick * SEND_INTERVAL) % 60

        # Simulate drive cycle
        if cycle < 20:
            accel = 2.5
        elif cycle < 35:
            accel = 0.0
        elif cycle < 50:
            accel = -2.0
        else:
            accel = -5.0

        speed   = max(0.0, min(140.0, speed + accel * SEND_INTERVAL))
        rpm     = max(750, min(6500, 800 + speed * 30 + random.uniform(-50, 50)))
        temp    = min(90.0, temp + 0.05)
        accel_x = accel / 9.81 + random.gauss(0, 0.005)
        accel_y = random.gauss(0, 0.003)
        voltage = 13.8 + random.gauss(0, 0.05) if rpm > 800 else 12.6

        # Build each frame
        frames = [
            (MSG_VEHICLE_SPEED, build_speed(speed)),
            (MSG_ENGINE_RPM,    build_rpm(rpm)),
            (MSG_ENGINE_TEMP,   build_temp(temp)),
            (MSG_SENSOR_DATA,   build_sensor(accel_x, accel_y, voltage)),
        ]

        # Heartbeat every 1 s
        if tick % 10 == 0:
            hb += 1
            frames.append((MSG_HEARTBEAT, build_heartbeat(hb)))

        # Transmit and log each frame independently to maintain CSV structural integrity
        for msg_id, data in frames:
            msg = can.Message(arbitration_id=msg_id,
                              data=data,
                              is_extended_id=False)
            try:
                bus.send(msg, timeout=0.01)
            except can.CanError as e:
                print(f"  Send error 0x{msg_id:03X}: {e}")

            # Prepare fields contextually to match the CSV columns precisely
            raw_hex = " ".join(f"{b:02X}" for b in data)
            row = [ts, f"0x{msg_id:03X}", msg_id, "", "", "", "", "", "", "", raw_hex]

            if msg_id == MSG_VEHICLE_SPEED:
                row[3] = round(speed, 2)
            elif msg_id == MSG_ENGINE_RPM:
                row[4] = round(rpm, 1)
            elif msg_id == MSG_ENGINE_TEMP:
                row[5] = round(temp, 2)
            elif msg_id == MSG_SENSOR_DATA:
                row[6] = round(accel_x, 4)
                row[7] = round(accel_y, 4)
                row[8] = round(voltage, 3)
            elif msg_id == MSG_HEARTBEAT:
                row[9] = hb

            writer.writerow(row)
        
        csv_file.flush()

        # Terminal Printout
        print(f"[{ts}]  "
              f"spd={speed:6.1f} km/h  "
              f"rpm={rpm:6.0f}  "
              f"tmp={temp:5.1f}C  "
              f"bat={voltage:.2f}V  "
              f"ax={accel_x:+.3f}g  "
              f"ay={accel_y:+.3f}g  "
              + (f"HB#{hb}" if tick % 10 == 0 else ""))

        time.sleep(SEND_INTERVAL)

except KeyboardInterrupt:
    print("\nStopped.")
finally:
    bus.shutdown()
    csv_file.close()
    print(f"CSV saved to {LOG_FILE}")