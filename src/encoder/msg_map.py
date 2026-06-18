MESSAGE_MAP = {
    "VehicleData": {
        "can_id": 0x100,
        "is_extended": False,
        "is_fd": False,
        "dlc": 8,
        "signals": {
            "Speed_kmh":    "Speed_kmh",
            "Engine_RPM":   "Engine_RPM",
            "Throttle_Pct": "Throttle_Pct",
            "Stall_Risk": "Stall_Risk"
        }
    },
    "TempData": {
        "can_id": 0x200,
        "is_extended": False,
        "is_fd": False,
        "dlc": 8,
        "signals": {
            "Coolant_Temp_C": "Coolant_Temp_C",
            "Oil_Temp_C":     "Oil_Temp_C",
            "Ambient_Temp_C": "Ambient_Temp_C"
        }
    },
    "BatteryData": {
        "can_id": 0x1CFFC1A2,
        "is_extended": True,
        "is_fd": False,
        "dlc": 8,
        "signals": {
            "Throttle_Pct": "Throttle_Pct",
            "Accel_ms2":    "Accel_ms2",
            "Battery_V":    "Battery_V"
        }
    },
    "GearboxData": {
        "can_id": 0x1CFFE100,
        "is_extended": True,
        "is_fd": False,
        "dlc": 8,
        "signals": {
            "Speed_kmh":       "Speed_kmh",
            "Engine_RPM":      "Engine_RPM",
            "Gear_Num":        "Gear_Num",
            "Engine_Load_Pct": "Engine_Load_Pct"
        }
    },
    "TransmissionData": {
        "can_id": 0x1CFFE200,
        "is_extended": True,
        "is_fd": False,
        "dlc": 8,
        "signals": {
            "Speed_kmh":        "Speed_kmh",
            "Fuel_Rate_mL_s":   "Fuel_Rate_mL_s",
            "Remaining_Fuel_L": "Remaining_Fuel_L",
            "Fuel_Pct":         "Fuel_Pct"
        }
    },
    "DrivelineData": {
        "can_id": 0x1CFFE300,
        "is_extended": True,
        "is_fd": False,
        "dlc": 8,
        "signals": {
            "Speed_kmh":  "Speed_kmh",
            "Engine_RPM": "Engine_RPM",
            "Distance_km": "Distance_km"
        }
    },
    "TyreData": {
        "can_id": 0x400,
        "is_extended": False,
        "is_fd": False,
        "dlc": 8,
        "signals": {
            "Tyre_P_FL": "Tyre_P_FL",
            "Tyre_P_FR": "Tyre_P_FR",
            "Tyre_P_RL": "Tyre_P_RL",
            "Tyre_P_RR": "Tyre_P_RR"
        }
    }
}