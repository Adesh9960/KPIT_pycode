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
}