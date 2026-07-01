from simulator.dids.didList import DID_DATABASE, DID_LENGTHS
import simulator.uds.negativeResponse as negative_response
import simulator.main as main

# Constant representing a successful operation status code
SUCCESS = 0x00

def set_DID(did: int, value: bytes) -> int:
    """
    Validates rules and updates a Data Identifier (DID) value in the memory database.

    Evaluates structural constraints sequentially to safeguard server memory state:
    1. **Existence Check:** Verifies the DID is supported in the database.
    2. **Write Permissions:** Confirms the target DID profile is flagged as writable.
    3. **Payload Length Validation:** Rejects payloads that do not strictly match 
       the required size configuration.
    4. **Security Clearance:** Enforces that the current server session security level 
       meets or exceeds the DID profile's baseline requirements.

    Args:
        did (int): The 16-bit integer key of the target Data Identifier.
        value (bytes): The raw data payload bytes proposed for the rewrite.

    Returns:
        int: `SUCCESS (0x00)` if written correctly, or a matching ISO 14229 Negative 
             Response Code scalar (e.g., 0x13, 0x31, or 0x33).
    """
    # Step 1: Confirm the database contains a profile tracking the requested identifier
    did_obj = DID_DATABASE.get(did)
    if did_obj is None:
        print(f"Unsupported DID: {hex(did)}")
        return negative_response.NRC_REQUEST_OUT_OF_RANGE

    # Step 2: Ensure the target memory address space accepts inbound configuration rewrites
    if not did_obj.is_writable:
        print(f"DID {hex(did)} is read-only")
        return negative_response.NRC_REQUEST_OUT_OF_RANGE

    # Step 3: Enforce strict byte length boundaries to avoid structure alignment corruption
    expected_length = DID_LENGTHS.get(did)
    if expected_length is not None and len(value) != expected_length:
        print(
            f"Invalid length for DID {hex(did)}. "
            f"Expected {expected_length}, got {len(value)}"
        )
        return negative_response.NRC_INCORRECT_MESSAGE_LENGTH

    # Step 4: Verify the client possesses adequate session privileges
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

    # Execution Block: Commit the validated payload sequence directly to state memory
    did_obj.value = value
    print(f"DID {hex(did)} updated successfully")
    return SUCCESS


def writeDataIdentifier(payload: bytearray) -> bytearray:
    """
    Processes an inbound UDS WriteDataByIdentifier (Service 0x2E) message payload.

    Parses incoming arrays matching structural message boundaries:
    `[SID (1 Byte)][DID (2 Bytes)][Data Parameter (N Bytes)]`
    Verifies minimum length rules, orchestrates structural validations against database 
    profiles, and outputs positive confirmation blocks or detailed negative responses.

    Args:
        payload (bytearray): Raw network message array sent by the diagnostic tester tool.

    Returns:
        bytearray: A finalized response buffer containing a positive confirmation signature (0x6E) 
                   with the mirrored DID bytes, or a detailed Negative Response frame.
    """
    # Frame Check: Message must contain at least 1 Byte SID + 2 Bytes DID + 1 Byte Data Minimum
    if len(payload) < 4:
        return negative_response.create_negative_response(0x2E, 0x13)

    # Extract boundaries: DID resides across indices 1 and 2 (Big Endian byte formatting)
    did = int.from_bytes(payload[1:3], 'big')
    data = payload[3:]

    # Pass extraction parameters to the core database state processor
    result = set_DID(did, data)

    # Triage Errors: Return negative responses if validation checks reject the block parameters
    if result != 0x00:
        return negative_response.create_negative_response(0x2E, result)

    # Formulate positive response: Service ID 0x2E + 0x40 = 0x6E followed by the target DID
    response = bytearray()
    response.append(0x6E)  
    response.extend(did.to_bytes(2, 'big'))
    return response