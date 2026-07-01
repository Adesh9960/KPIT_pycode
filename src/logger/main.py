import os
import threading
from data_structures.RingBuffer import RingBuffer
from io import TextIOWrapper

# ==========================================
# Global Service State & Synchronization
# ==========================================

# Flag indicating whether the background logger thread is actively running
running = False

# The thread-safe storage buffer holding incoming CANFrames before they are written to disk
ring_buffer: None | RingBuffer = None

# Mutex lock to synchronize buffer operations between the producer (main thread) and consumer (writer thread)
ring_lock: threading.Lock = None

# ==========================================
# File System & Path Configurations
# ==========================================

# Current working directory where the script execution started
SRC_DIR = os.getcwd()

# The top-level root directory of the project
PROJECT_ROOT = os.path.dirname(SRC_DIR)

# Target directory path where all generated CSV log files will be saved
LOGGER_FOLDER_PATH = os.path.join(PROJECT_ROOT, "data", "logger")

# The absolute path to the active, open CSV log file
LOGGER_FILE_PATH = None

# The active file stream object used to perform write operations
logger_file: TextIOWrapper = None

# ==========================================
# Threading
# ==========================================

# Handle for the background worker thread dedicated to writing data to CSV files
write_thread: threading.Thread = None


def is_running() -> bool:
    """
    Checks the active execution state of the logging service.

    Returns:
        bool: True if the background logging thread is active, False otherwise.
    """
    return running


def set_logger_file(path: str | None):
    """
    Updates the global target path configuration for the active log file.

    This is used by the writing service when rotating files or switching to a 
    new file due to file size limits or system file permissions.

    Args:
        path (str | None): The new absolute file path to use for logging data.
    """
    global LOGGER_FILE_PATH
    LOGGER_FILE_PATH = path