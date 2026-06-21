from simulator.dids.didList import DID_DATABASE
def get_DID(did: int) -> bytes | None:
    """
    Returns the value of the DID.

    Returns:
        bytes: DID value
        None: DID not supported
    """

    did_obj = DID_DATABASE.get(did)

    if did_obj is None:
        print(f"Unsupported DID: {hex(did)}")
        return None

    return did_obj.value

def readDataByIdentifier(payload: bytearray):           
    response: bytearray = [0x62]
    for i in range(1, len(payload), 2):
        did = int.from_bytes(
            payload[i: i + 2],
            "big"
        )

        did_data = get_DID(did)
     
        response.extend(
                did.to_bytes(2, 'big') + did_data
        )
            
    return response