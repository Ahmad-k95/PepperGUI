#!/usr/bin/env python2
import os

# Path to your folder
folder_path = os.path.expanduser("~/Desktop/18LMtest")

# Loop through all files in the folder
for filename in os.listdir(folder_path):
    if filename.endswith(".txt") and "test" in filename:
        
        # Remove the word 'test'
        new_filename = filename.replace("test", "")
        
        old_file = os.path.join(folder_path, filename)
        new_file = os.path.join(folder_path, new_filename)
        
        # Rename file
        os.rename(old_file, new_file)
        
        print("Renamed: {} -> {}".format(filename, new_filename))

print("Done.")
