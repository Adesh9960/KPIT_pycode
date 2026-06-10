import os
import threading
from data_structures.RingBuffer import RingBuffer
from io import TextIOWrapper

running = False
ring_buffer: None | RingBuffer = None
ring_lock: threading.Lock  = None
SRC_DIR = os.getcwd()
PROJECT_ROOT = os.path.dirname(SRC_DIR)
LOGGER_FOLDER_PATH = os.path.join(PROJECT_ROOT, "data", "logger")
LOGGER_FILE_PATH = None
logger_file: TextIOWrapper = None
write_thread: threading.Thread = None
def is_running()->bool:
    return running

def set_logger_file(path):
    global LOGGER_FILE_PATH
    LOGGER_FILE_PATH = path
