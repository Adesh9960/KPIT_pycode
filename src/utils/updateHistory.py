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


def update_history(data):
    history["time"].append(data.get("time"))
    history["speed"].append(data.get("speed", 0))
    history["rpm"].append(data.get("rpm", 0))
    history["coolant"].append(data.get("coolant", 0))
    history["oil_temp"].append(data.get("oil_temp", 0))
    history["fuel_pct"].append(data.get("fuel_pct", 0))
    history["fuel_rate"].append(data.get("fuel_rate", 0))
    history["throttle"].append(data.get("throttle_pct", 0))
    history["engine_load"].append(data.get("engine_load", 0))
    history["accel"].append(data.get("accel_ms2", 0))
    history["battery"].append(
        data.get("battery_v", data.get("voltage", 0))
    )
    history["gear_num"].append(data.get("gear_num", 0))
    history["gear"].append(data.get("gear", "N"))
    history["engine_state"].append(
        data.get("engine_state", "UNKNOWN")
    )

    # keep fixed size
    for key in history:
        if len(history[key]) > MAX_HISTORY:
            history[key].pop(0)