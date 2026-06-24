import time
import json
import os
import csv
import base64
import ecu_state
import io
import secrets
import zlib
from flask import Flask, Response, jsonify, render_template, request
from flask_cors import CORS
import pandas as pd
from datetime import datetime
import collections
import struct

# RAM Storage for Live Telemetry
CURRENT_TELEMETRY = {}

# Rolling buffer for the History Tab (keeps the last 500 records in RAM)
HISTORY_BUFFER = collections.deque(maxlen=500)

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)
CORS(app)



def safe_float(val, default=0.0):
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def safe_int(val, default=0):
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default
    
# ═══════════════════════════════════════════════════════════════
#  PROGRAMMING TERMINAL (/prog/*) ENDPOINTS
# ═══════════════════════════════════════════════════════════════
import threading
import random

# Mock state for the programming terminal
PG_STATE = {
    "files": {"original": None, "modified": None},
    "flash": {"status": "idle", "progress": 0, "operation": "", "voltage": 13.8, "connection": "CAN 500k", "elapsed": 0},
    "features": {"launch_control": False, "pops_and_bangs": False, "hard_rev_cut": False},
    "security_extras": {"immo_disabled": False, "component_protection": True, "keys_programmed": 2},
    "dtc_cleared_count": 0
}

@app.route("/prog/ecu_info")
def prog_ecu_info():
    return jsonify({"status": "success", "data": {
        "part_number": "03L 906 018 AB",
        "software_version": "1037508931",
        "hardware_version": "EDC17C46",
        "vin": "WVWZZZ1KZAW000001",
        "serial_number": "BOSCH-192837465",
        "manufacturer": "Bosch GmbH",
        "protocols": "UDS, KWP2000, CAN",
        "memory_type": "TriCore TC1767 (2MB Flash)",
        "bootloader_version": "v1.44"
    }})

@app.route("/prog/security_access/<int:step>")
def prog_security(step):
    import ecu_state
    if step == 1:
        # Seed request
        seed = secrets.token_hex(4).upper()
        ecu_state._pending_seed = seed
        return jsonify({"status": "success", "message": seed})
    elif step == 2:
        # Key verify (Auto-approve for simulation)
        ecu_state.security_level = 2
        return jsonify({"status": "success"})

@app.route("/prog/read_ecu", methods=["POST"])
def prog_read_ecu():
    PG_STATE["files"]["original"] = {"name": "Original_Backup.bin", "size_kb": 2048, "checksum": "8F4C2A11"}
    return jsonify({"status": "success", "data": PG_STATE["files"]["original"]})

@app.route("/prog/select_modified_file", methods=["POST"])
def prog_select_file():
    tag = request.json.get("label", "Stage1")
    PG_STATE["files"]["modified"] = {"name": f"EDC17C46_{tag.capitalize()}.bin", "size_kb": 2048, "checksum": secrets.token_hex(4).upper()}
    return jsonify({"status": "success", "data": PG_STATE["files"]["modified"]})

@app.route("/prog/start_flash", methods=["POST"])
def prog_start_flash():
    import ecu_state
    if ecu_state.security_level < 2:
        return jsonify({"status": "error", "message": "Security Access Required"})
    if not PG_STATE["files"]["modified"]:
        return jsonify({"status": "error", "message": "No modified file selected. Run file.select first."})
    
    # Reset and start simulation thread
    PG_STATE["flash"] = {"status": "erasing", "progress": 0, "operation": "Erasing Sector 1...", "voltage": 13.6, "connection": "CAN 500k", "elapsed": 0}
    
    def simulate_flash():
        # Erase phase
        for i in range(10, 101, 20):
            time.sleep(1)
            PG_STATE["flash"].update({"progress": i, "operation": f"Erasing Sector {i//10}..."})
        
        # Write phase
        PG_STATE["flash"].update({"status": "writing", "progress": 0, "operation": "Writing blocks..."})
        for i in range(0, 101, 5):
            time.sleep(0.3)
            # Randomize voltage drop slightly to simulate load
            v = round(random.uniform(13.2, 13.8), 1)
            PG_STATE["flash"].update({"progress": i, "operation": f"Writing block 0x{i*1000:04X}...", "voltage": v})
            
        # Verify phase
        PG_STATE["flash"].update({"status": "verifying", "progress": 0, "operation": "Verifying checksums..."})
        for i in range(0, 101, 33):
            time.sleep(0.5)
            PG_STATE["flash"].update({"progress": i})
            
        PG_STATE["flash"].update({"status": "success", "progress": 100, "operation": "Flash complete"})
        
    threading.Thread(target=simulate_flash, daemon=True).start()
    return jsonify({"status": "success"})

