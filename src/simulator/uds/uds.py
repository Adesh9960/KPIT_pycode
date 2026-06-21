from listener.listener import send_to_tx_queue
from listener.TxRequest import TxRequest, TxRequestType
import time
import secrets
import zlib
import simulator.main as main
import uds.negativeResponse as negative_response
import simulator.main as main

from .ReadDataIdentifier import readDataByIdentifier
from .WriteDataIdentifier import writeDataIdentifier
from .securityAccess import handleSecurityAccess
from .DiagonisticSessionControl import handleDiagonisticSessionControl
from .IOControl import handleInputOutputControl

import simulator.uds.Session as Session
import simulator.Data_generation.Parameters as params
import simulator.uds.uploadFirmware as uploadFirmware


def createTXRequest(payload: bytes):
    return TxRequest(
        priority=10,
        enqueue_timestamp_ns=time.time_ns(),
        request_type=TxRequestType.UDS,
        payload=payload,
        max_retries=0,
        timeout_ms=100,
    )
def send_response(payload: bytes | bytearray):
    return send_to_tx_queue(createTXRequest(bytes(payload)))

def validate_programming_session():

    if main.session_level != Session.SESSION_PROGRAMMING:
        return

    if params.current_speed != 0:
        print(
            f"Programming Session aborted. "
            f"Vehicle speed = {params.current_speed}"
        )

        main.session_level = Session.SESSION_DEFAULT
        return

    if params.battery_voltage <= 11:
        print(
            f"Programming Session aborted. "
            f"Battery voltage = {params.battery_voltage}"
        )

        main.session_level = Session.SESSION_DEFAULT
        return
    
def validate_session(*allowed_sessions):
    """
    Returns:
        None  -> Session valid
        NRC   -> Session invalid
    """

    if main.session_level in allowed_sessions:
        return None

    return negative_response.NRC_SERVICE_NOT_SUPPORTED_IN_ACTIVE_SESSION


def handle_tester_request(payload: bytearray):
    validate_programming_session()
    print("inside handle tester request")
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
            print("DiagonsitcSessionControl") 
            response = handleDiagonisticSessionControl()
            send_response(response)

        case 0x27:
            print("SecurityAccess") 
            response = handleSecurityAccess(payload)
            send_response(response)
        case 0x2F:
            print("IO Control")
            nrc = validate_session(
                Session.SESSION_EXTENDED,
                Session.SESSION_PROGRAMMING
            )
            if nrc is not None:
                return send_to_tx_queue(createTXRequest(negative_response.create_negative_response(0x2F, nrc)))
            response = handleInputOutputControl(payload)
            send_response(response)
          
        #Firware upload
        case 0x35:
            print("Upload firmware")
            nrc_code = validate_session(
                Session.SESSION_PROGRAMMING
            )

            if nrc_code is not None:
                send_response(negative_response.create_negative_response(
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
      
        case _:
            print(f"Unsupported SID: 0x{sid:02X}")

