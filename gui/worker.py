"""
背景工作執行緒

負責在背景執行 ffmpeg 裁切任務，避免阻塞 UI。
"""

from pathlib import Path
from typing import List, Optional
import sys
import os

from PyQt5.QtCore import QThread, pyqtSignal

# 將父目錄加入路徑以匯入 fast_video_slice
sys.path.insert(0, str(Path(__file__).parent.parent))
import fast_video_slice as fvs


class SliceWorker(QThread):
    """背景裁切工作執行緒"""

    # 信號定義
    progress = pyqtSignal(int, int, str)  # current, total, message
    log = pyqtSignal(str)  # log message
    finished_ok = pyqtSignal(list)  # output files list
    finished_error = pyqtSignal(str)  # error message

    def __init__(
        self,
        video: Path,
        subs: Path,
        ranges: List[dict],
        outdir: Path,
        check_duration: bool,
        verbose: bool,
        append_time: bool = False,
        subs_overrides: List[str | None] | None = None,
        precise_flags: List[bool] | None = None,
        use_hwaccel: bool = True,
        adjusted_flags: List[bool] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.video = video
        self.subs = subs
        self.ranges = ranges
        self.outdir = outdir
        self.check_duration = check_duration
        self.verbose = verbose
        self.append_time = append_time
        self.subs_overrides = subs_overrides or []
        self.precise_flags = precise_flags or []
        self.use_hwaccel = use_hwaccel
        self._hwaccel_config: fvs.HWAccelConfig | None = None
        self.adjusted_flags = adjusted_flags or []
        self._cancelled = False

    def cancel(self) -> None:
        """取消任務"""
        self._cancelled = True

    def run(self) -> None:
        output_files = []
        try:
            self.log.emit("開始處理...")

            # 驗證檔案
            self.log.emit(f"檢查檔案: {self.video.name}, {self.subs.name}")
            fvs.check_files(self.video, self.subs)

            # 解析時間區間
            parsed_ranges = []
            for r in self.ranges:
                # 若有標題，使用「標題,HH:MM:SS -> HH:MM:SS」格式
                if r.get("title"):
                    range_str = f"{r['title']},{r['start']} -> {r['end']}"
                else:
                    range_str = f"{r['start']} -> {r['end']}"
                parsed_ranges.append(fvs.parse_range(range_str))

            # 確保輸出目錄
            fvs.ensure_outdir(self.outdir)
            self.log.emit(f"輸出資料夾: {self.outdir}")

            # 確認 ffmpeg/ffprobe 路徑
            ffmpeg_cmd, ffprobe_cmd = fvs.ensure_ffmpeg_exists()
            self.log.emit(f"使用 ffmpeg: {ffmpeg_cmd}")
            self.log.emit(f"使用 ffprobe: {ffprobe_cmd}")
            if self.use_hwaccel:
                self._hwaccel_config = fvs.detect_hwaccel(ffmpeg_cmd)
                if self._hwaccel_config:
                    self.log.emit(f"硬體編碼: {self._hwaccel_config.name}")
                else:
                    self.log.emit("硬體編碼不可用，改用 CPU")

            # 讀取字幕
            self.log.emit("讀取字幕檔...")
            cues = fvs.read_srt(self.subs)
            self.log.emit(f"共讀取 {len(cues)} 條字幕")

            # 檢查影片長度
            video_duration: Optional[float] = None
            if self.check_duration:
                self.log.emit("檢查影片長度...")
                video_duration = fvs.probe_duration(self.video, ffprobe_cmd)
                self.log.emit(f"影片長度: {video_duration:.2f} 秒")

                for rng in parsed_ranges:
                    if rng.end > video_duration:
                        raise fvs.UserError(
                            f"區間超出影片長度（影片約 {video_duration:.2f} 秒）: {rng.label}"
                        )

            # 檢查標題重複
            seen_titles = set()
            for rng in parsed_ranges:
                if rng.safe_title:
                    if rng.safe_title in seen_titles:
                        raise fvs.UserError(f"標題重複：{rng.title}")
                    seen_titles.add(rng.safe_title)

            # 處理每個區間
            total = len(parsed_ranges)
            for idx, rng in enumerate(parsed_ranges, start=1):
                if self._cancelled:
                    self.log.emit("已取消")
                    return

                # 構建檔名：優先使用標題，否則用序號
                if rng.safe_title:
                    base = rng.safe_title
                elif self.append_time:
                    # 將時間轉為檔名安全格式
                    time_parts = rng.label.split("->")
                    start_str = time_parts[0].strip().replace(":", "-").replace(".", "-")
                    end_str = time_parts[1].strip().replace(":", "-").replace(".", "-") if len(time_parts) > 1 else ""
                    base = f"clip_{idx:03d}__{start_str}__{end_str}"
                else:
                    base = f"clip_{idx:03d}"

                video_out = self.outdir / f"{base}.mp4"
                subs_out = self.outdir / f"{base}.srt"

                self.progress.emit(idx, total, f"處理區間 {idx}/{total}: {rng.label}")
                self.log.emit(f"[{idx}/{total}] {rng.label} -> {video_out.name}")

                # 若輸出檔已存在，先刪除
                if video_out.exists():
                    video_out.unlink()

                # 裁切影片
                use_precise = (
                    self.precise_flags[idx - 1]
                    if idx - 1 < len(self.precise_flags)
                    else self.ranges[idx - 1].get("precise", False)
                )
                if use_precise and self.verbose:
                    mode = f"硬體加速({self._hwaccel_config.name})" if (self.use_hwaccel and self._hwaccel_config) else "CPU"
                    self.log.emit(f"  使用精準輸出（重編碼，{mode}）")
                if use_precise:
                    fvs.run_ffmpeg_precise(
                        self.video,
                        rng,
                        video_out,
                        self.verbose,
                        ffmpeg_cmd,
                        hwaccel_config=self._hwaccel_config if self.use_hwaccel else None,
                    )
                else:
                    fvs.run_ffmpeg(self.video, rng, video_out, self.verbose, ffmpeg_cmd)

                # 裁切字幕
                override_text = self.subs_overrides[idx - 1] if idx - 1 < len(self.subs_overrides) else None
                if override_text:
                    subs_out.write_text(override_text.strip() + "\n", encoding="utf-8")
                else:
                    sliced_cues = fvs.slice_cues(cues, rng)
                    fvs.write_srt(subs_out, sliced_cues)

                # 標記已調整（僅用於 log/後續擴充）
                adjusted = self.adjusted_flags[idx - 1] if idx - 1 < len(self.adjusted_flags) else False

                output_files.append(str(video_out))
                output_files.append(str(subs_out))

                suffix = "（已調整）" if adjusted or override_text else ""
                self.log.emit(f"  ✓ 已產生 {video_out.name}, {subs_out.name} {suffix}")

            self.log.emit(f"\n完成！共處理 {total} 個區間")
            self.finished_ok.emit(output_files)

        except fvs.UserError as exc:
            self.log.emit(f"[ERR] {exc}")
            self.finished_error.emit(str(exc))
        except Exception as exc:
            self.log.emit(f"[ERR] 非預期錯誤: {exc}")
            self.finished_error.emit(f"非預期錯誤: {exc}")
