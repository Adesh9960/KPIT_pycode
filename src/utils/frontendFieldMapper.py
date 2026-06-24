# frontend field mapping

SIGNAL_MAP = {
    "Gear_Num": "gear_num",
    "Speed_kmh": "speed",
    "Engine_RPM": "rpm",
    "Coolant_Temp_C": "coolant_temp",
    "Oil_Temp_C": "oil_temp",
    "Ambient_Temp_C": "ambient_temp",
    "Fuel_Pct": "fuel_pct",
    "Fuel_Rate_mL_s": "fuel_rate",
    "Remaining_Fuel_L": "fuel_l",
    "Distance_km": "distance_km",
    "Accel_ms2": "accel",
    "Accel_ms2_alt": "accel",
    "Engine_Load_Pct": "engine_load",
    "Throttle_Pct": "throttle_pct",
    "Rev_Limiter": "rev_limiter",
    "engine_state": "engine_state",
    "Stall_Risk": "stall_risk",
    "Clutch_State": "clutch_state",
    "Brake_State": "brake_state",
    "Battery_V": "battery_v",
    "Battery_V_alt": "battery_v"
}


def build_analytics_packet(decoded_frame):
    analytics = {}

    for signal_name, value in decoded_frame["signals"].items():
        frontend_key = SIGNAL_MAP.get(signal_name)

        if frontend_key:
            analytics[frontend_key] = value

    return analytics