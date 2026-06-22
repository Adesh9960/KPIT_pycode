import os
import shutil

def delete_file(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)
        print("File deleted")

def zip_folder(folder_to_zip, output_zip):
    shutil.make_archive(output_zip, 'zip', folder_to_zip)
    print("Folder zipped successfully!")