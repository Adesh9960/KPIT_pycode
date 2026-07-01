from simulator.dids.didList import DID_DATABASE

def get_DID(did: int) -> bytes | None:
    """
    Queries the local database to retrieve the raw bytes of a specified Data Identifier.

    Args:
        did (int): The 16-bit integer key mapping to the target DID.

    Returns:
        bytes: The raw data payload bytes associated with the identifier if found.
        None: If the requested DID is unsupported or missing from the database.
    """
    did_obj = DID_DATABASE.get(did)

    if did_obj is None:
        print(f"Unsupported DID: {hex(did)}")
        return None

    return did_obj.value


def readDataByIdentifier(payload: bytearray) -> bytearray:
    """
    Processes an inbound UDS ReadDataByIdentifier (Service 0x22) message payload.

    Iterates through the input payload array to extract one or more 16-bit DIDs 
    packed by the tester. It reads each DID sequentially, fetches its registered data 
    from memory, and appends both the mirrored DID and its raw values into a composite 
    positive response buffer array.

    The expected message structure follows:
    - Request: `[SID=0x22][DID1_High][DID1_Low][DID2_High][DID2_Low]...`
    - Response: `[SID_PR=0x62][DID1_High][DID1_Low][Data1_Bytes...][DID2_High][DID2_Low][Data2_Bytes...]...`

    Args:
        payload (bytearray): The raw diagnostic network message payload array.

    Returns:
        bytearray: A single compiled positive response buffer containing the 0x62 service 
                   identifier followed by interleaved DID labels and data content blocks.
    """
    # Initialize the positive response frame starting with the service identifier offset (0x22 + 0x40 = 0x62)
    response = bytearray([0x62])
    
    # Iterate through the payload starting at index 1, skipping by 2 bytes to read individual 16-bit DIDs
    for i in range(1, len(payload), 2):
        # Extract the 2-byte DID big-endian scalar integer value
        did = int.from_bytes(
            payload[i: i + 2],
            "big"
        )

        did_data = get_DID(did)
        
        # Note: If did_data returns None (unsupported DID), appending it directly will raise a TypeError.
        # Consider inserting a validation block here to handle None values or emit an NRC 0x31 frame instead.
        if did_data is not None:
            # Reconstruct and append the response block mapping: [DID (2 Bytes)] + [Raw Data Payload (N Bytes)]
            response.extend(
                did.to_bytes(2, 'big') + did_data
            )
            
    return response