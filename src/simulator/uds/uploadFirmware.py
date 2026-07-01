import simulator.main as main
import simulator.uds.negativeResponse as negative_response

def handleRequestUpload(payload: bytearray) -> bytearray:
    """
    Handles an incoming UDS RequestUpload (Service 0x35) diagnostic message.

    Validates that the client has successfully unlocked the necessary security 
    privileges (Security Level >= 2). If validated, it establishes state tracking
    variables inside the global application environment to stage data retrieval 
    and returns an explicit positive response.

    Args:
        payload (bytearray): The raw request packet containing target addresses and sizes.

    Returns:
        bytearray: A UDS positive response frame (0x75) or a specific Negative Response (NRC 0x33).
    """
    print("Current security level : ", main.security_level)
    
    # Security Gate: Flashing or data extraction routines require specific privilege thresholds
    if main.security_level < 2:
        return negative_response.create_negative_response(
            0x35,
            negative_response.NRC_SECURITY_ACCESS_DENIED
        )

    # Transition to data transfer state
    main.upload_active = True
    main.upload_offset = 0

    return bytearray([
        0x75,  # Positive Response Service Identifier (0x35 + 0x40)
        0x20,  # Length Format Identifier
        0x08   # Max Number of Block Length parameter
    ])


# Define the specific slice size read from the master binary frame array for each block transfer request
CHUNK_SIZE = 8


def handleTransferDataUpload(payload: bytearray) -> bytearray:
    """
    Handles an incoming UDS TransferData (Service 0x36) block transmission request.

    This function chunks data out of the central firmware image array based on the 
    current operational read offset index. It increments tracking offsets iteratively, 
    safeguarding operations by enforcing proper sequence verification via internal 
    state variables.

    Args:
        payload (bytearray): The input data transaction packet containing the block counter index.

    Returns:
        bytearray: A serialized byte array embedding positive response codes (0x76), the current 
                   block counter, and the raw firmware segment payload slice.
    """
    # Sequence Verification: Block unauthorized reading if RequestUpload wasn't executed first
    if not main.upload_active:
        return negative_response.create_negative_response(
            0x36,
            negative_response.NRC_REQUEST_SEQUENCE_ERROR
        )

    # Extract the block sequence sequence token provided by the client (index 1)
    block_counter = payload[1]

    # Calculate current data boundary dimensions 
    start = main.upload_offset
    end = start + CHUNK_SIZE

    # Slice the raw target text segment data out of memory
    chunk = main.firmware_image[start:end]

    # Advance the master memory pointer by the actual size of the extracted block array (handles EOF bounds safely)
    main.upload_offset += len(chunk)

    # Formulate the baseline structural response array frame
    response = bytearray([
        0x76,  # Positive Response Service Identifier (0x36 + 0x40)
        block_counter
    ])

    # Append the raw text frame slice data directly to the end of the byte sequence
    response.extend(chunk)

    return response


def handleTransferExitUpload(payload: bytearray) -> bytearray:
    """
    Handles an incoming UDS RequestTransferExit (Service 0x37) finalization request.

    Closes down the active data transaction pipe and systematically clears out and 
    resets state tracking offsets back to standard safe baselines.

    Args:
        payload (bytearray): The finalization control frame payload packet.

    Returns:
        bytearray: A short confirmation positive response frame (0x77).
    """
    # Sequence Verification: Enforce execution order restrictions
    if not main.upload_active:
        return negative_response.create_negative_response(
            0x37,
            negative_response.NRC_REQUEST_SEQUENCE_ERROR
        )

    # Deactivate the session download permissions and clear cache structures
    main.upload_active = False
    main.upload_offset = 0

    return bytearray([
        0x77  # Positive Response Service Identifier (0x37 + 0x40)
    ])