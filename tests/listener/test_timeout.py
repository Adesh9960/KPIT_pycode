import unittest
from unittest.mock import MagicMock

import listener.main as main
from timeout import check_timeouts


class DummyMonitor:
    def __init__(self):
        self.last_rx_time = 0
        self.timeout_ms = 0
        self.callback = MagicMock()


class TestTimeout(unittest.TestCase):

    def test_timeout_callback_called(self):
        monitor = DummyMonitor()

        main.message_monitor_list = {
            0x100: monitor
        }

        check_timeouts()

        monitor.callback.assert_called_once()


if __name__ == "__main__":
    unittest.main()