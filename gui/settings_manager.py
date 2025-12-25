"""
設定持久化管理器

負責儲存和載入使用者設定（上次使用的路徑、選項等）。
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .constants import SETTINGS_FILE


class SettingsManager:
    """管理應用程式設定的持久化"""

    def __init__(self, settings_dir: Optional[Path] = None):
        if settings_dir is None:
            settings_dir = Path.home()
        self.settings_path = settings_dir / SETTINGS_FILE
        self._settings: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """從檔案載入設定"""
        if self.settings_path.exists():
            try:
                with open(self.settings_path, "r", encoding="utf-8") as f:
                    self._settings = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._settings = {}
        else:
            self._settings = {}

    def save(self) -> None:
        """儲存設定到檔案"""
        try:
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"[WARN] 無法儲存設定: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """取得設定值"""
        return self._settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """設定值"""
        self._settings[key] = value

    # ---- 便捷方法 ----

    @property
    def last_video_path(self) -> str:
        return self.get("last_video_path", "")

    @last_video_path.setter
    def last_video_path(self, value: str) -> None:
        self.set("last_video_path", value)

    @property
    def last_subs_path(self) -> str:
        return self.get("last_subs_path", "")

    @last_subs_path.setter
    def last_subs_path(self, value: str) -> None:
        self.set("last_subs_path", value)

    @property
    def last_outdir(self) -> str:
        return self.get("last_outdir", "clips")

    @last_outdir.setter
    def last_outdir(self, value: str) -> None:
        self.set("last_outdir", value)

    @property
    def check_duration(self) -> bool:
        return self.get("check_duration", True)

    @check_duration.setter
    def check_duration(self, value: bool) -> None:
        self.set("check_duration", value)

    @property
    def verbose(self) -> bool:
        return self.get("verbose", False)

    @verbose.setter
    def verbose(self, value: bool) -> None:
        self.set("verbose", value)

    @property
    def append_time_to_filename(self) -> bool:
        return self.get("append_time_to_filename", False)

    @append_time_to_filename.setter
    def append_time_to_filename(self, value: bool) -> None:
        self.set("append_time_to_filename", value)

    @property
    def precise_use_hwaccel(self) -> bool:
        return self.get("precise_use_hwaccel", True)

    @precise_use_hwaccel.setter
    def precise_use_hwaccel(self, value: bool) -> None:
        self.set("precise_use_hwaccel", value)

    @property
    def last_ranges(self) -> List[Dict[str, str]]:
        """取得上次的時間區間列表"""
        return self.get("last_ranges", [])

    @last_ranges.setter
    def last_ranges(self, value: List[Dict[str, str]]) -> None:
        self.set("last_ranges", value)

    @property
    def window_geometry(self) -> Optional[Dict[str, int]]:
        return self.get("window_geometry")

    @window_geometry.setter
    def window_geometry(self, value: Dict[str, int]) -> None:
        self.set("window_geometry", value)
