MAX_HISTORY = 10000

history = {
    "time": [],
    "speed": [],
    "rpm": [],
    "coolant": [],
    "oil_temp": [],
    "fuel_pct": [],
    "fuel_rate": [],
    "throttle": [],
    "engine_load": [],
    "accel": [],
    "battery": [],
    "gear_num": [],
    "gear": [],
    "engine_state": []
}

def append_or_repeat(key, value):
    if value is None:
        value = history[key][-1] if history[key] else 0
    history[key].append(value)

def update_history(data):
    append_or_repeat("speed", data.get("speed"))
    append_or_repeat("rpm", data.get("rpm"))
    append_or_repeat("coolant", data.get("coolant"))
    append_or_repeat("oil_temp", data.get("oil_temp"))
    append_or_repeat("fuel_pct", data.get("fuel_pct"))
    append_or_repeat("fuel_rate", data.get("fuel_rate"))
    append_or_repeat("throttle", data.get("throttle_pct"))
    append_or_repeat("engine_load", data.get("engine_load"))
    append_or_repeat("accel", data.get("accel_ms2"))
    append_or_repeat("battery", data.get("battery_v", data.get("voltage")))
    append_or_repeat("gear_num", data.get("gear_num"))
    append_or_repeat("gear", data.get("gear"))
    append_or_repeat("engine_state", data.get("engine_state"))
    # keep fixed size
    for key in history:
        if len(history[key]) > MAX_HISTORY:
            history[key].pop(0)