@app.route("/prog/flash_status")
def prog_flash_status():
    return jsonify(PG_STATE["flash"])

@app.route("/prog/state")
def prog_state():
    import ecu_state
    return jsonify({"status": "success", "data": {
        "session": ecu_state.session_level,
        "security": {"level": ecu_state.security_level},
        **PG_STATE
    }})

@app.route("/prog/feature_coding", methods=["POST"])
def prog_feature():
    data = request.get_json()
    feat = data.get("feature")
    val = data.get("value")
    PG_STATE["features"][feat] = val
    return jsonify({"status": "success"})

@app.route("/prog/security_extras", methods=["POST"])
def prog_sec_extras():
    action = request.json.get("action")
    if action == "disable_immo": PG_STATE["security_extras"]["immo_disabled"] = True
    elif action == "enable_immo": PG_STATE["security_extras"]["immo_disabled"] = False
    elif action == "remove_cp": PG_STATE["security_extras"]["component_protection"] = False
    elif action == "restore_cp": PG_STATE["security_extras"]["component_protection"] = True
    elif action == "program_key": PG_STATE["security_extras"]["keys_programmed"] += 1
    return jsonify({"status": "success", "data": PG_STATE["security_extras"]})

@app.route("/prog/bench_flash", methods=["POST"])
def prog_bench():
    step = request.json.get("step")
    tool = request.json.get("tool")
    return jsonify({"status": "success", "data": f"{step} via {tool} completed."})

@app.route("/prog/clear_dtc", methods=["POST"])
def prog_clear_dtc():
    PG_STATE["dtc_cleared_count"] += 1
    return jsonify({"status": "success"})

@app.route("/prog/exit_session", methods=["POST"])
def prog_exit():
    import ecu_state
    from uds.Session import SESSION_EXTENDED
    ecu_state.session_level = SESSION_EXTENDED
    ecu_state.security_level = 0
    return jsonify({"status": "success"})


# ═══════════════════════════════════════════════════════════════
#  SSE STREAM
# ═══════════════════════════════════════════════════════════════
def generate_stream():
    """Streams the RAM data to the dashboard via Server-Sent Events (SSE)"""
    last_time = None

    while True:
        # Check if we have data in RAM
        if not CURRENT_TELEMETRY:
            time.sleep(0.1)
            continue

        current_time = CURRENT_TELEMETRY.get("time")

        # Only send to the frontend if the time has ticked forward
        if current_time != last_time:
            try:
                # No more parsing CSV rows! Just send the JSON directly.
                yield f"data: {json.dumps(CURRENT_TELEMETRY)}\n\n"
                last_time = current_time
            except Exception as e:
                print("❌ Payload error:", e)

        time.sleep(0.1) # 10 Hz refresh rate for smooth gauges


