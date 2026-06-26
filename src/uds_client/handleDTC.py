
from uds_client.UDSError import UDSError

def read_dtcs(self, status_mask=0xFF):
    """
    Read DTCs using Service 0x19 SubFunction 0x02
    """
    request = bytes([0x19, 0x02, status_mask])

    response = self.send_and_wait(request)

    if response[0] == 0x7F:
        raise UDSError(response)

    if response[0] != 0x59 or response[1] != 0x02:
        raise RuntimeError("Invalid ReadDTC response")

    dtcs = []

    data = response[3:]      # Skip SID, SubFunction, StatusMask

    while len(data) >= 4:
        code = int.from_bytes(data[:3], "big")
        status = data[3]

        dtcs.append({
            "code": code,
            "status": status
        })

        data = data[4:]

    return {
        "status": "success",
        "dtcs": dtcs
    }

def clear_all_dtcs(self):
    """
    Clear all DTCs (0xFFFFFF)
    """
    request = bytes([0x14, 0xFF, 0xFF, 0xFF])

    response = self.send_and_wait(request)

    if response[0] == 0x7F:
        raise UDSError(response)

    if response != bytes([0x54, 0xFF, 0xFF, 0xFF]):
        raise RuntimeError("Invalid ClearDTC response")

    return {
        "status": "success"
    }