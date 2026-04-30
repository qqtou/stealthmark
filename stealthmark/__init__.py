# stealthmark package - auto-add src to path so relative imports work
import sys
from pathlib import Path

# Add project_root/src so 'src.' imports work from here
_stealthmark_root = Path(__file__).parent  # .../stealthmark/
_project_root = _stealthmark_root.parent     # .../stealthmark project root
_src_path = str(_project_root / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

from src.core.manager import StealthMark
from src.core.base import WatermarkData, WatermarkStatus

__all__ = ["StealthMark", "WatermarkData", "WatermarkStatus"]
