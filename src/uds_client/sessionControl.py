from uds_client.UDSError import UDSError

DEFAULT_SESSION = 0x01
PROGRAMMING_SESSION = 0x02
EXTENDED_SESSION = 0x03

ALLOWED_SESSIONS = [
    DEFAULT_SESSION,
    PROGRAMMING_SESSION,
    EXTENDED_SESSION
]


def diagnostic_session_control(self, session_type: int):
    """
    UDS Service 0x10 - Diagnostic Session Control

    Request:
        10 <session>

    Positive Response:
        50 <session> <P2ServerMaxHi> <P2ServerMaxLo>
           <P2*ServerMaxHi> <P2*ServerMaxLo>

    Example:
        Request  : 10 03
        Response : 50 03 00 32 01 F4
    """

    response = self.send_and_wait(
        bytes([
            0x10,
            session_type
        ]),
        timeout=5
    )
    if response[0] != 0x50:
        raise UDSError(
            response
        )
    print(
        f"Session changed successfully "
        f"to 0x{session_type:02X}"
    )

    return True