"""Root convenience launcher for AI Knowledge Wrapper."""

import sys
from pathlib import Path

# Add 'src' and root directory to sys.path
root_dir = Path(__file__).resolve().parent
src_dir = root_dir / "src"

for d in [str(src_dir), str(root_dir)]:
    if d not in sys.path:
        sys.path.insert(0, d)

from akw.cli import main

if __name__ == "__main__":
    main()