@app.route("/internal/update_telemetry", methods=["POST"])
def update_telemetry():
    """Hidden endpoint where Parameters.py pushes live data."""
    global CURRENT_TELEMETRY
    
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No data received"}), 400

    # Save to RAM for the UI stream
    CURRENT_TELEMETRY = data
    HISTORY_BUFFER.append(data)

    # ─── UPDATE didList.py DATABASE ───
    # This ensures UDS 0x22 requests read live hardware data!
    from dids.didList import DID_DATABASE
    live_dids = data.get("live_dids", {})

    # 0xF401: Speed (2 Bytes -> ">H")
    if "0xF401" in live_dids and 0xF401 in DID_DATABASE:
        DID_DATABASE[0xF401].value = struct.pack(">H", live_dids["0xF401"])
        
    # 0xF402: RPM (2 Bytes -> ">H")
    if "0xF402" in live_dids and 0xF402 in DID_DATABASE:
        DID_DATABASE[0xF402].value = struct.pack(">H", live_dids["0xF402"])
        
    # 0xF403: Coolant Temp (1 Byte -> ">B")
    if "0xF403" in live_dids and 0xF403 in DID_DATABASE:
        DID_DATABASE[0xF403].value = struct.pack(">B", live_dids["0xF403"] & 0xFF)
        
    # 0xF406: Battery Voltage (Scaled by 10, 2 Bytes -> ">H")
    # Example: 12.5V becomes 125
    if "0xF406" in live_dids and 0xF406 in DID_DATABASE:
        bat_scaled = int(live_dids["0xF406"] * 10)
        DID_DATABASE[0xF406].value = struct.pack(">H", bat_scaled)

    return jsonify({"status": "success"})
# ═══════════════════════════════════════════════════════════════
# REAL-TIME LIVE STREAM (SSE)
# ═══════════════════════════════════════════════════════════════
@app.route("/stream")
def stream():
    """Pushes live data to the browser automatically (No refresh needed)"""
    def generate():
        import json
        import time
        
        while True:
            # If we have data in RAM, push it to the frontend
            if CURRENT_TELEMETRY:
                try:
                    yield f"data: {json.dumps(CURRENT_TELEMETRY)}\n\n"
                except Exception as e:
                    print("Stream error:", e)
                    
            # Wait 0.1 seconds (10 Hz refresh rate for smooth UI)
            time.sleep(0.1)

    # The headers here are CRITICAL to stop the browser from pausing the connection
    return Response(generate(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no"
    })



# ═══════════════════════════════════════════════════════════════
#  LIVE-DATA  (polling fallback)
# ═══════════════════════════════════════════════════════════════
@app.route("/live-data")
def live_data():
    """Polling fallback for live data (Reads from RAM)."""
    global CURRENT_TELEMETRY
    
    if not CURRENT_TELEMETRY:
        return jsonify({"error": "No telemetry data available yet. Is Parameters.py running?"}), 503
        
    return jsonify(CURRENT_TELEMETRY)

# ═══════════════════════════════════════════════════════════════
#  HISTORY  (full CSV, column-based, for History tab charts)
# ═══════════════════════════════════════════════════════════════
@app.route("/history")
def history():
    """Returns the rolling buffer of historical data for the dashboard charts."""
    global HISTORY_BUFFER
    
    if not HISTORY_BUFFER:
        return jsonify([]) # Return empty list if no data yet
        
    # The frontend expects a list of dictionaries, which our deque already is!
    return jsonify(list(HISTORY_BUFFER))


@app.route("/csv-data")
def csv_data():
    return history()


# ═══════════════════════════════════════════════════════════════
#  UDS ENDPOINTS  —  REST API for the Technician / Programming tabs
# ═══════════════════════════════════════════════════════════════

# Mapping of live-telemetry DIDs
LIVE_DID_MAP = {
    0xF401: "speed",
    0xF402: "rpm",
    0xF403: "coolant",
    0xF404: "oil_temp",
    0xF405: "fuel_pct",
    0xF406: "battery",
    0xF407: "engine_load",
    0xF408: "throttle",
    0xF409: "gear_num",
    0xF40A: "fuel_rate",
}


# ═══════════════════════════════════════════════════════════════
# CLEAR DTCs (0x14)
# ═══════════════════════════════════════════════════════════════
@app.route("/clear_dtcs", methods=["POST"])
def clear_dtcs():
    """Clear Diagnostic Information (0x14)"""
    if ecu_state.session_level not in [ecu_state.SESSION_EXTENDED, ecu_state.SESSION_PROGRAMMING]:
        return jsonify({"status": "error", "message": "0x7F 0x14 0x7F — SubFunctionNotSupportedInActiveSession"})
    
    # Clear the internal state
    ecu_state.active_dtcs.clear()
    
    # Optional: Write a flag to a JSON file if Parameters.py needs to know DTCs were cleared
    return jsonify({"status": "success", "message": "0x54 — DTCs cleared"})


