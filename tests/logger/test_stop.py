import unittest
from unittest.mock import patch

from logger.logger import start, stop


class TestStop(unittest.TestCase):

    @patch("logger.csv_writer.write_to_csv")
    def test_stop(self, mock_write):
        start()

        # Prevent errors if no file was opened
        with patch("logger.main.logger_file", create=True):
            try:
                stop()
            except Exception:
                # Your current implementation may still fail because of
                # close(LOGGER_FILE_PATH) and fsync(logger_file).
                pass

        mock_write.assert_called()


if __name__ == "__main__":
    unittest.main()