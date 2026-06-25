from uds_client.UDSError import UDSError
class IOControl:
    RETURN_CONTROL_TO_ECU = 0x00
    RESET_TO_DEFAULT = 0x01
    FREEZE_CURRENT_STATE = 0x02
    SHORT_TERM_ADJUSTMENT = 0x03

HEADLIGHT_DID = 0xF200
FAN_DID = 0xF201
HORN_DID = 0xF202

def io_control(
    self,
    did: int,
    control_parameter: int,
    control_state: bool = False
):
    """
    UDS Service 0x2F

    Request:
        2F DID_H DID_L ControlParameter [ControlState]

    Positive Response:
        6F DID_H DID_L ControlParameter [ControlState]
    """

    request = (
        bytes([
            0x2F,
            (did >> 8) & 0xFF,
            did & 0xFF,
            control_parameter
        ])
        + bytes([control_state])
    )

    response = self.send_and_wait(
        request,
        timeout=5
    )

    if response[0] != 0x6F:
        raise UDSError(response)

    print(
        f"IO Control successful "
        f"DID=0x{did:04X}"
    )

    return response