import shutil
from pathlib import Path
from datetime import datetime

# SOURCE: read-only
SRC = Path("E:/gallery")

# DESTINATION ROOT
DST_ROOT = Path("C:/")

def main():
    if not SRC.exists():
        print(f"Source not found: {SRC}")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    dst = DST_ROOT / f"gallery-backup_{timestamp}"

    print(f"Backing up from: {SRC}")
    print(f"Backing up to:   {dst}")

    shutil.copytree(SRC, dst)

    print("Backup completed successfully.")
    print("Source was not modified.")

if __name__ == "__main__":
    main()