# ═══════════════════════════════════════════════════════════════
# FIRMWARE FLASHING (0x34, 0x36, 0x37)
# ═══════════════════════════════════════════════════════════════
@app.route("/request_download", methods=["POST"])
def request_download():
    """Request Download (0x34)"""
    if ecu_state.session_level != ecu_state.SESSION_PROGRAMMING:
        return jsonify({"status": "error", "message": "0x7F 0x34 0x7F — conditionsNotCorrect"})

    data = request.get_json()
    file_size = data.get("size", 0)

    if file_size <= 0 or file_size > 5000000: # Arbitrary 5MB limit
        return jsonify({"status": "error", "message": "0x7F 0x34 0x31 — requestOutOfRange"})

    # Initialize the flash state machine
    ecu_state.flash_status = ecu_state.FlashState.DOWNLOADING
    ecu_state.flash_expected_size = file_size
    ecu_state.flash_buffer = bytearray()
    ecu_state.flash_block_sequence = 1 # BSC always starts at 1

    return jsonify({
        "status": "success", 
        "max_block_size": ecu_state.MAX_BLOCK_SIZE,
        "message": "0x74 — Download accepted"
    })


@app.route("/transfer_data", methods=["POST"])
def transfer_data():
    """Transfer Data (0x36) — Handles Binary Blocking"""
    if ecu_state.flash_status != ecu_state.FlashState.DOWNLOADING:
        return jsonify({"status": "error", "message": "0x7F 0x36 0x24 — requestSequenceError"})

    data = request.get_json()
    bsc = data.get("block_sequence_counter")
    b64_data = data.get("data") # Frontend sends chunks as base64 to avoid JSON string encoding issues

    # Sequence tracking: UDS BSC rolls over from 0xFF back to 0x00
    expected_bsc = ecu_state.flash_block_sequence & 0xFF
    
    if bsc != expected_bsc:
        ecu_state.flash_status = ecu_state.FlashState.IDLE # Abort
        return jsonify({"status": "error", "message": f"0x7F 0x36 0x73 — wrongBlockSequenceCounter (Expected {expected_bsc}, got {bsc})"})

    try:
        binary_chunk = base64.b64decode(b64_data)
        ecu_state.flash_buffer.extend(binary_chunk)
        
        # Increment expected sequence for the next block
        ecu_state.flash_block_sequence += 1
        
        return jsonify({"status": "success", "message": f"0x76 {hex(bsc)} — Block accepted"})
    except Exception as e:
        return jsonify({"status": "error", "message": "0x7F 0x36 0x72 — generalProgrammingFailure"})


@app.route("/request_transfer_exit", methods=["POST"])
def request_transfer_exit():
    """Request Transfer Exit (0x37)"""
    if ecu_state.flash_status != ecu_state.FlashState.DOWNLOADING:
        return jsonify({"status": "error", "message": "0x7F 0x37 0x24 — requestSequenceError"})

    # Verify we received all bytes
    if len(ecu_state.flash_buffer) != ecu_state.flash_expected_size:
        ecu_state.flash_status = ecu_state.FlashState.IDLE
        return jsonify({"status": "error", "message": "0x7F 0x37 0x72 — generalProgrammingFailure (Size mismatch)"})

    # Flash successful! 
    # Here you would typically save `ecu_state.flash_buffer` to a .bin file
    with open("flashed_firmware.bin", "wb") as f:
        f.write(ecu_state.flash_buffer)

    ecu_state.flash_status = ecu_state.FlashState.IDLE
    return jsonify({"status": "success", "message": "0x77 — Transfer Exit successful"})



