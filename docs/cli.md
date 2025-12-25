# CLI 使用筆記

## 基本用法
```bash
python3 fast_video_slice.py \
  --video input.mp4 \
  --subs input.srt \
  --range "00:01:10.05 -> 00:01:45.20" \
  --range "標題二,00:05:00 -> 00:05:30.10" \
  --outdir clips \
  --check-duration \
  --verbose
```

## 參數摘要
- `--video <path>`：來源影片
- `--subs <path>`：字幕 `.srt`
- `--range "HH:MM:SS(.ff) -> HH:MM:SS(.ff)"`：可多段；`.ff` 視為影格（預設 30fps，0–29）
  - 可含標題：`標題,00:00:05.00 -> 00:00:10.15`，標題會用於檔名，重複會報錯
- `--outdir <path>`：輸出目錄，預設 `clips`
- `--check-duration`：先用 ffprobe 確認區間不超出影片長度
- `--verbose`：印出處理細節與 ffmpeg 命令

## 輸出
- 未提供標題：`clip_001.mp4` / `clip_001.srt`…
- 提供標題：清理後的標題作為檔名
- 正式輸出預設採 `-ss/-to -c copy`（快速、無損，受關鍵影格影響）

## 注意
- `.ff` 以 30fps 解析，如影片 fps 不同，極細微位置可能略有差異；需要絕對精準請在 GUI 開啟「精準輸出」使用重編碼。
- 只支援 `.srt`；非 UTF-8 需先轉碼。
