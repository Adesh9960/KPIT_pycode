NRCMessageMap = {
    0x10: "NRC_GENERAL_REJECT" ,
    0x11: "NRC_SERVICE_NOT_SUPPORTED",
    0x12: "NRC_SUBFUNCTION_NOT_SUPPORTED",
    0x13: "NRC_INCORRECT_MESSAGE_LENGTH",
    0x22: "NRC_CONDITIONS_NOT_CORRECT",
    0x31: "NRC_REQUEST_OUT_OF_RANGE",
    0x33: "NRC_SECURITY_ACCESS_DENIED",
    0x78: "NRC_RESPONSE_PENDING",
    0x7F: "NRC_SERVICE_NOT_SUPPORTED_IN_ACTIVE_SESSION"
}

class UDSError(Exception):
    def __init__(self, response):
        self.sid = response[1]
        self.nrc = response[2]
        self.message = NRCMessageMap.get(self.nrc)
        super().__init__(self.message)