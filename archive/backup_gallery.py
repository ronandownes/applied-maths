import os
import shutil
from datetime import datetime

source_dir = os.path.dirname(os.path.abspath(__file__))
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
holder_dir = "C:/gallery-backups"
dest_dir = os.path.join(holder_dir, f"gallery-{timestamp}")

# Clean prior conflicts
if os.path.exists(dest_dir):
    shutil.rmtree(dest_dir, ignore_errors=True)

# Ensure holder exists
os.makedirs(holder_dir, exist_ok=True)

shutil.copytree(source_dir, dest_dir)
print(f"Backup: {dest_dir}")
