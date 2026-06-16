from enum import Enum
from udsoncan.services import ReadDataByIdentifier, WriteDataByIdentifier
from listener.TxRequest import TxRequest, TxRequestType
from listener.listener import send_to_tx_queue
import time
import threading

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
            timeout_ms=timeout,
        )
class UDS:
    role: UDSRoles
    def __init__(self, role):
        self.role = role
        self._event = threading.Event()
        self._response = threading.Event()

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
        timeout = 5
        self.send_and_wait(payload, timeout)

    def writeDataByIdentifier(self, DID: int, data: bytes):
        timeout = 0.05
        request = WriteDataByIdentifier.make_request(
            did=DID,
            value=data,
            didconfig=None
        )
        payload = request.get_payload()
        self.send_and_wait(payload, timeout)


