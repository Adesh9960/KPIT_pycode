import unittest
from unittest.mock import MagicMock, patch
import queue

import listener.main as main
from receiver import receiver


class DummyFrame:
    def __init__(self):
        self.can_id = 0x100
        self.is_error = False


class DummyMonitor:
    def __init__(self):
        self.last_rx_time = 0


class TestReceiver(unittest.TestCase):

    @patch("receiver.is_UDS", return_value=False)
    @patch("receiver.write_log")
    def test_receive_normal_frame(self, _, __):
        frame = DummyFrame()

        main.adapter = MagicMock()
        main.adapter.receive.side_effect = [frame, KeyboardInterrupt()]

        main.can_queue = queue.Queue()
        main.uds_queue = queue.Queue()
        main.message_monitor_list = {
            frame.can_id: DummyMonitor()
        }

        try:
            receiver()
        except KeyboardInterrupt:
            pass

        self.assertEqual(main.can_queue.qsize(), 1)


if __name__ == "__main__":
    unittest.main()