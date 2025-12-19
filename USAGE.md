# FastVideoSlice CLI 使用說明

## 前置需求
- Python 3.8+
- ffmpeg / ffprobe 已安裝且在 PATH
- 字幕檔需為 UTF-8 編碼的 `.srt`（會自動去除 BOM）

## 安裝/取得
此工具僅依賴標準函式庫，放在同目錄即可直接執行：
```bash
python3 fast_video_slice.py --help
```

## 參數
- `--video <path>`：來源影片檔（必填）
- `--subs <path>`：來源字幕檔 `.srt`（必填）
- `--range "HH:MM:SS -> HH:MM:SS"`：時間區間，至少一個，可多次提供
- `--outdir <path>`：輸出資料夾，預設 `clips`（不存在會自動建立）
- `--check-duration`：先用 ffprobe 讀影片長度，若區間超界則報錯
- `--verbose`：顯示處理細節與 ffmpeg 命令

## 使用範例
```bash
python3 fast_video_slice.py \
  --video input.mp4 \
  --subs input.srt \
  --range "00:01:10 -> 00:01:45" \
  --range "00:05:00->00:05:15" \
  --outdir clips \
  --check-duration \
  --verbose
```

## 輸出
- 每個區間輸出：
  - `clip_001.mp4`（ffmpeg `-ss/-to -c copy` 快速裁切）
  - `clip_001.srt`（字幕時間裁切到區間、時間軸從 00:00:00、序號重排）
- 檔名序號依輸入區間順序。

## 驗證與錯誤訊息
- 檢查：檔案存在/型別、字幕副檔名、時間格式 `HH:MM:SS`、`start < end`、（選）區間不超出影片長度。
- 常見錯誤：
  - `[ERR] 找不到影片檔: ...`
  - `[ERR] 字幕檔格式不支援（僅接受 .srt）`
  - `[ERR] 時間格式錯誤，需為 HH:MM:SS`
  - `[ERR] 區間不合法，需滿足 start < end`
  - `[ERR] 區間超出影片長度（影片約 X 秒）: ...`（啟用 `--check-duration` 時）
  - `[ERR] ffmpeg 執行失敗: ...`

## 限制與注意事項
- 使用 `-c copy`，可能因關鍵影格導致起訖時間有極小偏差；字幕嚴格按時間裁切，可能與畫面有 0.x 秒落差。
- 不支援字幕燒錄、不支援多段合併；僅輸出對應區段的 mp4 + srt。
