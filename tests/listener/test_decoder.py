import unittest

from listener.error_decoder import (
    decode_error,
    CAN_ERR_ACK,
    CAN_ERR_BUSOFF,
)
from data_structures.CANFrame import CANFrame


class TestDecodeError(unittest.TestCase):

    def test_ack_error(self):
        frame = CANFrame(
            can_id=CAN_ERR_ACK,
            dlc=0,
            data=b"",
            timestamp_ns=0,
            is_error=True,
            is_extended=False,
            is_fd=False
        )

        decode_error(frame)

        self.assertIn("ACK error", frame.details)

    def test_multiple_errors(self):
        frame = CANFrame(
            can_id=CAN_ERR_ACK | CAN_ERR_BUSOFF,
            dlc=0,
            data=b"",
            timestamp_ns=0,
            is_error=True,
            is_extended=False,
            is_fd=False
        )

        decode_error(frame)

        self.assertIn("ACK error", frame.details)
        self.assertIn("Bus-Off", frame.details)


if __name__ == "__main__":
    unittest.main()