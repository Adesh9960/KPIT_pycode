import zlib
class SecurityAccessError(Exception):
    pass
ALLOWED_LEVELS = [1, 2, 3]
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

def calculate_key(self, seed: bytes, level) -> bytes:
        """
        Must match ECU algorithm.
        Demo algorithm only.
        """
        if ALLOWED_LEVELS.count(level) == 0:
             return b"incorrectvalue"
        if level == 3:
            return level3key(seed)
        if level == 2:
            return level2key(seed)
        if level == 1:
            return level1key(seed)
            
        return b"incorrectvalue"
    
def security_access(self, level: int = 1):
        request_seed_subfunction = (level * 2) - 1
        send_key_subfunction = level * 2

        # Step 1: Request Seed
        response = self.send_and_wait(
            bytes([
                0x27,
                request_seed_subfunction
            ]),
            5
        )

        # Check positive response
        if response[0] != 0x67:
            raise SecurityAccessError(
                f"Negative response: {response.hex()}"
            )

        seed = response[2:]

        print(f"Received seed: {seed.hex()}")

        # Step 2: Calculate key
        key = self.calculate_key(seed)

        print(f"Calculated key: {key.hex()}")

        # Step 3: Send Key
        response = self.send_and_wait(
            bytes([
                0x27,
                send_key_subfunction
            ]) + key
        )

        if response != bytes([
            0x67,
            send_key_subfunction
        ]):
            raise SecurityAccessError(
                f"Unlock failed: {response.hex()}"
            )

        print("Security Access Granted")
        return True