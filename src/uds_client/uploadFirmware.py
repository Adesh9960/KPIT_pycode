from uds_client.UDSError import UDSError
import os
def request_upload(self):
    """
    Request firmware from ECU.

    Request:
        35

    Response:
        75 20 08
    """

    response = self.send_and_wait(
        bytes([0x35]),
        timeout=5
    )

    if response[0] != 0x75:
        raise UDSError(response)

    max_chunk_size = response[2]

    print(
        f"Upload accepted. "
        f"Chunk size={max_chunk_size}"
    )

    return max_chunk_size



def transfer_data_upload(
    self,
    block_counter: int
):
    """
    Request next chunk.

    Request:
        36 <blockCounter>

    Response:
        76 <blockCounter> <data>
    """

    response = self.send_and_wait(
        bytes([
            0x36,
            block_counter
        ]),
        timeout=5
    )

    if response[0] != 0x76:
        raise UDSError(
            response
        )

    if response[1] != block_counter:
        raise UDSError(
            response
        )

    return response[2:]




def transfer_exit_upload(self):
    """
    Request:
        37

    Response:
        77
    """

    response = self.send_and_wait(
        bytes([0x37]),
        timeout=5
    )

    if response != bytes([0x77]):
        raise UDSError(
            response
        )

    print("Upload complete")

    return True



def read_firmware_from_ecu(
    self,
    output_file: str
):
    firmware = bytearray()

    self.request_upload()

    block_counter = 1

    while True:

        chunk = self.transfer_data_upload(
            block_counter
        )

        if len(chunk) == 0:
            break

        firmware.extend(chunk)

        print(
            f"Received block "
            f"{block_counter} "
            f"({len(chunk)} bytes)"
        )

        block_counter += 1

        if block_counter > 255:
            block_counter = 1

    self.transfer_exit_upload()
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "wb") as f:
        f.write(firmware)

    print(
        f"Downloaded "
        f"{len(firmware)} bytes"
    )

    return bytes(firmware)