"""
MESSAGE_MAP: maps each CAN message name to its frame ID, framing info, and
the signal-name -> telemetry-key mapping used to build/encode that frame.
Generated from Vehicle.dbc — keep in sync if the DBC changes.
"""

MESSAGE_MAP = {

    "PowertrainCore": {
        "can_id": 0x100,
        "is_extended": False,
        "is_fd": False,
        "dlc": 8,
        "signals": {
            "Speed_kmh":    "Speed_kmh",
            "Engine_RPM":   "Engine_RPM",
            "Throttle_Pct": "Throttle_Pct",
            "Stall_Risk":   "Stall_Risk",
            "Accel_ms2":    "Accel_ms2",
        },
    },

    "ThermalElectrical": {
        "can_id": 0x200,
        "is_extended": False,
        "is_fd": False,
        "dlc": 5,
        "signals": {
            "Coolant_Temp_C": "Coolant_Temp_C",
            "Oil_Temp_C":     "Oil_Temp_C",
            "Ambient_Temp_C": "Ambient_Temp_C",
            "Battery_V":      "Battery_V",
        },
    },

    "GearboxOdometer": {
        "can_id": 0x101,
        "is_extended": False,
        "is_fd": False,
        "dlc": 4,
        "signals": {
            "Gear_Num":        "Gear_Num",
            "Engine_Load_Pct": "Engine_Load_Pct",
            "Distance_km":     "Distance_km",
        },
    },

    "FuelStatus": {
        "can_id": 0x400,
        "is_extended": False,
        "is_fd": False,
        "dlc": 4,
        "signals": {
            "Fuel_Rate_mL_s":   "Fuel_Rate_mL_s",
            "Remaining_Fuel_L": "Remaining_Fuel_L",
            "Fuel_Pct":         "Fuel_Pct",
        },
    },

    "TyreStatus": {
        "can_id": 0x18ff0500,
        "is_extended": True,
        "is_fd": False,
        "dlc": 6,
        "signals": {
            "Tyre_P_FL": "Tyre_P_FL",
            "Tyre_P_FR": "Tyre_P_FR",
            "Tyre_P_RL": "Tyre_P_RL",
            "Tyre_P_RR": "Tyre_P_RR",
        },
    },

    "ActuatorData": {
        "can_id": 0x600,
        "is_extended": False,
        "is_fd": False,
        "dlc": 3,
        "signals": {
            "Head_Lamp":    "Head_Lamp",
            "Radiator_Fan": "Radiator_Fan",
            "Fuel_Pump":    "Fuel_Pump",
        },
    },
    "DriverInputs": {
        "can_id": 0x303,
        "is_extended": False,
        "is_fd": False,
        "dlc": 4,
        "signals": {
            "Clutch_State":    "Clutch_State",
            "Brake_State":     "Brake_State",
            "Rev_Limiter":     "Rev_Limiter",
            "Brake_Pedal_Pct": "Brake_Pedal_Pct",
        },
    },

    "ChassisDynamics": {
    "can_id": 0x306,        # Use the CAN ID you've assigned in your DBC
    "is_extended": False,
    "is_fd": False,
    "dlc": 8,
    "signals": {
        "Brake_Force_Pct":    "Brake_Force_Pct",
        "Steering_Angle_deg": "Steering_Angle_deg",
        "Lateral_Accel_ms2":  "Lateral_Accel_ms2",
        "Steering_Direction": "Steering_Direction",
    },
},

}