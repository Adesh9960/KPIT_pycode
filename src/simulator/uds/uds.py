import simulator.DIDs as DIDs
from listener.listener import send_to_tx_queue
from listener.TxRequest import TxRequest, TxRequestType
import time
import secrets
import zlib
import simulator.main as main
class UDSRepsonseError(Exception):
    """
    Raised when a there is a error.
    """
    def __init__(self, sid: bytes, error_data: bytes):
        self.sid = sid
        self.error_data = error_data
        super().__init__()

def get_DID(DID: int):
    print(DID)
    DID_val = DIDs.DIDlist.get(DID)
    if DID_val is None:
        raise UDSRepsonseError(0x22, 0x31)
    response_val = DID_val
    if isinstance(DID_val, str):
        response_val = DID_val.encode('ascii')
        print("Response_val is : ", response_val)
    return response_val
    
def set_DID():
    pass

def generate_seed() -> bytes:
    seed = secrets.token_bytes(4)
    print(seed.hex())
    return seed.hex()

def level1key(seed: bytes):
    return bytes(b ^ 0xA5 for b in seed)

def level2key(seed: bytes):
    key = bytearray()

    for b in seed:
        rotated = ((b << 3) | (b >> 5)) & 0xFF
        key.append(rotated ^ 0x5C)

    return bytes(key)

def level3key(seed: bytes):
    crc = zlib.crc32(seed)
    return crc.to_bytes(4, "big")

def createTXRequest(payload: bytes):
    return TxRequest(
        priority=10,
        enqueue_timestamp_ns=time.time_ns(),
        request_type=TxRequestType.UDS,
        payload=payload,
        max_retries=0,
        timeout_ms=100,
    )

def handle_tester_request(payload: bytearray):
    print("inside handle tester request")
    sid = payload[0]
    match sid:
        case 0x22:
            print("ReadDataByIdentifier")
            response: bytearray = [0x62]
            for i in range(1, len(payload), 2):
                did = int.from_bytes(
                    payload[i: i + 2],
                    "big"
                )

                try:
                    did_data = get_DID(did)
                except UDSRepsonseError as e:
                    return send_to_tx_queue(createTXRequest(bytes(0x7F + e.sid + e.error_data)))
                
                response.extend(
                    did.to_bytes(2, 'big') + did_data
                )
            
            send_to_tx_queue(createTXRequest(bytes(response)))

        case 0x2E:
            print("WriteDataByIdentifier")
        case 0x10:
            print("DiagnosticSessionControl")
        case 0x27:
            print("SecurityAccess") 
            req = int.from_bytes(payload[1], byteorder='big', signed=False)
            if req % 2 == 1:
                seed = generate_seed()
                response = bytearray(int.from_bytes(payload[0], byteorder='big', signed=False))
                response.append((payload[1] + seed)) 
                send_to_tx_queue(createTXRequest(bytes(response)))
                if payload[1] == 0x01:
                    main.session_key = level1key(seed)
                    main.session_level = 1

                if payload[1] == 0x03:
                    main.session_key = level2key(seed)
                    main.session_level = 2
                    
                if payload[1] == 0x05:
                    main.session_key = level3key(seed)
                    main.session_level = 3
            else:
                tester_key = payload[2:]
                if(tester_key == main.session_key):
                    main.session_expire_time = time.time() + 5 * 60
                    response = bytearray(int.from_bytes(payload[0], byteorder='big', signed=False))
                    response.append(payload[1])
                    send_to_tx_queue(createTXRequest(bytes(response)))

        case 0x3E:
            print("TesterPresent")
        case _:
            print(f"Unsupported SID: 0x{sid:02X}")

