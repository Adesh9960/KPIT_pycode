import os
import threading
from data_structures.RingBuffer import RingBuffer
from data_structures.CANFrame import CANFrame
import logger.main as main
from .csv_writer import write_loop, write_to_csv

def start():
    """
    Initializes and starts the background CAN logging service.
    
    This function handles the system setup, including:
    1. Ensuring the target log directory exists.
    2. Instantiating a thread-safe lock (`ring_lock`).
    3. Allocating a `RingBuffer` with a fixed capacity of 100 elements.
    4. Spawning and running a dedicated worker thread (`write_thread`) to 
       periodically commit buffer data into CSV log files.
    """
    main.running = True

    if not os.path.exists(main.LOGGER_FOLDER_PATH):
        os.makedirs(main.LOGGER_FOLDER_PATH)
    main.ring_lock = threading.Lock()
    # initialize ring buffer
    main.ring_buffer = RingBuffer(100)

    # create csv writer thread with target = write_loop
    main.write_thread = threading.Thread(target=write_loop)
    main.write_thread.start() 
    print("Logger started")


def write_log(frame: CANFrame):
    """
    Safely pushes an incoming CAN data frame into the global ring buffer.

    Acquires a thread-safe mutex lock (`ring_lock`) before appending the data 
    to prevent race conditions with the background writer thread.

    Args:
        frame (CANFrame): The structured CAN network packet data to be logged.
    """
    try:
        with main.ring_lock:
            main.ring_buffer.push(frame)
    except Exception as e:
        print(f"LOGGER Service either not started or facing error \n Error : {e}")


def stop():
    """
    Gracefully terminates the background logging service and flushes remaining data.

    Executes a structured shutdown sequence:
    1. Sets the global execution flag to false, alerting the worker thread to stop.
    2. Waits for the worker thread to exit completely (`join`).
    3. Executes a final manual flush of remaining frames from the ring buffer into the CSV.
    4. Explicitly commits internal OS buffers (`fsync`) and safely closes active file descriptors.
    """
    main.running = False
    main.write_thread.join()
    write_to_csv()
    if main.logger_file is not None:
        main.logger_file.flush()
        os.fsync(main.logger_file.fileno())
        main.logger_file.close()
    print("Logger stopped")