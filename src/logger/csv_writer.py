import time
import os
import shutil
import tempfile
import logger.main as main
from data_structures.CANFrame import CANFrame
import errno
file_count = 0
def write_loop():
    while main.is_running():
        time.sleep(0.5)
        write_to_csv()


def inc_file_count():
    global file_count
    file_count += 1 

def frames_to_logs(frames: list[CANFrame])-> list[str]:
    logs = [f"{frame.timestamp_ns},{frame.can_id},{frame.dlc},{frame.data.hex()}\n" for frame in frames]
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



def remove_first_n_lines(file_path: str, n: int) -> int:
    fd, temp_path = tempfile.mkstemp()
    removed = 0

    try:
        with os.fdopen(fd, "w") as temp_file:
            with open(file_path, "r") as src:
                # Skip up to n lines
                while removed < n:
                    if src.readline() == "":
                        break  # EOF reached
                    removed += 1

                # Copy the rest
                shutil.copyfileobj(src, temp_file)

        os.replace(temp_path, file_path)
        return removed

    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise

    
def cleanup_memory(n: int):
    while(n > 0):
        file_path = oldest_log_file()
        if file_path is None:
            print("No memory found")
            return
        removed = remove_first_n_lines(file_path, n)
        n -= removed
        if os.path.getsize(file_path) == 0:
            os.remove(file_path)
        # lines = []
        # with open(file_path, 'r+') as f:
        #     lines = f.readlines()
        # if len(lines) <= n:
        #     n -= len(lines)
        #     os.remove(file_path)
        # else:
        #     with open(file_path, 'w') as f:
        #         f.writelines(lines[n:])
        #     break

def perform_write(logs: list[str]):
    main.logger_file = open(main.LOGGER_FILE_PATH, 'a')
    try:
        main.logger_file.writelines(logs)
        with main.ring_lock:
            main.ring_buffer.commit()
    except OSError as e:
        match e.errno:
            case errno.ENOSPC:
                
                print("Disk full, rewriting old logs")
                cleanup_memory(len(logs))
                perform_write(logs, False)
            case errno.EACCES:
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
        if(main.logger_file is not None): 
            main.logger_file.close()
        main.set_logger_file(os.path.join(main.LOGGER_FOLDER_PATH, "log" + f"{file_count:03d}.csv"))
        inc_file_count()
    if len(logs) > 0:
        perform_write(logs)




