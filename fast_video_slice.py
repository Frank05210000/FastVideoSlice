#!/usr/bin/env python3
"""
FastVideoSlice CLI: cut video segments with matching SRT slices (copy stream).

Usage example:
  python fast_video_slice.py --video input.mp4 --subs input.srt \
    --range "00:01:10 -> 00:01:45" --range "00:05:00->00:05:15" \
    --outdir clips --check-duration --verbose
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence


@dataclass
class TimeRange:
    start: float  # seconds
    end: float  # seconds
    label: str  # original string for logging
    title: str | None = None  # optional user-provided title
    safe_title: str | None = None  # sanitized title for file naming


@dataclass
class SRTCue:
    start: float  # seconds
    end: float  # seconds
    lines: List[str]


class UserError(Exception):
    """User-facing errors with friendly messages."""


def parse_hms(text: str) -> float:
    match = re.fullmatch(r"(\d{2}):(\d{2}):(\d{2})", text.strip())
    if not match:
        raise UserError("時間格式錯誤，需為 HH:MM:SS")
    h, m, s = map(int, match.groups())
    if not (0 <= m < 60 and 0 <= s < 60):
        raise UserError("時間格式錯誤，分秒需介於 00-59")
    return h * 3600 + m * 60 + s


def parse_range(text: str) -> TimeRange:
    title_part: str | None = None
    raw = text.strip()
    if "," in raw:
        title_part, raw = raw.split(",", 1)
        title_part = title_part.strip()
        if not title_part:
            raise UserError("標題不可為空，格式：標題,HH:MM:SS -> HH:MM:SS")
    parts = re.split(r"\s*->\s*", raw)
    if len(parts) != 2:
        raise UserError("區間格式錯誤，需為 HH:MM:SS -> HH:MM:SS")
    start = parse_hms(parts[0])
    end = parse_hms(parts[1])
    if start >= end:
        raise UserError("區間不合法，需滿足 start < end")
    safe_title = sanitize_title(title_part) if title_part else None
    return TimeRange(start=start, end=end, label=text, title=title_part, safe_title=safe_title)


def check_files(video_path: Path, subs_path: Path) -> None:
    if not video_path.exists():
        raise UserError(f"找不到影片檔: {video_path}")
    if not video_path.is_file():
        raise UserError(f"影片路徑不是檔案: {video_path}")
    if not subs_path.exists():
        raise UserError(f"找不到字幕檔: {subs_path}")
    if not subs_path.is_file():
        raise UserError(f"字幕路徑不是檔案: {subs_path}")
    if subs_path.suffix.lower() != ".srt":
        raise UserError("字幕檔格式不支援（僅接受 .srt）")


def read_srt(path: Path) -> List[SRTCue]:
    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise UserError("字幕檔不是 UTF-8，請先轉檔再試")
    # 移除 BOM 以避免首行 cue 序號被污染
    if raw.startswith("\ufeff"):
        raw = raw.lstrip("\ufeff")
    blocks = re.split(r"(?:\r?\n){2,}", raw.strip())
    cues: List[SRTCue] = []
    for block in blocks:
        lines = [line.lstrip("\ufeff") for line in block.splitlines()]
        if len(lines) < 2:
            continue
        times_line = lines[1] if lines[0].strip().isdigit() else lines[0]
        text_lines = lines[2:] if lines[0].strip().isdigit() else lines[1:]
        start, end = parse_srt_time_range(times_line)
        cues.append(SRTCue(start=start, end=end, lines=text_lines))
    return cues


def parse_srt_time(time_str: str) -> float:
    match = re.fullmatch(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})", time_str.strip())
    if not match:
        raise UserError(f"字幕時間格式錯誤: {time_str}")
    h, m, s, ms = map(int, match.groups())
    if not (0 <= m < 60 and 0 <= s < 60 and 0 <= ms < 1000):
        raise UserError(f"字幕時間格式錯誤: {time_str}")
    return h * 3600 + m * 60 + s + ms / 1000.0


def parse_srt_time_range(line: str) -> tuple[float, float]:
    match = re.fullmatch(r"(.*?)\s*-->\s*(.*)", line.strip())
    if not match:
        raise UserError(f"字幕時間區間格式錯誤: {line}")
    start = parse_srt_time(match.group(1))
    end = parse_srt_time(match.group(2))
    return start, end


def _split_time_ms(seconds: float) -> tuple[int, int, int, int]:
    total_ms = int(round(seconds * 1000))
    total_seconds, ms = divmod(total_ms, 1000)
    s = total_seconds % 60
    total_minutes = total_seconds // 60
    m = total_minutes % 60
    h = total_minutes // 60
    return h, m, s, ms


def sanitize_title(title: str | None) -> str | None:
    if title is None:
        return None
    # 允許中文字、英數、底線、連字號、小數點與空白（空白轉底線）
    cleaned = re.sub(r"[^\w\-. ]", "_", title.strip(), flags=re.UNICODE)
    cleaned = cleaned.replace(" ", "_")
    cleaned = re.sub(r"_+", "_", cleaned).strip("._")
    if not cleaned:
        raise UserError(f"標題不合法：{title}")
    return cleaned


def format_srt_time(seconds: float) -> str:
    h, m, s, ms = _split_time_ms(seconds)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def slice_cues(cues: Sequence[SRTCue], rng: TimeRange) -> List[SRTCue]:
    sliced: List[SRTCue] = []
    for cue in cues:
        if cue.end <= rng.start or cue.start >= rng.end:
            continue
        new_start = max(cue.start, rng.start)
        new_end = min(cue.end, rng.end)
        shifted_start = new_start - rng.start
        shifted_end = new_end - rng.start
        sliced.append(SRTCue(start=shifted_start, end=shifted_end, lines=cue.lines))
    return sliced


def format_srt(cues: Sequence[SRTCue]) -> str:
    lines: List[str] = []
    for idx, cue in enumerate(cues, start=1):
        lines.append(str(idx))
        lines.append(f"{format_srt_time(cue.start)} --> {format_srt_time(cue.end)}")
        lines.extend(cue.lines)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def ensure_outdir(outdir: Path) -> None:
    try:
        outdir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise UserError(f"輸出資料夾建立失敗: {exc}")


def find_ff_binary(name: str) -> str | None:
    """依序嘗試：環境變數、_MEIPASS/bin、專案 bin、工作目錄 bin、系統 PATH。"""
    env_key = f"FVS_{name.upper()}"
    env_path = os.environ.get(env_key)
    if env_path and Path(env_path).exists():
        return env_path

    candidates: List[Path] = []
    if hasattr(sys, "_MEIPASS"):
        candidates.append(Path(sys._MEIPASS) / "bin" / name)
    candidates.append(Path(__file__).parent / "bin" / name)
    candidates.append(Path.cwd() / "bin" / name)
    which_path = shutil.which(name)
    if which_path:
        candidates.append(Path(which_path))

    for cand in candidates:
        if cand.exists():
            return str(cand)
    return None


def clean_subprocess_env() -> dict[str, str]:
    """避免 PyInstaller 注入的 DYLD/LD 路徑干擾 ffmpeg/ffprobe。"""
    env = os.environ.copy()
    for key in (
        "LD_LIBRARY_PATH",
        "DYLD_LIBRARY_PATH",
        "DYLD_FALLBACK_LIBRARY_PATH",
        "DYLD_FRAMEWORK_PATH",
        "DYLD_VERSIONED_LIBRARY_PATH",
        "PYTHONHOME",
        "PYTHONPATH",
    ):
        env.pop(key, None)
    return env


def ensure_unique_titles(ranges: Sequence[TimeRange]) -> None:
    seen: dict[str, str] = {}
    for rng in ranges:
        if rng.safe_title:
            if rng.safe_title in seen:
                raise UserError(f"輸入標題重複（或清理後重複）: {rng.title}")
            seen[rng.safe_title] = rng.title or rng.safe_title


def ensure_ffmpeg_exists() -> tuple[str, str]:
    ffmpeg_path = find_ff_binary("ffmpeg")
    ffprobe_path = find_ff_binary("ffprobe")
    if not ffmpeg_path:
        raise UserError("找不到 ffmpeg，請先安裝或在 bin/ 內附帶 ffmpeg")
    if not ffprobe_path:
        raise UserError("找不到 ffprobe，請先安裝或在 bin/ 內附帶 ffprobe")
    return ffmpeg_path, ffprobe_path


def probe_duration(video_path: Path, ffprobe_cmd: str) -> float:
    cmd = [
        ffprobe_cmd,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True, env=clean_subprocess_env()
        )
    except subprocess.CalledProcessError as exc:
        raise UserError(f"ffprobe 取得影片長度失敗: {exc.stderr.strip()}")
    try:
        return float(result.stdout.strip())
    except ValueError:
        raise UserError("ffprobe 回傳的影片長度無法解析")


def format_ffmpeg_time(seconds: float) -> str:
    h, m, s, ms = _split_time_ms(seconds)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def run_ffmpeg(
    video_path: Path, rng: TimeRange, output_path: Path, verbose: bool, ffmpeg_cmd: str
) -> None:
    if output_path.exists():
        raise UserError(f"輸出檔已存在，避免覆蓋: {output_path}")
    cmd = [
        ffmpeg_cmd,
        "-y",
        "-ss",
        format_ffmpeg_time(rng.start),
        "-to",
        format_ffmpeg_time(rng.end),
        "-i",
        str(video_path),
        "-c",
        "copy",
        str(output_path),
    ]
    if verbose:
        print("[ffmpeg]", " ".join(cmd))
    try:
        subprocess.run(
            cmd,
            check=True,
            capture_output=not verbose,
            text=True,
            env=clean_subprocess_env(),
        )
    except subprocess.CalledProcessError as exc:
        err_msg = exc.stderr.strip() if exc.stderr else str(exc)
        raise UserError(f"ffmpeg 執行失敗: {err_msg}")


def write_srt(output_path: Path, cues: Sequence[SRTCue]) -> None:
    output_path.write_text(format_srt(cues), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="影片與字幕切片工具（快速裁切 copy stream）"
    )
    parser.add_argument("--video", required=True, help="來源影片檔路徑")
    parser.add_argument("--subs", required=True, help="來源字幕檔（.srt）路徑")
    parser.add_argument(
        "--range",
        dest="ranges",
        action="append",
        required=True,
        help='時間區間，格式 "HH:MM:SS -> HH:MM:SS"；可多次提供',
    )
    parser.add_argument("--outdir", default="clips", help="輸出資料夾，預設 clips")
    parser.add_argument(
        "--check-duration",
        action="store_true",
        help="驗證區間不可超出影片長度（需 ffprobe）",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="顯示詳細處理訊息與 ffmpeg 命令",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    video_path = Path(args.video)
    subs_path = Path(args.subs)
    outdir = Path(args.outdir)

    try:
        check_files(video_path, subs_path)
        ranges = [parse_range(r) for r in args.ranges]
        ensure_unique_titles(ranges)
        ensure_outdir(outdir)
        ffmpeg_cmd, ffprobe_cmd = ensure_ffmpeg_exists()
        cues = read_srt(subs_path)
        video_duration = (
            probe_duration(video_path, ffprobe_cmd) if args.check_duration else None
        )
        if video_duration is not None:
            for rng in ranges:
                if rng.end > video_duration:
                    raise UserError(
                        f"區間超出影片長度（影片約 {video_duration:.2f} 秒）: {rng.label}"
                    )
        for idx, rng in enumerate(ranges, start=1):
            base = rng.safe_title if rng.safe_title else f"clip_{idx:03d}"
            video_out = outdir / f"{base}.mp4"
            subs_out = outdir / f"{base}.srt"
            if args.verbose:
                title_info = f"{rng.title or base}"
                print(f"[處理] {title_info}: {rng.label} -> {video_out.name}")
            run_ffmpeg(video_path, rng, video_out, args.verbose, ffmpeg_cmd)
            sliced_cues = slice_cues(cues, rng)
            write_srt(subs_out, sliced_cues)
        if args.verbose:
            print("完成")
        return 0
    except UserError as exc:
        print(f"[ERR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
