from collections import deque
MAX_HISTORY = 10000

history = {
    "time": deque(maxlen=MAX_HISTORY),
    "speed": deque(maxlen=MAX_HISTORY),
    "rpm": deque(maxlen=MAX_HISTORY),
    "coolant": deque(maxlen=MAX_HISTORY),
    "oil_temp": deque(maxlen=MAX_HISTORY),
    "fuel_pct": deque(maxlen=MAX_HISTORY),
    "fuel_rate": deque(maxlen=MAX_HISTORY),
    "throttle": deque(maxlen=MAX_HISTORY),
    "engine_load": deque(maxlen=MAX_HISTORY),
    "accel": deque(maxlen=MAX_HISTORY),
    "battery": deque(maxlen=MAX_HISTORY),
    "gear_num": deque(maxlen=MAX_HISTORY),
    "gear": deque(maxlen=MAX_HISTORY),
    "engine_state": deque(maxlen=MAX_HISTORY)
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
