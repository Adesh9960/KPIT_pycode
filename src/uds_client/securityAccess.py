import zlib

class SecurityAccessError(Exception):
    """Exception raised when a UDS Security Access (Service 0x27) transaction fails or is rejected."""
    pass

# Validation array containing the explicit security levels supported by this client interface
ALLOWED_LEVELS = [0, 1, 2, 3]

def level1key(seed: bytes) -> bytes:
    """
    Computes the security key for Level 1 access using a bitwise XOR algorithm.

    Args:
        seed (bytes): The raw seed byte array generated and sent by the ECU server.

    Returns:
        bytes: The calculated response key array where each byte is masked with 0xA5.
    """
    return bytes(b ^ 0xA5 for b in seed)


def level2key(seed: bytes) -> bytes:
    """
    Computes the security key for Level 2 access using a bitwise rotation and XOR mask.

    Performs an 8-bit left rotation by 3 bits on each byte, isolates the byte mask 
    boundary, and applies a fixed 0x5C bitwise XOR operation.

    Args:
        seed (bytes): The raw seed byte array generated and sent by the ECU server.

    Returns:
        bytes: The transformed deterministic response key byte array.
    """
    key = bytearray()
    for b in seed:
        # Rotate bits left by 3 places, shifting overflowing high bits back into the lower 3 positions
        rotated = ((b << 3) | (b >> 5)) & 0xFF
        key.append(rotated ^ 0x5C)
    return bytes(key)


def level3key(seed: bytes) -> bytes:
    """
    Computes the security key for Level 3 access using a standard CRC32 checksum.

    Args:
        seed (bytes): The raw seed byte array generated and sent by the ECU server.

    Returns:
        bytes: A 4-byte big-endian representation of the calculated CRC32 scalar.
    """
    crc = zlib.crc32(seed)
    return crc.to_bytes(4, "big")


def calculate_key(seed: bytes, level: int) -> bytes:
    """
    Routes the input security seed to its respective level-dependent key derivation algorithm.

    Acts as a factory method mapping requests to specified internal key generation procedures. 
    Must identically mimic the target ECU's internal firmware authentication validation matrix.

    Args:
        seed (bytes): The raw variable-length seed array retrieved from the server.
        level (int): The target security access level index being negotiated.

    Returns:
        bytes: The computed verification key array, or b"incorrectvalue" if validation parameters fail.
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


def security_access(self, level: int = 1) -> bool: 
    """
    Executes the standard ISO 14229 Security Access (Service 0x27) handshake sequence.

    Coordinates a synchronized two-step handshake pipeline with the remote ECU node:
    1. **Request Seed:** Sends a request using an odd sub-function code `(level * 2) - 1`.
    2. **Send Key:** Transforms the returned seed using the corresponding algorithm and transmits 
       the verification key using an even sub-function code `level * 2`.

    Level 0 handles a special bypass case to check or drop active security tiers.

    Args:
        level (int, optional): The diagnostic security level to unlock. Defaults to 1.

    Returns:
        bool: True if security verification succeeds and access privileges are granted.

    Raises:
        SecurityAccessError: If the server rejects the security frame, provides a 
                             Negative Response Code (NRC), or verification keys mismatch.
    """
    # Special Handling: Level 0 drops or checks the current access security state
    if level == 0:
        response = self.send_and_wait(
              bytes([
                   0x27,
                   0x00
              ]), 5
         )   
        return True 

    # Derive standard ISO 14229 sub-function rules: Seed requests are odd, Key submissions are even
    request_seed_subfunction = (level * 2) - 1
    send_key_subfunction = level * 2

    # ----------------------------------------------------
    # Step 1: Request Seed from the Server Node
    # ----------------------------------------------------
    response = self.send_and_wait(
        bytes([
            0x27,
            request_seed_subfunction
        ]),
        5
    )

    # Validate standard Service Positive Response offset calculation (0x27 + 0x40 = 0x67)
    if response[0] != 0x67:
        raise SecurityAccessError(
            f"Negative response: {response.hex()}"
        )

    # Extract seed bytes, omitting the Service ID (index 0) and Sub-function ID (index 1)
    seed = response[2:]
    print(f"Received seed: {seed.hex()}")

    # ----------------------------------------------------
    # Step 2: Compute the verification cryptographic Key
    # ----------------------------------------------------
    key = calculate_key(seed, level)
    print(f"Calculated key: {key.hex()}")

    # ----------------------------------------------------
    # Step 3: Transmit Key back to Server for validation
    # ----------------------------------------------------
    response = self.send_and_wait(
        bytes([
            0x27,
            send_key_subfunction
        ]) + key,
        5
    )
    print("Final response: ", response)
    
    # Confirm server confirmed authorization matching the positive submission signature
    if response != bytes([
        0x67,
        send_key_subfunction
    ]):
        raise SecurityAccessError(
            f"Unlock failed: {response.hex()}"
        )

    print("Security Access Granted")
    return True