import simulator.main as main
import simulator.uds.negativeResponse as negativeResponse

def handle_read_dtc() -> bytes:
    """
    Processes a UDS ReadDTCInformation (Service 0x19) request.

    Constructs a positive response block using sub-function 0x02 
    (reportDTCByStatusMask) to query the local DTC manager database. It loops 
    through all recorded faults, packing each 3-byte DTC code array alongside 
    its respective status mask byte.

    The expected response payload structure follows:
    `[SID_PR=0x59][SubFunction=0x02][DTCStatusAvailabilityMask=0xFF][DTC1_High][DTC1_Mid][DTC1_Low][DTCStatus1]...`

    Returns:
        bytes: The compiled positive response data block containing active faults.
    """
    response = bytearray()

    response.append(0x59)   # Positive Response Service Identifier (0x19 + 0x40)
    response.append(0x02)   # Subfunction: reportDTCByStatusMask
    response.append(0xFF)   # DTCStatusAvailabilityMask (0xFF assumes all status bits are supported)

    # Serialize each registered trouble code into the byte stream
    for dtc in main.dtc_manager.get_all():
        response.extend(dtc.code.to_bytes(3, "big"))  # Standard 3-byte internal DTC code layout
        response.append(dtc.status)                   # Current DTC status byte (e.g., pending, confirmed)

    return bytes(response)


def handle_clear_dtc(data: bytearray) -> bytes:
    """
    Processes a UDS ClearDiagnosticInformation (Service 0x14) request.

    Enforces that the client session meets or exceeds Security Level 2 before executing 
    destructive operations. It extracts the 3-byte target group parameter mask; if the group 
    matches the standard `0xFFFFFF` wildcard mask, it drops all faults globally across all systems.

    Args:
        data (bytearray): Raw incoming request buffer containing `[SID=0x14][GroupOfDTC_High][GroupOfDTC_Mid][GroupOfDTC_Low]`.

    Returns:
        bytes: A positive response header mapping (0x54) on success, or an explicit 
               Negative Response frame (NRC 0x33).
    """
    # Security Gate: Clearing fault logs requires explicit write privileges
    if main.security_level < 2:
        return negativeResponse.create_negative_response(0x14, 0x33)

    # Extract the full 4-byte stream containing the 0x14 SID header + the 3-byte group parameter mask
    group = int.from_bytes(data, "big")
    print("Group: ", hex(group))
    
    # 0x14FFFFFF means clear all DTCs (SID 0x14 combined with the 3-byte wildcard mask 0xFFFFFF)
    if group == 0x14FFFFFF:
        main.dtc_manager.clear_all()
    else:
        # Isolate the specific 3-byte group filter parameter out of the combined int representation
        specific_group = group & 0xFFFFFF
        main.dtc_manager.clear_dtc(specific_group)

    # Return positive response SID (0x14 + 0x40 = 0x54) along with the echoed group mask bytes
    return bytes([0x54]) + data[1:]


def get_snapshot(dtcCode: int):
    """
    Queries environmental freeze-frame parameter logs indexed to a targeted fault code.

    Args:
        dtcCode (int): The 24-bit representation identifier of the target trouble code.
    """
    main.dtc_manager.get_snapshot(dtcCode)