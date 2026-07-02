from enum import Enum
from dids.didConfig import didconfig
from udsoncan.services import ReadDataByIdentifier, WriteDataByIdentifier
from listener.TxRequest import TxRequest, TxRequestType
from listener.listener import send_to_tx_queue
import time
import threading
import uds_client.uploadFirmware as handleUploadFirmware
from uds_client.sessionControl import diagnostic_session_control
from uds_client.IOControl import io_control
from uds_client.securityAccess import security_access
from uds_client.handleDTC import read_dtcs, clear_all_dtcs
from uds_client.UDSError import UDSError

class UDSRoles(Enum):
    """Enumeration defining authorization access roles for the UDS Client session."""
    USER = "user"
    MECHANIC = "mech"
    SHOWROOM = "show"
    MANUFACTURER = "man"

def createUDSRequest(payload, timeout, priority = 10) -> TxRequest:
    """
    Wraps an outbound UDS diagnostic service payload into a prioritized TxRequest instance.

    Args:
        payload (bytes): The raw compiled diagnostic network request payload.
        timeout (float): Max valid response duration bounds in seconds.
        priority (int, optional): Priority tier used by the transmission scheduler. Defaults to 10.

    Returns:
        TxRequest: The structured transaction envelope scheduled for delivery.
    """
    return TxRequest(
            priority=priority,
            enqueue_timestamp_ns=time.time_ns(),
            request_type=TxRequestType.UDS,
            payload=payload,
            max_retries=0,
            timeout_ms=timeout * 1000,
        )

