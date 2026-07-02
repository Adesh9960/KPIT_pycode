import unittest

from logger.csv_writer import frames_to_logs
from data_structures.CANFrame import CANFrame


class TestFramesToLogs(unittest.TestCase):

    def test_single_frame(self):
        frame = CANFrame(
            timestamp_ns=123456789,
            can_id=0x123,
            dlc=8,
            data=b"\x01\x02\x03\x04\x05\x06\x07\x08",
            is_extended=False,
            is_fd=False,
            is_error=False
        )

        logs = frames_to_logs([frame])

        self.assertEqual(len(logs), 1)
        self.assertIn("123456789", logs[0])
        self.assertIn("0x123", logs[0]) 


if __name__ == "__main__":
    unittest.main()