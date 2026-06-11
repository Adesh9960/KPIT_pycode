import unittest

from logger.logger import start, write_log
import logger.main as main
from data_structures.CANFrame import CANFrame


class TestWriteLog(unittest.TestCase):

    def test_push_frame(self):
        start()

        frame = CANFrame(
        timestamp_ns=1000,
        can_id=100,
        dlc=8,
        data=b'ABCDEF12',
        is_extended=False,
        is_fd=False,
        is_error=False
        )

        write_log(frame)
        frames = []
        with main.ring_lock:
            frames = main.ring_buffer.get_all()
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0].can_id, 100)


if __name__ == "__main__":
    unittest.main()