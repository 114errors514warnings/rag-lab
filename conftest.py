"""确保无论从哪个目录调用 pytest，项目根都在 import 路径上。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
