from simulator.dids.DID import DID_DATABASE, DID_LENGTHS
import simulator.uds.negativeResponse as negative_response
import simulator.main as main

SUCCESS = 00

def set_DID(did: int, value: bytes) -> int:
    """
    Returns:
        0x00 -> Success
        0x13 -> Incorrect Message Length
        0x31 -> Request Out Of Range
        0x33 -> Security Access Denied
    """

    did_obj = DID_DATABASE.get(did)

    if did_obj is None:
        print(f"Unsupported DID: {hex(did)}")
        return negative_response.NRC_REQUEST_OUT_OF_RANGE

    if not did_obj.is_writable:
        print(f"DID {hex(did)} is read-only")
        return negative_response.NRC_REQUEST_OUT_OF_RANGE

    expected_length = DID_LENGTHS.get(did)

    if expected_length is not None and len(value) != expected_length:
        print(
            f"Invalid length for DID {hex(did)}. "
            f"Expected {expected_length}, got {len(value)}"
        )
        return negative_response.NRC_INCORRECT_MESSAGE_LENGTH

    try:
        current_security_level = int(main.security_level)
    except (ValueError, TypeError):
        current_security_level = 0

    if current_security_level < did_obj.security_level:
        print(
            f"Security access denied for DID {hex(did)}. "
            f"Required: {did_obj.security_level}, "
            f"Current: {current_security_level}"
        )
        return negative_response.NRC_SECURITY_ACCESS_DENIED

    did_obj.value = value

    print(f"DID {hex(did)} updated successfully")

    return SUCCESS

def writeDataIdentifier(payload: bytearray):
    if len(payload) < 4:
        return negative_response.create_negative_response(0x2E, 0x13)

    did = int.from_bytes(payload[1:3], 'big')
    data = payload[3:]

    result = set_DID(did, data)

    if result != 0x00:
        return negative_response.create_negative_response(0x2E, result)

    response = bytearray()
    response.append(0x6E)  # Positive response SID
    response.extend(did.to_bytes(2, 'big'))
    return response