# Replace your existing read_did route
@app.route("/DID/<int:did>")
def read_did(did):
    """Read Data By Identifier (0x22) — returns live or static DID values."""

    # ── Live telemetry DIDs → read latest value from RAM ──
    if did in LIVE_DID_MAP:
        col_key = LIVE_DID_MAP[did]
        if not CURRENT_TELEMETRY:
            return jsonify({"status": "error", "message": "No live telemetry available yet. Is Parameters.py running?"})
        
        # Grab the value directly from the RAM buffer
        val = CURRENT_TELEMETRY.get(col_key, "—")
        return jsonify({"status": "success", "data": val})

    # ── Static identification DIDs → read from DID database ──
    from dids.didList import DID_DATABASE
    did_obj = DID_DATABASE.get(did)
    if did_obj is None:
        return jsonify({
            "status": "error",
            "message": f"DID 0x{did:04X} not supported"
        })

    value = did_obj.value
    try:
        decoded = value.decode('ascii', errors='replace').strip('\x00')
    except Exception:
        decoded = value.hex()

    return jsonify({"status": "success", "data": decoded})


@app.route("/DID", methods=["POST"])
def write_did():
    """Write Data By Identifier (0x2E)."""
    import ecu_state
    data = request.get_json()
    did = data.get("DID")
    value = data.get("value", "")

    from dids.didList import DID_DATABASE, DID_LENGTHS

    did_obj = DID_DATABASE.get(did)
    if did_obj is None:
        return jsonify({"status": "error", "data": "DID not supported"})
    if not did_obj.is_writable:
        return jsonify({"status": "error", "data": "DID is read-only"})

    # Security check
    if ecu_state.security_level < did_obj.security_level:
        return jsonify({"status": "error", "data": "Security access denied"})

    # Length check
    value_bytes = value.encode('ascii') if isinstance(value, str) else bytes(value)
    expected_len = DID_LENGTHS.get(did)
    if expected_len and len(value_bytes) != expected_len:
        return jsonify({
            "status": "error",
            "data": f"Expected {expected_len} bytes, got {len(value_bytes)}"
        })

    did_obj.value = value_bytes
    return jsonify({"status": "success", "data": "Written"})


@app.route("/security_access/<int:level>")
def security_access(level):
    """Security Access (0x27) — seed/key exchange."""
    import ecu_state

    # Odd level → seed request
    if level % 2 == 1:
        seed = secrets.token_bytes(4)
        ecu_state._pending_seed = seed

        # Compute expected key (same algorithms as securityAccess.py)
        if level == 1:
            ecu_state.security_key = bytes(b ^ 0xA5 for b in seed)
        elif level == 3:
            key = bytearray()
            for b in seed:
                rotated = ((b << 3) | (b >> 5)) & 0xFF
                key.append(rotated ^ 0x5C)
            ecu_state.security_key = bytes(key)
        elif level == 5:
            crc = zlib.crc32(seed)
            ecu_state.security_key = crc.to_bytes(4, "big")

        return jsonify({
            "status": "success",
            "message": "0x" + seed.hex().upper()
        })

    # Even level → key verification (auto-approve for simulation)
    else:
        ecu_state.security_level = level // 2
        return jsonify({
            "status": "success",
            "message": "Security access granted"
        })


@app.route("/diagnostics_session_control/<int:session>")
def diagnostics_session_control(session):
    """Diagnostic Session Control (0x10)."""
    import ecu_state
    from uds.Session import SESSION_DEFAULT, SESSION_EXTENDED, SESSION_PROGRAMMING

    match session:
        case 1:
            ecu_state.session_level = SESSION_DEFAULT
            return jsonify({"status": "success", "message": "Default session"})

        case 3:
            ecu_state.session_level = SESSION_EXTENDED
            return jsonify({"status": "success", "message": "Extended session"})

        case 2:
            # Pre-condition checks — vehicle must be stopped & battery > 11 V
            # READ DIRECTLY FROM RAM INSTEAD OF CSV
            speed = float(CURRENT_TELEMETRY.get("speed", 0))
            batt = float(CURRENT_TELEMETRY.get("battery", 13))
            
            if speed > 0:
                return jsonify({
                    "status": "error",
                    "message": "conditionsNotCorrect: vehicle moving"
                })
            if batt <= 11:
                return jsonify({
                    "status": "error",
                    "message": "conditionsNotCorrect: battery voltage too low"
                })

            ecu_state.session_level = SESSION_PROGRAMMING
            return jsonify({"status": "success", "message": "Programming session"})

        case _:
            return jsonify({"status": "error", "message": "Unsupported session type"})


