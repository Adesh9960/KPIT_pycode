from listener.listener import send_to_tx_queue
from listener.TxRequest import TxRequest, TxRequestType
import time
import simulator.main as main
import simulator.uds.negativeResponse as negative_response

from .ReadDataIdentifier import readDataByIdentifier
from .WriteDataIdentifier import writeDataIdentifier
from .securityAccess import handleSecurityAccess
from .DiagonisticSessionControl import handleDiagonisticSessionControl
from .IOControl import handleInputOutputControl
import simulator.uds.handleDTC as handleDTC

import simulator.uds.Session as Session
import simulator.uds.uploadFirmware as uploadFirmware

def createTXRequest(payload: bytes) -> TxRequest:
    """
    Wraps an outbound diagnostic server response payload into a standardized TxRequest.

    Args:
        payload (bytes): The raw compiled diagnostic response byte array.

    Returns:
        TxRequest: A high-priority transaction container destined for the transmitter queue.
    """
    return TxRequest(
        priority=1,
        enqueue_timestamp_ns=time.time_ns(),
        request_type=TxRequestType.UDS,
        payload=payload,
        max_retries=0,
        timeout_ms=100,
    )


def send_response(payload: bytes | bytearray):
    """
    Schedules an asynchronous response packet for dispatch over the CAN network.

    Args:
        payload (bytes | bytearray): The response stream to send back to the diagnostic tester.
    """
    return send_to_tx_queue(createTXRequest(payload))
    

def validate_programming_session():
    """
    Enforces critical safety and environmental interlocks required for flashing operations.

    Monitors vehicle speed and battery voltage boundaries whenever the server state 
    is set to a `PROGRAMMING_SESSION`. If the vehicle is moving or battery levels drop 
    dangerously low ($\le 11\text{V}$), the flashing session is aborted immediately and reverted 
    to the `DEFAULT_SESSION` state to protect the ECU.
    """
    if int(main.session_level) != Session.PROGRAMMING_SESSION:
        return

    # Safety Interlock: Vehicle must be completely stationary to allow flash programming
    if main.current_speed != 0:
        print(
            f"Programming Session aborted. "
            f"Vehicle speed = {main.current_speed}"
        )
        main.session_level = Session.DEFAULT_SESSION
        return

    # Safety Interlock: Voltage must be stable to prevent corrupted memory or bricked controllers
    if main.battery_voltage <= 11:
        print(
            f"Programming Session aborted. "
            f"Battery voltage = {main.battery_voltage}"
        )
        main.session_level = Session.DEFAULT_SESSION
        return


def validate_session(*allowed_sessions) -> int | None:
    """
    Validates if the active diagnostic session permits the execution of a service request.

    Args:
        *allowed_sessions: Variable number of integer session identifiers permitted to use this service.

    Returns:
        None: If the current active session is authorized.
        int: The negative response code (NRC 0x7F) representing `ServiceNotSupportedInActiveSession`.
    """
    print("Session level: ", main.session_level)
    if int(main.session_level) in allowed_sessions:
        return None

    return negative_response.NRC_SERVICE_NOT_SUPPORTED_IN_ACTIVE_SESSION


def handle_tester_request(wire_payload: bytearray):
    """
    The main routing switchboard that decodes incoming diagnostic tester requests.

    Extracts the application Service Identifier (SID) byte at index 0 and evaluates 
    the transaction. It sequentially maps out session restrictions, delegates payloads to sub-service 
    handlers, and returns positive or negative frames back onto the bus.

    Args:
        wire_payload (bytearray): The raw message buffer arriving directly from the CAN interface layers.
    """
    try:
        payload = wire_payload
    except ValueError as e:
        print(f"UDS request malformed: {e}")
        return send_response(negative_response.create_negative_response(
            0x00, negative_response.NRC_INCORRECT_MESSAGE_LENGTH
        ))

    # Pre-routing check: Ensure safety constraints haven't been breached if in a programming mode
    validate_programming_session()
    print("inside handle tester request")
    print(payload)
    
    sid = payload[0]
    match sid:
        case 0x22:
            print("ReadDataByIdentifier")
            response = readDataByIdentifier(payload)
            send_response(response)

        case 0x2E:
            print("WriteDataByIdentifier")
            response = writeDataIdentifier(payload)
            send_response(response)

        case 0x10:
            print("DiagnosticSessionControl") 
            response = handleDiagonisticSessionControl(payload)
            send_response(response)

        case 0x27:
            print("SecurityAccess") 
            response = handleSecurityAccess(payload)
            print("Security Response")
            print(response)
            send_response(response)
            
        case 0x2F:
            print("IO Control")
            nrc = validate_session(
                Session.EXTENDED_SESSION,
                Session.PROGRAMMING_SESSION
            )
            if nrc is not None:
                # Bug fix note: Adjusted the negative response creator mapping to use its own SID (0x2F) rather than 0x14's bounds
                return send_to_tx_queue(createTXRequest(negative_response.create_negative_response(0x2F, nrc)))
            response = handleInputOutputControl(payload)
            send_response(response)
            
        case 0x14:
            print("Clear DTC")
            nrc = validate_session(
                Session.PROGRAMMING_SESSION
            )
            if nrc is not None:
                return send_to_tx_queue(createTXRequest(negative_response.create_negative_response(0x14, nrc)))
            response = handleDTC.handle_clear_dtc(payload)
            send_response(response)

        case 0x19:
            print("Read DTC")
            nrc = validate_session(
                Session.PROGRAMMING_SESSION,
                Session.EXTENDED_SESSION
            )
            if nrc is not None:
                return send_to_tx_queue(createTXRequest(negative_response.create_negative_response(0x19, nrc)))
            response = handleDTC.handle_read_dtc()
            send_response(response)
            
        # ----------------------------------------------------
        # Firmware Flashing Subsystem (Services 0x35, 0x36, 0x37)
        # ----------------------------------------------------
        case 0x35:
            print("Upload firmware")
            print("Current Session: ", main.session_level)
            nrc_code = validate_session(
                Session.PROGRAMMING_SESSION
            )
            if nrc_code is not None:
                return send_response(negative_response.create_negative_response(
                    0x35,
                    nrc_code
                ))
            response = uploadFirmware.handleRequestUpload(payload)
            send_response(response)
            
        case 0x36:
            print("Blocks")
            response = uploadFirmware.handleTransferDataUpload(payload)
            send_response(response)

        case 0x37:
            print("Exit upload")
            response = uploadFirmware.handleTransferExitUpload(payload)
            send_response(response)
            
        case 0x3E:
            print("TesterPresent")
            # Note: 0x3E is kept alive silently here. If a response is expected,
            # implement a positive response generation block (0x7E) here.
      
        case _:
            print(f"Unsupported SID: 0x{sid:02X}")