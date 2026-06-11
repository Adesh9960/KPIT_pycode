import unittest
from unittest.mock import MagicMock

import listener.main as main
from transmitter import transmit


class DummyRequest:
    def __init__(self):
        self.payload = object()
        self.request_type = "raw_can"
        self.retry_count = 0
        self.max_retries = 3
        self.timeout_ms = 0
        self.next_retry_time = 0
        self.uds_error_callback = MagicMock()


class TestTransmit(unittest.TestCase):

    def setUp(self):
        main.adapter = MagicMock()
        main.retry_queue = []

    def test_successful_send(self):
        req = DummyRequest()

        transmit(req)

        main.adapter.send.assert_called_once_with(req.payload)
        self.assertEqual(len(main.retry_queue), 0)


if __name__ == "__main__":
    unittest.main()