# 環境與安裝

## 必要條件
- Python 3.8+
- `ffmpeg` / `ffprobe` 已安裝且在 PATH（macOS 可用 Homebrew，Windows 可用 choco/scoop/官方包）
- 若使用 GUI：需要 PyQt5

## 安裝步驟
```bash
git clone <repo>
cd FastVideoSlice
python3 -m venv .venv && source .venv/bin/activate  # 選用
pip install -r requirements.txt  # 安裝 PyQt5；CLI 無額外依賴
```

## 執行
- CLI：`python3 fast_video_slice.py --help`
- GUI：`python3 -m gui`

## 檔案需求
- 影片：ffmpeg 支援的格式（mp4/mkv/mov…）
- 字幕：`.srt`（UTF-8）

## 其他
- 設定檔：`~/.fastvideoslice_settings.json`
- 預覽暫存：系統 temp 目錄 `fastvideoslice_preview`（會在關閉預覽時清理）
