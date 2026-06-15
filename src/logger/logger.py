import os
import threading
from data_structures.RingBuffer import RingBuffer
from data_structures.CANFrame import CANFrame
import logger.main as main
from .csv_writer import write_loop, write_to_csv

def start():

    main.running = True

    if not os.path.exists(main.LOGGER_FOLDER_PATH):
        os.makedirs(main.LOGGER_FOLDER_PATH)
    main.ring_lock = threading.Lock()
    # initialize ring buffer
    main.ring_buffer = RingBuffer(100)

    # #create csv writer thread with target = write_loop
    main.write_thread = threading.Thread(target=write_loop)
    main.write_thread.start() 
    print("Logger started")

def write_log(frame: CANFrame):
    try:
        with main.ring_lock:
            main.ring_buffer.push(frame)
    except Exception as e:
        print(f"LOGGER Service either not started or facing error \n Error : {e}")

def stop():
    main.running = False
    main.write_thread.join()
    write_to_csv()
    if main.logger_file is not None:
        main.logger_file.flush()
        os.fsync(main.logger_file.fileno())
        main.logger_file.close()
    print("Logger stopped")
