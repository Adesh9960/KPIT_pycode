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

    "EngineDiagnostics": {
        "can_id": 0x300,
        "is_extended": False,
        "is_fd": False,
        "dlc": 8,
        "signals": {
            "MAF_g_s":        "MAF_g_s",
            "MAP_kPa":        "MAP_kPa",
            "IAT_C":          "IAT_C",
            "Ign_Timing_deg": "Ign_Timing_deg",
        },
    },

    "FuelInjectionStatus": {
        "can_id": 0x301,
        "is_extended": False,
        "is_fd": False,
        "dlc": 8,
        "signals": {
            "Fuel_Pressure_bar": "Fuel_Pressure_bar",
            "Fuel_Trim_Pct":     "Fuel_Trim_Pct",
            "Injector_PW_ms":    "Injector_PW_ms",
            "Knock_Count":       "Knock_Count",
        },
    },

    "EmissionsThermal": {
        "can_id": 0x302,
        "is_extended": False,
        "is_fd": False,
        "dlc": 4,
        "signals": {
            "Catalyst_Temp_C":    "Catalyst_Temp_C",
            "Trans_Fluid_Temp_C": "Trans_Fluid_Temp_C",
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

    "BatteryCharging": {
        "can_id": 0x304,
        "is_extended": False,
        "is_fd": False,
        "dlc": 6,
        "signals": {
            "Battery_SOC_Pct":      "Battery_SOC_Pct",
            "Alternator_V":         "Alternator_V",
            "Idle_Speed_Adapt_RPM": "Idle_Speed_Adapt_RPM",
        },
    },

    "UDSStatus": {
        "can_id": 0x305,
        "is_extended": False,
        "is_fd": False,
        "dlc": 1,
        "signals": {
            "UDS_Session": "UDS_Session",
        },
    },

    "WheelSpeeds": {
        "can_id": 0x18ff0010,
        "is_extended": True,
        "is_fd": False,
        "dlc": 8,
        "signals": {
            "Wheel_Speed_FL_kmh": "Wheel_Speed_FL_kmh",
            "Wheel_Speed_FR_kmh": "Wheel_Speed_FR_kmh",
            "Wheel_Speed_RL_kmh": "Wheel_Speed_RL_kmh",
            "Wheel_Speed_RR_kmh": "Wheel_Speed_RR_kmh",
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