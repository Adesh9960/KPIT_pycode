import time
import os
import shutil
import tempfile
import logger.main as main
from data_structures.CANFrame import CANFrame
import errno

file_count = 0

def write_loop():
    """
    Runs an infinite background loop that periodically invokes the CSV writing sequence.
    
    Monitors the system status via `main.is_running()`, pausing for 0.5 seconds 
    between polling iterations to prevent high CPU utilization.
    """
    while main.is_running():
        time.sleep(0.5)
        write_to_csv()


def inc_file_count():
    """
    Increments the global `file_count` tracker by 1.
    
    Used to keep track of sequential naming for newly generated log files.
    """
    global file_count
    file_count += 1 


def frames_to_logs(frames: list[CANFrame]) -> list[str]:
    """
    Converts a list of structured CANFrame objects into formatted CSV string lines.

    Args:
        frames (list[CANFrame]): A list of CANFrame data structures to convert.

    Returns:
        list[str]: A list of raw CSV-formatted strings ready to be written to a file,
                   each ending with a newline character.
    """
    if type(frames) == "list[str]":
        print("error : ", frames)
    logs = [f"{frame.timestamp_ns}, {hex(frame.can_id)}, {frame.dlc}, {frame.data.hex()}, {frame.details}\n" for frame in frames]
    return logs


def oldest_log_file() -> str | None:
    """
    Scans the logger directory to find the oldest modified log file.

    Returns:
        str: The absolute path to the oldest log file found.
        None: If the target logging directory contains no files.
    """
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


def latest_log_file() -> str | None:
    """
    Scans the logger directory to find the most recently modified log file.

    Returns:
        str: The absolute path to the latest log file found.
        None: If the target logging directory is empty.
    """
    files = [
        os.path.join(main.LOGGER_FOLDER_PATH, f)
        for f in os.listdir(main.LOGGER_FOLDER_PATH)
        if os.path.isfile(os.path.join(main.LOGGER_FOLDER_PATH, f))
    ]
    if len(files) == 0: return None
    latest_file = max(files, key=os.path.getmtime)
    return latest_file


def remove_first_n_lines(file_path: str, n: int) -> int:
    """
    Removes a specified number of lines from the beginning of a file.

    Creates a temporary file, skips the first `n` lines of the source file, 
    copies the remaining contents over, and safely replaces the original file.

    Args:
        file_path (str): The path to the file that needs trimming.
        n (int): The maximum number of lines to remove from the top.

    Returns:
        int: The actual number of lines removed (could be less than `n` if EOF was reached).
        
    Raises:
        Exception: Relays any underlying I/O exceptions while guaranteeing 
                   the cleanup of the temporary file.
    """
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
    """
    Frees up space on the disk by iteratively truncating lines from older log files.

    Loops through files starting from the oldest, deleting lines until a total 
    of `n` lines have been purged. Completely deletes files that become empty.

    Args:
        n (int): The total target number of lines to clear out of the log history.
    """
    while(n > 0):
        file_path = oldest_log_file()
        if file_path is None:
            print("No memory found")
            return
        removed = remove_first_n_lines(file_path, n)
        n -= removed
        if os.path.getsize(file_path) == 0:
            os.remove(file_path)


def perform_write(logs: list[str]):
    """
    Appends the formatted log entries directly into the active logger file.

    Handles explicit OS errors such as full disk space (by triggering a memory 
    cleanup of old logs) and permission denials (by rolling over to a new 
    sequentially numbered log file).

    Args:
        logs (list[str]): A list of pre-formatted string lines to write.
    """
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
                perform_write(logs)  # Note: Removed the invalid second parameter here
            case errno.EACCES:
                print("Permission denied")
                main.set_logger_file(os.path.join(main.LOGGER_FOLDER_PATH, "log" + f"{file_count:03d}.csv"))
                time.sleep(1)
                inc_file_count()
            case _:
                print(f"Unexpected I/O error: {e}")
    

def write_to_csv():
    """
    Orchestrates the process of pulling data from the ring buffer and writing to disk.

    Fetches available CAN frames within a thread-safe lock, formats them, validates 
    the active log file's state (existence and size constraints), handles log 
    rotation if a file exceeds 100MB, and hands off data to `perform_write`.
    """
    frames = []
    with main.ring_lock:
        frames = main.ring_buffer.get_all()
    logs = frames_to_logs(frames)
    if len(logs) <= 0:
        return

    if main.LOGGER_FILE_PATH is None or (not os.path.exists(main.LOGGER_FILE_PATH)) or os.path.getsize(main.LOGGER_FILE_PATH) >= 104857600:
        if(main.LOGGER_FILE_PATH is not None and os.path.exists(main.LOGGER_FILE_PATH)): 
            main.logger_file.close()
        if(main.LOGGER_FILE_PATH is None): main.set_logger_file(latest_log_file())
        if main.LOGGER_FILE_PATH is None: 
            main.set_logger_file(os.path.join(main.LOGGER_FOLDER_PATH, "log" + f"{file_count:03d}.csv"))
            inc_file_count()

    perform_write(logs)