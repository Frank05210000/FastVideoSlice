#!/usr/bin/env python3
"""
FastVideoSlice GUI 啟動入口

執行方式：
  python -m gui
  或
  python gui/__main__.py
"""

import sys
from pathlib import Path

# 確保可以匯入父目錄的模組
sys.path.insert(0, str(Path(__file__).parent.parent))

from gui.main_window import run_app

if __name__ == "__main__":
    sys.exit(run_app())
