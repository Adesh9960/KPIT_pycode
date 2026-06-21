from .DID import DID

DID_DATABASE = {
    0xF180: DID(0xF180, b"BOOT_SW_V1.0", False, 0),
    0xF181: DID(0xF181, b"APP_SW_V2.3", False, 0),
    0xF186: DID(0xF186, b"\x01", False, 0),
    0xF18C: DID(0xF18C, b"ECU12345678", False, 0),
    0xF190: DID(0xF190, b"WAUFFAFL2GA006626", False, 0),

    0xF18E: DID(0xF18E, b"KPIT001", True, 1),
    0xF197: DID(0xF197, b"INITIAL_WORKSHOP_DATA", True, 1),

    0xF19D: DID(0xF19D, b"20260620", True, 2),
    0xF184: DID(0xF184, b"APP_FINGERPRINT_001", True, 2),
    0xF185: DID(0xF185, b"DATA_FINGERPRINT_001", True, 2),
}

DID_NAMES = {
    0xF180: "Boot Software Identification",
    0xF181: "Application Software Identification",
    0xF186: "Active Diagnostic Session",
    0xF18C: "ECU Serial Number",
    0xF190: "Vehicle Identification Number (VIN)",

    0xF18E: "Repair Shop Code",
    0xF197: "Workshop Data",

    0xF19D: "ECU Programming Date",
    0xF184: "Application Software Fingerprint",
    0xF185: "Application Data Fingerprint",
}
DID_LENGTHS = {
    0xF180: 8,   # Boot Software Identification
    0xF181: 8,   # Application Software Identification
    0xF186: 1,   # Active Diagnostic Session
    0xF18C: 12,  # ECU Serial Number
    0xF190: 17,  # VIN

    0xF18E: 8,   # Repair Shop Code
    0xF197: 16,  # Workshop Data

    0xF19D: 8,   # ECU Programming Date (YYYYMMDD)

    0xF184: 16,  # Application Software Fingerprint
    0xF185: 16,  # Application Data Fingerprint
}