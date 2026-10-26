import sys
from pathlib import Path

# The fake upstream is a helper module that sits beside the tests.
sys.path.insert(0, str(Path(__file__).parent))
