from pathlib import Path
import sys

# Directories
BASE_DIR = Path(__file__).parent.parent
if 'win' in sys.platform:
    ROOT_DIR = BASE_DIR
else:
    ROOT_DIR = "/tmp/data"

# Starting message
START_MESSAGE = "OK"