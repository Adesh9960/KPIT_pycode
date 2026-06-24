from .DID import DID

# ═══════════════════════════════════════════════════════════════
# DID DATABASE
# security_level: 0 = Default Session (read-only, no auth)
#                 1 = Extended Session (0x10 0x03, security level 1)
#                 2 = Programming Session (0x10 0x02, security level 2)
#
# Standard ISO DIDs (0xF180–0xF19E): static ECU identity data
# Custom Live Telemetry DIDs (0xF401–0xF412): dynamic signals from Parameters.py
# Custom Actuator DIDs (0xF410–0xF412): IO Control targets (0x2F)
# ═══════════════════════════════════════════════════════════════

DID_DATABASE = {

    # ── Standard ISO 14229 Identity DIDs ──────────────────────
    # security_level 0: readable in Default session, not writable
    0xF180: DID(0xF180, b"BOOT_SW_V1.0",           False, 0),
    0xF181: DID(0xF181, b"APP_SW_V2.3",             False, 0),
    0xF186: DID(0xF186, b"\x01",                    False, 0),  # Active session byte
    0xF18C: DID(0xF18C, b"ECU12345678",             False, 0),
    0xF190: DID(0xF190, b"WAUFFAFL2GA006626",       False, 0),  # VIN (17 bytes)

    # security_level 1: readable in Extended session, writable with level-1 security
    0xF18E: DID(0xF18E, b"KPIT001",                 True,  1),  # Repair Shop Code
    0xF197: DID(0xF197, b"INITIAL_WORKSHOP_DATA",   True,  1),  # Workshop Data

    # security_level 2: writable only in Programming session with level-2 security
    0xF19D: DID(0xF19D, b"20260620",                True,  2),  # ECU Programming Date
    0xF184: DID(0xF184, b"APP_FINGERPRINT_001",     True,  2),  # App SW Fingerprint
    0xF185: DID(0xF185, b"DATA_FINGERPRINT_001",    True,  2),  # App Data Fingerprint

    # ── Live Telemetry DIDs (from Parameters.py get_telemetry_entry) ──
    # These are READ-ONLY (is_writable=False), readable in Extended session (level 1)
    # Values are placeholders — UDSHandler.handle_read_did() replaces them live
    0xF401: DID(0xF401, b"\x00\x00",   False, 1),  # Speed_kmh        uint16 km/h
    0xF402: DID(0xF402, b"\x00\x00",   False, 1),  # Engine_RPM       uint16 RPM
    0xF403: DID(0xF403, b"\x00\x00",   False, 1),  # Coolant_Temp_C   int16  × 100
    0xF404: DID(0xF404, b"\x00\x00",   False, 1),  # Oil_Temp_C       int16  × 100
    0xF405: DID(0xF405, b"\x00\x00",   False, 1),  # Fuel_Pct         uint16 × 10
    0xF406: DID(0xF406, b"\x00\x00",   False, 1),  # Battery_V        uint16 × 100
    0xF407: DID(0xF407, b"\x00\x00",   False, 1),  # Engine_Load_Pct  uint16 × 10
    0xF408: DID(0xF408, b"\x00\x00",   False, 1),  # Throttle_Pct     uint16 × 10
    0xF409: DID(0xF409, b"\x00",       False, 1),  # Gear_Num         uint8
    0xF40A: DID(0xF40A, b"\x00\x00",   False, 1),  # Fuel_Rate_mL_s   uint16 × 100
    0xF40B: DID(0xF40B, b"\x00\x00",   False, 1),  # Ambient_Temp_C   int16  × 100
    0xF40C: DID(0xF40C, b"\x00\x00",   False, 1),  # Accel_ms2        int16  × 100
    0xF40D: DID(0xF40D, b"\x00\x00\x00\x00", False, 1),  # Distance_km uint32 × 1000

    # ── Actuator DIDs (IO Control 0x2F targets) ──────────────
    # is_writable=True so 0x2F can override them
    # security_level 1: overrideable in Extended session (technician test)
    0xF410: DID(0xF410, b"\x00",  True, 1),  # Head_Lamp    (0=ECU, 1=Force ON, 0=Force OFF)
    0xF411: DID(0xF411, b"\x00",  True, 1),  # Radiator_Fan (0=ECU, 1=Force ON, 0=Force OFF)
    0xF412: DID(0xF412, b"\x00",  True, 1),  # Fuel_Pump    (0=ECU, 1=Force ON, 0=Force OFF)

    # ── Tyre Pressure DIDs ───────────────────────────────────
    # Read-only, extended session
    0xF420: DID(0xF420, b"\x00\x00", False, 1),  # Tyre_P_FL  uint16 × 10 (psi)
    0xF421: DID(0xF421, b"\x00\x00", False, 1),  # Tyre_P_FR
    0xF422: DID(0xF422, b"\x00\x00", False, 1),  # Tyre_P_RL
    0xF423: DID(0xF423, b"\x00\x00", False, 1),  # Tyre_P_RR
}

# ── Human-readable names ──────────────────────────────────────
DID_NAMES = {
    # Standard ISO
    0xF180: "Boot Software Identification",
    0xF181: "Application Software Identification",
    0xF184: "Application Software Fingerprint",
    0xF185: "Application Data Fingerprint",
    0xF186: "Active Diagnostic Session",
    0xF18C: "ECU Serial Number",
    0xF18E: "Repair Shop Code",
    0xF190: "Vehicle Identification Number (VIN)",
    0xF197: "Workshop Data",
    0xF19D: "ECU Programming Date",
    # Live telemetry
    0xF401: "Speed (km/h)",
    0xF402: "Engine RPM",
    0xF403: "Coolant Temperature (°C)",
    0xF404: "Oil Temperature (°C)",
    0xF405: "Fuel Level (%)",
    0xF406: "Battery Voltage (V)",
    0xF407: "Engine Load (%)",
    0xF408: "Throttle Position (%)",
    0xF409: "Current Gear",
    0xF40A: "Fuel Rate (mL/s)",
    0xF40B: "Ambient Temperature (°C)",
    0xF40C: "Acceleration (m/s²)",
    0xF40D: "Trip Distance (km)",
    # Actuators
    0xF410: "Head Lamp",
    0xF411: "Radiator Fan",
    0xF412: "Fuel Pump",
    # Tyres
    0xF420: "Tyre Pressure FL (psi)",
    0xF421: "Tyre Pressure FR (psi)",
    0xF422: "Tyre Pressure RL (psi)",
    0xF423: "Tyre Pressure RR (psi)",
}

# ── Expected byte lengths for 0x22 request validation ────────
DID_LENGTHS = {
    0xF180: 12,
    0xF181: 11,
    0xF184: 16,
    0xF185: 16,
    0xF186: 1,
    0xF18C: 12,
    0xF18E: 8,
    0xF190: 17,
    0xF197: 16,
    0xF19D: 8,
    # Live telemetry
    0xF401: 2,
    0xF402: 2,
    0xF403: 2,
    0xF404: 2,
    0xF405: 2,
    0xF406: 2,
    0xF407: 2,
    0xF408: 2,
    0xF409: 1,
    0xF40A: 2,
    0xF40B: 2,
    0xF40C: 2,
    0xF40D: 4,
    # Actuators
    0xF410: 1,
    0xF411: 1,
    0xF412: 1,
    # Tyres
    0xF420: 2,
    0xF421: 2,
    0xF422: 2,
    0xF423: 2,
}