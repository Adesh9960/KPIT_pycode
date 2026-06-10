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


def oldest_log_file() -> str:
    files = [
        os.path.join(main.LOGGER_FOLDER_PATH, f)
        for f in os.listdir(main.LOGGER_FOLDER_PATH)
        if os.path.isfile(os.path.join(main.LOGGER_FOLDER_PATH, f))
    ]

    if files:
        oldest_log_file = min(files, key=os.path.getmtime)
        return oldest_log_file
    else:
        print("No files found.")
        return None

def cleanup_memory(n: int):
    file_path = oldest_log_file()
    
    if file_path is None:
        print("No memory found")
        lines = []
    while(n != 0):
        with open(file_path, 'r+') as f:
            lines = f.readlines()
        if len(lines) <= n:
            n -= len(lines)
            os.remove(file_path)
        else:
            with open(file_path, 'w') as f:
                f.writelines(lines[n:])
            break

def perform_write(logs: list[str]):
    main.logger_file = open(main.LOGGER_FILE_PATH, 'a')
    try:
        main.logger_file.writelines(logs)
        with main.ring_lock:
            main.ring_buffer.commit()
    except OSError as e:
        match e.errno:
            case e.errno.ENOSPC:
                print("Disk full, rewriting old logs")
                cleanup_memory(len(logs))
                perform_write(logs)
            case e.errno.EACCES:
                print("Permission denied")
                main.set_logger_file(os.path.join(main.LOGGER_FOLDER_PATH, "log" + f"{file_count:03d}.csv"))
                time.sleep(1)
                inc_file_count()
            case _:
                print(f"Unexpected I/O error: {e}")
    
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
    perform_write(logs)




