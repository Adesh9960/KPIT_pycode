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