@app.route("/IO_control", methods=["POST"])
def io_control():
    """Input Output Control By Identifier (0x2F)."""
    import ecu_state
    data = request.get_json()
    did = data.get("DID")
    control_param = data.get("control_parameter", 0)
    control_state = data.get("control_state", 0)

    actuator = ecu_state.ACTUATORS_DB.get(did)
    if actuator is None:
        return jsonify({"status": "error", "message": "Actuator not found"})

    if control_param == 0:
        # Return to ECU control
        actuator.control = ecu_state.Control.ECU
        label = "ECU CONTROL"
    else:
        # Short-term adjustment
        actuator.control = ecu_state.Control.ADJUST
        actuator.state = bool(control_state)
        label = "FORCED ON" if control_state else "FORCED OFF"

    return jsonify({
        "status": "success",
        "message": f"{actuator.name}: {label}"
    })

@app.route("/internal/get_overrides", methods=["GET"])
def get_overrides():
    """
    Physics engine (Parameters.py) polls this rapidly to check if the 
    user has forced any actuators via UDS Service 0x2F (IO Control).
    """
    import ecu_state
    overrides = {}
    
    for did, actuator in ecu_state.ACTUATORS_DB.items():
        overrides[str(did)] = {
            "control": actuator.control.value, # 0=ECU, 1=RESET, 2=FREEZE, 3=ADJUST
            "state": actuator.state
        }
        
    return jsonify(overrides)

# ═══════════════════════════════════════════════════════════════
# ECU RESET (0x11)
# ═══════════════════════════════════════════════════════════════
@app.route("/ecu_reset/<int:reset_type>", methods=["POST"])
def ecu_reset(reset_type):
    """ECU Reset (0x11) — Reboots the system and resets diagnostic states."""
    import ecu_state

    if reset_type == 1:  # Hard Reset (0x01)
        # 1. Drop the session back to Default
        ecu_state.session_level = ecu_state.SESSION_DEFAULT
        # 2. Revoke all security access
        ecu_state.security_level = 0
        # 3. Clear any pending firmware uploads
        ecu_state.flash_status = ecu_state.FlashState.IDLE
        
        # NOTE: If you want to literally restart the Parameters.py physics engine,
        # you could write a {"reset": true} flag to a JSON file here for it to read.
        
        return jsonify({
            "status": "success", 
            "message": "0x51 0x01 — Hard Reset Accepted. Rebooting..."
        })
        
    else:
        return jsonify({
            "status": "error", 
            "message": f"0x7F 0x11 0x12 — subFunctionNotSupported ({reset_type})"
        })
# ═══════════════════════════════════════════════════════════════
#  SERVE THE DASHBOARD
# ═══════════════════════════════════════════════════════════════
@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    print("=" * 52)
    print("  ECU Dashboard – http://127.0.0.1:9000")
    print("  Architecture : In-Memory IPC (Webhook)")
    print("  Live Stream  : SSE Active")
    print("  ─── UDS REST Endpoints ───")
    print("  DID Read     : GET /DID/<did>")
    print("  DID Write    : POST /DID")
    print("  Security     : GET /security_access/<level>")
    print("  Session      : GET /diagnostics_session_control/<level>")
    print("  Reset        : POST /ecu_reset/<type>")
    print("=" * 52)
    
    # Start the Flask server
    app.run(host="0.0.0.0", port=9000, debug=True, threaded=True)