class UDS:
    """
    An object-oriented orchestration client managing ISO 14229 Unified Diagnostic Services.

    Acts as a centralized interface wrapping sub-service modules like Diagnostic Session 
    Control, Security Access, Input/Output Control, Diagnostic Trouble Code (DTC) utilities, 
    and multi-frame firmware download protocols. It coordinates thread-safe synchronous requests 
    using blocking asynchronous event flags.
    """
    role: UDSRoles
    
    # Delegated sub-service client operations mapped from independent library implementations
    diagnostic_session_control = diagnostic_session_control
    io_control = io_control
    security_access = security_access
    read_dtcs = read_dtcs
    clear_all_dtcs = clear_all_dtcs
    transfer_data_upload = handleUploadFirmware.transfer_data_upload
    transfer_exit_upload = handleUploadFirmware.transfer_exit_upload
    request_upload = handleUploadFirmware.request_upload

    def __init__(self, role):
        """
        Initializes the primary diagnostic UDS client module.

        Args:
            role (UDSRoles): The authorization identity class restricting or granting 
                             access privileges to critical ecosystem services.
        """
        self.role = role
        self._event = threading.Event()  # Synchronization primitive blocking thread during transaction
        self._response: bytes

    def on_response(self, payload: bytes):
        """
        Callback entry point invoked by the network layer whenever a diagnostic packet arrives.

        Extracts the message array, assigns it to the internal transactional store, and triggers 
        the cross-thread synchronization event flag to release any thread waiting inside `send_and_wait`.

        Args:
            payload (bytes): The raw, reassembled response payload bytes arriving from the network layer.
        """
        self._response = payload

        # Wake up the blocked application thread waiting inside the timeout loop
        self._event.set()
    
    def send_and_wait(self, payload: bytes, timeout: float) -> bytes:
        """
        Transmits a request payload and blocks until a response returns or a timeout occurs.

        Clears existing thread conditions, pushes the transaction envelope to the scheduler, 
        and halts current thread processing until the hardware notification callback 
        signals execution completion.

        Args:
            payload (bytes): The formatted raw service identifier parameters.
            timeout (float): Maximum allowed threshold length to wait before dropping connection (seconds).

        Returns:
            bytes: The extracted raw server response byte array.

        Raises:
            TimeoutError: If the remote ECU node fails to respond before the timeout threshold expires.
        """
        self._event.clear()
        self._response = None
        uds_req = createUDSRequest(payload, timeout)
        send_to_tx_queue(uds_req)

        # Block current execution thread context up to the timeout threshold limit
        if not self._event.wait(timeout):
            raise TimeoutError("UDS response Timeout")
        
        return self._response

    def readDataByIdentifier(self, DID: int) -> dict | None:
        """
        Requests the value of a specific Data Identifier (DID) from the ECU via service 0x22.

        Wraps parameters into a `ReadDataByIdentifier` request, blocks for execution, and 
        triages the underlying frame array to isolate negative responses, evaluate 
        protocol validity, and decode localized ASCII data strings.

        Args:
            DID (int): The 16-bit target data identifier index (e.g., 0xF190 for VIN).

        Returns:
            dict: A key-value lookup map linking the integer DID identifier to its decoded string representation.
            None: If the transaction terminates with a server Negative Response Code (NRC).

        Raises:
            UDSError: If the received frame lacks structural validation parameters matching standard positive parameters.
        """
        request = ReadDataByIdentifier().make_request(didlist=DID, didconfig=None)
        payload = request.get_payload()
        timeout = 10
        self.send_and_wait(payload, timeout)
        print("UDS Response: ", self._response)

        response = self._response

        # Case 1: Triage ISO 14229 Negative Response (0x7F) protocol block
        if response[0] == 0x7F:
            original_sid = response[1]
            nrc = response[2]
            print(f"Negative Response: SID=0x{original_sid:02X}, NRC=0x{nrc:02X}")
            return None

        # Case 2: Validate Standard ISO 14229 Positive Response offset (Service 0x22 + 0x40 = 0x62)
        if response[0] != 0x62:
            raise UDSError(response)

        # Parse structural data boundaries: [SID (1 Byte)][DID (2 Bytes)][Data Payload (N Bytes)]
        did = int.from_bytes(response[1:3], "big")
        value = response[3:].decode("ascii")
        
        reslist = {did: value}
        print(reslist)
        return reslist
        

    def writeDataByIdentifier(self, DID: int, data: str) -> dict:
        """
        Overwrites the content of a target Data Identifier (DID) via service 0x2E.

        Encodes input string sequences into standard byte parameters, structures an 
        outbound diagnostic payload packet, and evaluates network response frames 
        to track success or negative execution returns.

        Args:
            DID (int): The 16-bit identifier code index to edit.
            data (str): The raw text data sequence string to write to the ECU storage.

        Returns:
            dict: Structured state summary profiling execution status (e.g., {"status": "success", "did": 61840} 
                  or an entry logging the exact failing SID and NRC).

        Raises:
            UDSError: If the server returns a malformed response header not matching positive write offsets.
        """
        timeout = 5
        print("Inside write Data Indenftifer")

        # Encode plaintext context values to raw text byte representations
        write_request = WriteDataByIdentifier().make_request(
            did=DID,
            value=bytes(data, encoding="utf-8"),
            didconfig=didconfig
        )

        print("Write request : ", write_request)

        payload = write_request.get_payload()
        print(payload)
        self.send_and_wait(payload, timeout)

        print("UDS Response:", self._response)
        response = self._response

        # Case 1: Triage ISO 14229 Negative Response (0x7F) protocol block
        if response[0] == 0x7F:
            original_sid = response[1]
            nrc = response[2]
            print(f"Negative Response: SID=0x{original_sid:02X}, NRC=0x{nrc:02X}")
            return {
                "status": "error",
                "sid": original_sid,
                "nrc": nrc
            }

        # Case 2: Validate Standard ISO 14229 Positive Response offset (Service 0x2E + 0x40 = 0x6E)
        if response[0] != 0x6E:
            raise UDSError(response)

        did = int.from_bytes(response[1:3], "big")
        result = {
            "status": "success",
            "did": did
        }
        print(result)
        return result 

    def firmwareUpload(self, output_file: str) -> dict:
        """
        Triggers and runs a coordinated sequential firmware upload routine from the ECU.

        Acts as a routing macro invoking sequence handles within the underlying transfer wrapper 
        module to progressively stage, dump, and structure internal binary firmware assets.

        Args:
            output_file (str): Absolute or relative filesystem location where the extracted binary 
                               firmware payload will be compiled.

        Returns:
            dict: A operational outcome tracking state map (e.g., {"status": "success"}).
        """
        handleUploadFirmware.read_firmware_from_ecu(self, output_file)
        return {
            "status": "success",
        }