
import simulator.main as main
import simulator.uds.negativeResponse as negative_response
def handleRequestUpload(payload: bytearray):
    if main.security_level < 2:
        return negative_response.create_negative_response(
            0x35,
            negative_response.NRC_SECURITY_ACCESS_DENIED
        )

    main.upload_active = True
    main.upload_offset = 0

    return bytearray([
        0x75,  # Positive response
        0x20,
        0x08
    ])


CHUNK_SIZE = 8


def handleTransferDataUpload(payload: bytearray):

    if not main.upload_active:
        return negative_response.create_negative_response(
            0x36,
            negative_response.NRC_REQUEST_SEQUENCE_ERROR
        )

    block_counter = payload[1]

    start = main.upload_offset
    end = start + CHUNK_SIZE

    chunk = main.firmware_image[start:end]

    main.upload_offset += len(chunk)

    response = bytearray([
        0x76,
        block_counter
    ])

    response.extend(chunk)

    return response

def handleTransferExitUpload(payload: bytearray):

    if not main.upload_active:
        return negative_response.create_negative_response(
            0x37,
            negative_response.NRC_REQUEST_SEQUENCE_ERROR
        )

    main.upload_active = False
    main.upload_offset = 0

    return bytearray([0x77])