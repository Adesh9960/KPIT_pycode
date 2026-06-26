from enum import Enum
from simulator.dids.didConfig import didconfig
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
from uds_client.uds_crypto import encrypt_uds_payload, decrypt_uds_payload, UDSCryptoError
from uds_client.uds_aes_key import UDS_AES_KEY
from uds_client.UDSError import UDSError

import hashlib

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

    read_dtcs = read_dtcs
    clear_all_dtcs = clear_all_dtcs

    transfer_data_upload = handleUploadFirmware.transfer_data_upload
    transfer_exit_upload = handleUploadFirmware.transfer_exit_upload
    request_upload = handleUploadFirmware.request_upload


    def __init__(self, role):
        self.role = role
        self._event = threading.Event()
        self._response: bytes

    def on_response(self, payload):
        print(f"[RAW-RX] {payload}")
        # print(f"[KEY-CHECK-TESTER] using key fingerprint: {hashlib.sha256(UDS_AES_KEY).hexdigest()[:16]}")
        # print(f"[AES-RX-TESTER] wire={bytes(payload).hex()} len={len(payload)}")
        try:
            # self._response = decrypt_uds_payload(UDS_AES_KEY, bytes(payload))
            self._response = payload
        except UDSCryptoError as e:
            print(f"UDS response decryption failed: {e}")
            self._response = bytes([0x7F, 0x00, 0x22])
        except ValueError as e:
            print(f"UDS response malformed: {e}")
            self._response = bytes([0x7F, 0x00, 0x13])
        finally:
            self._event.set()
    
    def send_and_wait(self, payload, timeout):
        self._event.clear()
        self._response = None

        # encrypted_payload = encrypt_uds_payload(UDS_AES_KEY, bytes(payload))
        # print(f"[AES-TX] plaintext={bytes(payload).hex()} -> ciphertext={encrypted_payload.hex()}")
        # print("TX HEX:", encrypted_payload.hex())
        # print("TX LEN:", len(encrypted_payload))
        # uds_req = createUDSRequest(encrypted_payload, timeout) 
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
            raise UDSError(
                response
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
        timeout = 5
        print("Inside write Data Indenftifer")

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

        # Negative Response
        if response[0] == 0x7F:
            original_sid = response[1]
            nrc = response[2]

            print(
                f"Negative Response: SID=0x{original_sid:02X}, NRC=0x{nrc:02X}"
            )

            return {
                "status": "error",
                "sid": original_sid,
                "nrc": nrc
            }

        # Positive Response
        if response[0] != 0x6E:
            raise UDSError(
                response
            )

        did = int.from_bytes(response[1:3], "big")

        result = {
            "status": "success",
            "did": did
        }

        print(result)

        return result 

    def firmwareUpload(self, output_file):
        file_data = handleUploadFirmware.read_firmware_from_ecu(self, output_file)
        with open(f"../data/firmware/firmware.bin", "wb") as f:
            f.write(file_data)
        return {
            "status": "success",
        }