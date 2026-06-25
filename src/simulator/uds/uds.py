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
from .uds_crypto import encrypt_uds_payload, decrypt_uds_payload, UDSCryptoError
from .uds_aes_key import UDS_AES_KEY


import simulator.uds.Session as Session
import simulator.uds.uploadFirmware as uploadFirmware

import hashlib

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
    print("Actual Payload", payload)
    print(f"[KEY-CHECK-ECU] using key fingerprint: {hashlib.sha256(UDS_AES_KEY).hexdigest()[:16]}")
    # encrypted_payload = encrypt_uds_payload(UDS_AES_KEY, bytes(payload))
    # print("TX HEX:", encrypted_payload.hex())
    # print("TX LEN:", len(encrypted_payload))
    # print(f"[AES-TX-ECU] plaintext={bytes(payload).hex()} -> ciphertext={encrypted_payload.hex()} len={len(encrypted_payload)}")
    # return send_to_tx_queue(createTXRequest(encrypted_payload))
    return send_to_tx_queue(createTXRequest(payload))
    
def validate_programming_session():

    if int(main.session_level) != Session.PROGRAMMING_SESSION:
        return

    if main.current_speed != 0:
        print(
            f"Programming Session aborted. "
            f"Vehicle speed = {main.current_speed}"
        )

        main.session_level = Session.DEFAULT_SESSION
        return

    if main.battery_voltage <= 11:
        print(
            f"Programming Session aborted. "
            f"Battery voltage = {main.battery_voltage}"
        )

        main.session_level = Session.DEFAULT_SESSION
        return
    
def validate_session(*allowed_sessions):
    """
    Returns:
        None  -> Session valid
        NRC   -> Session invalid
    """
    print("Session level: ", main.session_level)
    if int(main.session_level) in allowed_sessions:
        return None

    return negative_response.NRC_SERVICE_NOT_SUPPORTED_IN_ACTIVE_SESSION


def handle_tester_request(wire_payload: bytearray):
    try:
        # payload = decrypt_uds_payload(UDS_AES_KEY, bytes(wire_payload))
        # print(f"[AES-RX] wire={bytes(wire_payload).hex()} -> decrypted={payload.hex()}")
        payload = wire_payload
    except UDSCryptoError as e:
        print(f"UDS request decryption failed: {e}")
        return send_response(negative_response.create_negative_response(
            0x00, negative_response.NRC_GENERAL_REJECT
        ))
    except ValueError as e:
        print(f"UDS request malformed: {e}")
        return send_response(negative_response.create_negative_response(
            0x00, negative_response.NRC_INCORRECT_MESSAGE_LENGTH
        ))

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
            print("DiagonsitcSessionControl") 
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
                return send_to_tx_queue(createTXRequest(negative_response.create_negative_response(0x2F, nrc)))
            response = handleInputOutputControl(payload)
            send_response(response)
          
        #Firware upload
        case 0x35:
            print("Upload firmware")
            print("Current Session: ", main.session_level)
            nrc_code = validate_session(
                Session.PROGRAMMING_SESSION
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

