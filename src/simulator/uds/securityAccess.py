import secrets
import zlib
import simulator.main as main
import simulator.uds.negativeResponse as negative_response

def generate_seed() -> bytes:
    seed = secrets.token_bytes(4)
    print(seed.hex())
    return seed

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

def handleSecurityAccess(payload):
    req = payload[1]
    print("inside handle security")
    if req % 2 == 1:
        seed = generate_seed()
        response = bytearray([0x67])
        response.append(req)
        response.extend(seed)

        if payload[1] == 0x01:
            main.security_key = level1key(seed)
            main.security_level = 1
        if payload[1] == 0x03:
            main.security_key = level2key(seed)
            main.security_level = 2
            
        if payload[1] == 0x05:
            main.security_key = level3key(seed)
            main.security_level = 3
            
    else:
        tester_key = payload[2:]
        print("Verifying key...")

        if(tester_key == main.security_key):
            response = bytearray([payload[0] + 0x40])
            response.append(payload[1])
            print("Unlocked successfully")
        else:
            response = negative_response.create_negative_response(payload[0],negative_response.NRC_SECURITY_ACCESS_DENIED)
            print("Keys did not match")
            print("testet_key : ", tester_key)
            print("security_key : ", main.security_key)

    return response