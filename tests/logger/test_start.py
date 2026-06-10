import unittest
import os
import sys
import sys
print("cwd =", os.getcwd())
print("path =", sys.path)
from logger.logger import start
import logger.main as main


class TestStart(unittest.TestCase):

    def test_start_initializes_logger(self):
        start()

        self.assertTrue(main.running)
        self.assertIsNotNone(main.ring_buffer)
        self.assertIsNotNone(main.write_thread)


if __name__ == "__main__":
    unittest.main()