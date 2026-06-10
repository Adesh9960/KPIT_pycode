import time
import os
import logger.main as main
from data_structures.CANFrame import CANFrame
file_count = 0
def write_loop():
    while main.is_running():
        time.sleep(0.5)
        write_to_csv()


def inc_file_count():
    global file_count
    file_count += 1 

def frames_to_logs(frames: list[CANFrame])-> list[str]:
    logs = [f"{frame.timestamp_ns},{frame.can_id},{frame.dlc},{frame.data}\n" for frame in frames]
    return logs

def write_to_csv():
    frames = []
    with main.ring_lock:
        frames = main.ring_buffer.get_all()
    logs = frames_to_logs(frames)
    if main.LOGGER_FILE_PATH is None or os.path.getsize(main.LOGGER_FILE_PATH) >= 104857600:
        main.set_logger_file(os.path.join(main.LOGGER_FOLDER_PATH, "log" + f"{file_count:03d}.csv"))
        inc_file_count()
        if(main.logger_file is not None): 
            main.logger_file.close()
        main.logger_file = open(main.LOGGER_FILE_PATH, 'a')
    try:
        main.logger_file.writelines(logs)
        with main.ring_lock:
            main.ring_buffer.commit()
    except OSError as e:
        match e.errno:
            case e.errno.ENOSPC:
                print("Disk full, stopping logger")
            case e.errno.EACCES:
                print("Permission denied")
            case _:
                print(f"Unexpected I/O error: {e}")


    
    

        
    
    