# frontend field mapping
SIGNAL_MAP = {
    "Speed_kmh": "speed",
    "Engine_RPM": "rpm",
    "Throttle_Pct": "throttle_pct",
    "Coolant_Temp_C": "coolant_temp",
    "Oil_Temp_C": "oil_temp",
    "Ambient_Temp_C": "ambient_temp",
    "Battery_V": "battery_v",
    "Accel_ms2": "accel",
    "Gear_Num": "gear_num",
    "Engine_Load_Pct": "engine_load",
    "Fuel_Rate_mL_s": "fuel_rate",
    "Remaining_Fuel_L": "fuel_l",
    "Fuel_Pct": "fuel_pct",
    "Distance_km": "distance_km",
    "Tyre_P_FL": "tyre_p_fl",
    "Tyre_P_FR": "tyre_p_fr",
    "Tyre_P_RL": "tyre_p_rl",
    "Tyre_P_RR": "tyre_p_rr",
    "Stall_Risk": "stall_risk"
}

def build_analytics_packet(decoded_frame):
    analytics = {}

    for signal_name, value in decoded_frame["signals"].items():
        frontend_key = SIGNAL_MAP.get(signal_name)

        if frontend_key:
            analytics[frontend_key] = value

    return analytics