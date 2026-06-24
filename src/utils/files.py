import os
import shutil
import time
def delete_file(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)
        print("File deleted")

def zip_folder(folder_to_zip, output_zip):
    try:
        print("Starting zip...")
        start = time.time()

        result = shutil.make_archive(
            output_zip,
            'zip',
            folder_to_zip
        )

        print("Created:", result)
        print("Time taken:", time.time() - start)

    except Exception as e:
        print("ZIP ERROR:", repr(e))
        raise