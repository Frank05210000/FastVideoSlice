# FastVideoSlice CLI 使用說明

> 維護狀態：目前僅維護 CLI / GUI，`web/` 目錄暫不更新（可忽略）。

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
- `--range "HH:MM:SS(.ff) -> HH:MM:SS(.ff)"`：時間區間，至少一個，可多次提供（ff 視為影格，預設 30fps，範圍 00-29）。
  - 可加上自訂標題：`"影片標題,HH:MM:SS(.ff) -> HH:MM:SS(.ff)"`，輸出檔名將使用標題。
  - 標題經過檔名安全清理（非法字元改為 `_`，空白改 `_`），若重複或清理後重複會報錯。
- `--outdir <path>`：輸出資料夾，預設 `clips`（不存在會自動建立）
- `--check-duration`：先用 ffprobe 讀影片長度，若區間超界則報錯
- `--verbose`：顯示處理細節與 ffmpeg 命令

## 使用範例
```bash
python3 fast_video_slice.py \
  --video input.mp4 \
  --subs input.srt \
  --range "精華一,00:01:10 -> 00:01:45" \
  --range "精華二,00:05:00->00:05:15" \
  --outdir clips \
  --check-duration \
  --verbose
```

## 輸出
- 每個區間輸出：
  - 若有標題，使用清理後的標題作為檔名，例如 `精華一.mp4`、`精華一.srt`
  - 若無標題，使用序號 `clip_001.mp4`、`clip_001.srt`
  - ffmpeg `-ss/-to -c copy` 快速裁切；字幕時間裁切到區間、時間軸從 00:00:00、序號重排

## 驗證與錯誤訊息
- 檢查：檔案存在/型別、字幕副檔名、時間格式 `HH:MM:SS(.ff)`、`start < end`、（選）區間不超出影片長度。ff 視為影格，預設 30fps。
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
