import unittest
import queue

import listener.main as main
from listener.listener import send_to_tx_queue
from listener.TxRequest import TxRequest, TxRequestType


class TestTxQueue(unittest.TestCase):

    def setUp(self):
        main.tx_queue = queue.PriorityQueue()

    def test_enqueue(self):
        req = TxRequest(
            priority=1,
            enqueue_timestamp_ns=0,
            request_id=1,
            request_type=TxRequestType.RAWCAN,
            payload=None,
            max_retries=3,
            timeout_ms=100,
            uds_error_callback=None,
            confirmation_callback=None,
        )

        send_to_tx_queue(req)

        result = main.tx_queue.get_nowait()

        self.assertEqual(result.request_id, 1)


if __name__ == "__main__":
    unittest.main()