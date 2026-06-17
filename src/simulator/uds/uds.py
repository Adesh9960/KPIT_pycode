import simulator.DIDs as DIDs
from listener.listener import send_to_tx_queue

class UDSRepsonseError(Exception):
    """
    Raised when a there is a error.
    """
    def __init__(self, sid: bytes, error_data: bytes):
        self.sid = sid
        self.error_data = error_data
        super().__init__()

def get_DID(DID: int):

    DID_val = DIDs.DIDlist.get(DID)
    if DID_val is None:
        raise UDSRepsonseError(0x22, 0x31)
    response_val = DID_val
    if isinstance(DID_val, str):
        response_val = DID_val.encode('ascii')
    return response_val
    
def set_DID():
    pass

def handle_tester_request(payload: bytearray):
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
                    return send_to_tx_queue(bytes(0x7F + e.sid + e.error_data))
                
                response.append(
                        bytes.fromhex(did) + did_data
                    )
        
                send_to_tx_queue(response)

        case 0x2E:
            print("WriteDataByIdentifier")
        case 0x10:
            print("DiagnosticSessionControl")
        case 0x27:
            print("SecurityAccess") 
        case 0x3E:
            print("TesterPresent")
        case _:
            print(f"Unsupported SID: 0x{sid:02X}")

