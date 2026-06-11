import unittest
import os
import sys

# print("cwd =", os.getcwd())
# print("path =", sys.path)
from src.data_structures.CANFrame import CANFrame
from src.data_structures.RingBuffer import RingBuffer


def frame(i):
    return CANFrame(
        timestamp_ns=i * 1000,
        can_id=i,
        dlc=8,
        data=bytes([i] * 8),
        is_extended=False,
        is_fd=False,
        is_error=False
    )


class TestRingBuffer(unittest.TestCase):

    def test_empty(self):
        rb = RingBuffer(5)

        self.assertTrue(rb.is_empty())
        self.assertEqual(rb.size(), 0)

    def test_single_push(self):
        rb = RingBuffer(5)

        rb.push(frame(1))

        self.assertFalse(rb.is_empty())
        self.assertEqual(rb.size(), 1)

    def test_fill_buffer(self):
        rb = RingBuffer(5)

        for i in range(5):
            rb.push(frame(i))

        self.assertTrue(rb.is_full())
        self.assertEqual(rb.size(), 5)

    def test_overwrite(self):
        rb = RingBuffer(5)

        for i in range(7):
            rb.push(frame(i))

        data = rb.get_all()

        ids = [f.can_id for f in data]

        self.assertEqual(ids, [2, 3, 4, 5, 6])

    def test_commit_all(self):
        rb = RingBuffer(5)

        for i in range(5):
            rb.push(frame(i))

        rb.get_all()
        rb.commit()

        self.assertTrue(rb.is_empty())
        self.assertEqual(rb.size(), 0)

    def test_partial_after_commit(self):
        rb = RingBuffer(5)

        for i in range(3):
            rb.push(frame(i))

        rb.get_all()
        rb.commit()

        rb.push(frame(100))

        self.assertEqual(rb.size(), 1)

    def test_multiple_wraps(self):
        rb = RingBuffer(3)

        for i in range(20):
            rb.push(frame(i))

        data = rb.get_all()

        ids = [f.can_id for f in data]

        self.assertEqual(ids, [17, 18, 19])


if __name__ == "__main__":
    unittest.main()