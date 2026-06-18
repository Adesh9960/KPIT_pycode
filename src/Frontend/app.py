from flask import Flask, render_template, jsonify
import pandas as pd
import os
import csv
import io

app = Flask(__name__)

CSV_FILE = r"D:\Programming\Projects\Data_Generation\engine_telemetry_log.csv"

# New CSV column order from Updated_parameter_2.py
# 0  System_Time
# 1  Gear
# 2  Gear_Num
# 3  Speed_kmh
# 4  Engine_RPM
# 5  Coolant_Temp_C
# 6  Oil_Temp_C
# 7  Ambient_Temp_C
# 8  Fuel_Rate_mL_s
# 9  Remaining_Fuel_L
# 10 Fuel_Pct
# 11 Distance_km
# 12 Accel_ms2
# 13 Engine_Load_Pct
# 14 Throttle_Pct
# 15 Rev_Limiter
# 16 Engine_State
# 17 Stall_Risk
# 18 Clutch_State
# 19 Brake_State
# 20 Battery_V
# 21 Tyre_P_FL
# 22 Tyre_P_FR
# 23 Tyre_P_RL
# 24 Tyre_P_RR

COL = {
    "time": 0, "gear": 1, "gear_num": 2, "speed": 3, "rpm": 4,
    "coolant": 5, "oil_temp": 6, "ambient": 7,
    "fuel_rate": 8, "fuel_l": 9, "fuel_pct": 10,
    "distance": 11, "accel": 12, "engine_load": 13, "throttle": 14,
    "rev_lim": 15, "engine_state": 16, "stall_risk": 17,
    "clutch": 18, "brake": 19, "battery": 20,
    "tyre_fl": 21, "tyre_fr": 22, "tyre_rl": 23, "tyre_rr": 24,
}


def tail_rows(path, n=2):
    """Read only the last n data rows via binary seek — O(1) regardless of file size."""
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        file_size = f.tell()
        block = 2048
        data = b""
        while file_size > 0 and data.count(b"\n") <= n + 1:
            read_size = min(block, file_size)
            f.seek(file_size - read_size)
            chunk = f.read(read_size)
            data = chunk + data
            file_size -= read_size

    lines = [l for l in data.decode(errors="ignore").splitlines() if l.strip()]
    rows = []
    for line in reversed(lines):
        if line.startswith("System_Time"):
            break
        for row in csv.reader(io.StringIO(line)):
            if row and len(row) >= 5:
                rows.insert(0, row)
        if len(rows) >= n:
            break
    return rows


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


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/live-data")
def live_data():
    """
    Fast endpoint — tail-reads only the last 2 rows.
    Reads all real values directly from the new CSV schema.
    No re-derivation needed.
    """
    if not os.path.exists(CSV_FILE):
        return jsonify({"error": "CSV file not found"})

    rows = tail_rows(CSV_FILE, n=2)
    if not rows:
        return jsonify({"error": "No data yet"})

    r = rows[-1]   # latest row

    def g(col_key):
        idx = COL.get(col_key, -1)
        return r[idx] if 0 <= idx < len(r) else ""

    return jsonify({
        "time":         g("time"),
        "gear":         g("gear"),
        "gear_num":     safe_int(g("gear_num")),
        "speed":        safe_float(g("speed")),
        "rpm":          safe_int(g("rpm")),
        "coolant_temp": safe_float(g("coolant")),
        "oil_temp":     safe_float(g("oil_temp")),
        "ambient_temp": safe_float(g("ambient")),
        "fuel_rate":    safe_float(g("fuel_rate")),
        "fuel_l":       safe_float(g("fuel_l")),
        "fuel_pct":     safe_float(g("fuel_pct")),
        "distance_km":  safe_float(g("distance")),
        "accel":        safe_float(g("accel")),
        "engine_load":  safe_float(g("engine_load")),
        "throttle_pct": safe_float(g("throttle")),
        "rev_limiter":  safe_int(g("rev_lim")),
        "engine_state": g("engine_state"),
        "stall_risk":   safe_int(g("stall_risk")),
        "clutch":       g("clutch"),
        "brake":        g("brake"),
        "battery_v":    safe_float(g("battery")),
        "tyre_pressure": {
            "fl": safe_float(g("tyre_fl")),
            "fr": safe_float(g("tyre_fr")),
            "rl": safe_float(g("tyre_rl")),
            "rr": safe_float(g("tyre_rr")),
        },
    })


@app.route("/csv-data")
def csv_data():
    """Full CSV read for history mode charts and table."""
    if not os.path.exists(CSV_FILE):
        return jsonify({"error": "CSV file not found"})

    df = pd.read_csv(CSV_FILE)

    def col(name):
        return df[name].tolist() if name in df.columns else []

    return jsonify({
        "time":         col("System_Time"),
        "gear":         col("Gear"),
        "gear_num":     col("Gear_Num"),
        "speed":        col("Speed_kmh"),
        "rpm":          col("Engine_RPM"),
        "coolant":      col("Coolant_Temp_C"),
        "oil_temp":     col("Oil_Temp_C"),
        "fuel_rate":    col("Fuel_Rate_mL_s"),
        "fuel_pct":     col("Fuel_Pct"),
        "fuel_l":       col("Remaining_Fuel_L"),
        "distance":     col("Distance_km"),
        "accel":        col("Accel_ms2"),
        "throttle":     col("Throttle_Pct"),
        "engine_load":  col("Engine_Load_Pct"),
        "engine_state": col("Engine_State"),
        "battery":      col("Battery_V"),
    })


if __name__ == "__main__":
    app.run(debug=True)
