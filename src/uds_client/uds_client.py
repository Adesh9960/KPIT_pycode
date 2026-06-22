from enum import Enum
from udsoncan.services import ReadDataByIdentifier, WriteDataByIdentifier
from listener.TxRequest import TxRequest, TxRequestType
from listener.listener import send_to_tx_queue
import time
import threading
import uds_client.uploadFirmware as handleUploadFirmware
from uds_client.sessionControl import diagnostic_session_control
from uds_client.IOControl import io_control
from uds_client.securityAccess import security_access

class UDSRoles(Enum):
    USER = "user"
    MECHANIC = "mech"
    SHOWROOM = "show"
    MANUFACTURER = "man"

def createUDSRequest(payload, timeout, priority = 10) -> TxRequest:
    return TxRequest(
            priority=priority,
            enqueue_timestamp_ns=time.time_ns(),
            request_type=TxRequestType.UDS,
            payload=payload,
            max_retries=0,
            timeout_ms=timeout * 1000,
        )
class UDS:
    role: UDSRoles
    diagnostic_session_control = diagnostic_session_control
    io_control = io_control
    security_access = security_access

    transfer_data_upload = handleUploadFirmware.transfer_data_upload
    transfer_exit_upload = handleUploadFirmware.transfer_exit_upload
    def __init__(self, role):
        self.role = role
        self._event = threading.Event()
        self._response: bytes

    def on_response(self, payload):
        self._response = payload
        self._event.set()
    
    def send_and_wait(self, payload, timeout):
        self._event.clear()
        self._response = None

        uds_req = createUDSRequest(payload, timeout)

        send_to_tx_queue(uds_req)

        if not self._event.wait(timeout):
            raise TimeoutError("UDS response Timeout")
        
        return self._response

    def readDataByIdentifier(self, DID: int):
        request = ReadDataByIdentifier().make_request(didlist= DID, didconfig=None)
        payload = request.get_payload()
        timeout = 10
        self.send_and_wait(payload, timeout)
        print("UDS Response: ", self._response)

        response = self._response

        # Negative Response
        if response[0] == 0x7F:
            original_sid = response[1]
            nrc = response[2]

            print(
                f"Negative Response: SID=0x{original_sid:02X}, NRC=0x{nrc:02X}"
            )
            return

        # Positive Response
        if response[0] != 0x62:
            raise ValueError(
                f"Unexpected SID 0x{response[0]:02X}"
            )


        did = int.from_bytes(response[1:3], "big")
        value = response[3:].decode("ascii")
        # print(hex(did))
        # print(value)
        reslist = {}
        reslist[did] = value
        print(reslist)
        return reslist
        

    def writeDataByIdentifier(self, DID: int, data: bytes):
        timeout = 0.05
        request = WriteDataByIdentifier.make_request(
            did=DID,
            value=data,
            didconfig=None
        )
        payload = request.get_payload()
        self.send_and_wait(payload, timeout)    

    def firmwareUpload(self, output_file):
        handleUploadFirmware.request_upload(self)
        handleUploadFirmware.read_firmware_from_ecu(self, output_file)