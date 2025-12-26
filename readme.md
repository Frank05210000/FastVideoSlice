# FastVideoSlice

影片/字幕多段切片工具（CLI + GUI）。支援標題檔名、影格時間輸入、精準重編碼模式、硬體編碼加速、預覽微調（可編輯單段字幕）。

## 目錄
- [快速開始](#快速開始)
- [安裝 ffmpeg/ffprobe](#安裝-ffmpegffprobe)
- [GUI 快速開始（零基礎）](#gui-快速開始零基礎)
- [功能亮點](#功能亮點)
- [路徑與設定](#路徑與設定)
- [精準-vs-快速](#精準-vs-快速)
- [解說文件](#解說文件)
- [原始規格（保留）](#原始規格保留)

## 快速開始
- 需求：Python 3.8+，`ffmpeg`/`ffprobe` 在 PATH；GUI 需 PyQt5（`pip install -r requirements.txt`）
- CLI：`python3 fast_video_slice.py --video in.mp4 --subs in.srt --range "00:01:10.05 -> 00:01:45.20" --outdir clips`
- GUI：`python3 -m gui`

## GUI 快速開始
給沒有開發背景的使用者，一步步把 GUI 跑起來。

1) 安裝 Python（若已安裝，可跳過） 
   - 下載並安裝：<https://www.python.org/downloads/>（安裝時勾選「Add Python to PATH」/「Add to environment variables」）
2) 安裝 ffmpeg/ffprobe（若已安裝，可跳過）  
   - macOS：用 Spotlight 搜尋「Terminal」，打開後執行 `brew install ffmpeg`（先安裝 Homebrew：<https://brew.sh/>）  
   - Windows：用「開始」搜尋「PowerShell」，右鍵「以系統管理員身分執行」，輸入 `choco install ffmpeg`（若未安裝 Chocolatey：<https://chocolatey.org/install>），或改用 Scoop：`scoop install ffmpeg`  
   - 確認：在 Terminal/PowerShell 輸入 `ffmpeg -version`、`ffprobe -version`，能顯示版本即完成。
3) 下載專案程式碼（若已下載，可跳過） 
   - 點擊 GitHub 的「Code」→「Download ZIP」，解壓後得到資料夾 `FastVideoSlice`。
4) 建立與啟用虛擬環境  
   - 打開 Terminal/PowerShell，先切換到專案資料夾（例如 `cd 路徑/FastVideoSlice`）。  
   - 建立環境：`python -m venv .venv`  
   - 啟用環境：  
     - macOS/Linux：`source .venv/bin/activate`  
     - Windows：`.venv\Scripts\activate`
5) 安裝依賴  
   ```bash
   pip install -r requirements.txt
   ```
6) 啟動 GUI  
   ```bash
   python -m gui
   ```  
   出現視窗後，選影片/字幕、填區間即可使用。
7) 結束後關閉視窗，若要停用虛擬環境，在 Terminal/PowerShell 輸入 `deactivate`。

## 安裝 ffmpeg/ffprobe
- Python 下載：<https://www.python.org/downloads/>
- macOS（Homebrew）：
  - 安裝 Homebrew：<https://brew.sh/>
  - `brew install ffmpeg`
- Windows：
  - 若已裝 Chocolatey：以系統管理員 PowerShell 執行 `choco install ffmpeg`
  - 或 Scoop：`scoop install ffmpeg`
  - 或下載官方 build（含 ffprobe）：<https://www.gyan.dev/ffmpeg/builds/>，解壓後將 `bin` 路徑加入環境變數 PATH
- Linux（Debian/Ubuntu）：`sudo apt-get install ffmpeg`
- 確認：`ffmpeg -version` 與 `ffprobe -version` 需可在終端執行

## 功能亮點
- 多段區間 `HH:MM:SS(.ff)`（.ff 以 30fps 解析），可加標題作為檔名
- 預設快速裁切 `-c copy`，無損但受關鍵影格影響
- 精準輸出（重編碼），可 per-clip 勾選；可選硬體編碼 (VideoToolbox, Apple Silicon)
- 預覽：可微調時間/字幕、切換精準/硬體加速（開啟精準時才會做 360p 快速重編碼並保留低碼率音訊），可取消，影片下方顯示當前字幕行
- 字幕切片：僅保留交集、時間重設為 00:00:00、序號重排；可針對單段覆寫字幕文本

## 路徑與設定
- 設定檔：`~/.fastvideoslice_settings.json`（GUI 路徑、區間、勾選狀態）
- 預覽暫存：系統 temp/`fastvideoslice_preview`
- 輸出預設：`clips/clip_001.mp4` + `.srt`（或標題檔名）

## 精準-vs-快速
- 快速（預設）：`-c copy`，快且無損，但微調可能被關鍵影格吸附
- 精準：重編碼，時間貼合，速度慢；可勾硬體編碼加速
- 預覽在精準模式下用 360p、低碼率音訊快速轉碼，加速回饋；未開精準時用 `-c copy` 預覽；正式輸出依勾選決定 copy 或重編碼

## 解說文件
- [`docs/setup.md`](docs/setup.md) 環境安裝
- [`docs/cli.md`](docs/cli.md) CLI 用法
- [`docs/gui.md`](docs/gui.md) GUI 流程與選項
- [`docs/precision.md`](docs/precision.md) 精準/硬體/預覽說明
- [`docs/changelog.md`](docs/changelog.md) 變更摘要；細節見 `UPDATE_LOG.md`
- [`docs/README.md`](docs/README.md) 文件導覽

## 原始規格
影片剪輯工具規格書 v1.0

【維護狀態】目前僅維護 CLI / GUI，`web/` 目錄暫不更新（可忽略）。

1. 目的與範圍

本工具用於：輸入一部影片與其字幕檔（SRT），由使用者指定一段或多段時間區間後，自動輸出對應的影片片段，並產出與片段同步的外掛字幕檔（.srt）。
本版本不包含字幕燒錄（burn-in）、不包含多段合併成單支影片。

⸻

2. 使用情境
	•	使用者想從一部長影片中擷取多段精華片段
	•	同時需要保留字幕，且字幕時間軸需從片段起點重新計時

⸻

3. 功能需求

3.1 輸入檔案
	1.	影片檔（必填）
	•	支援常見格式：.mp4, .mkv, .mov 等（依 ffmpeg 支援為準）
	2.	字幕檔（必填）
	•	格式：.srt
	•	編碼建議：UTF-8（若非 UTF-8，需在使用說明提醒使用者先轉檔）

3.2 時間區間輸入（裁切範圍）
	•	使用者可輸入一段或多段時間區間
	•	每段區間格式：
	•	HH:MM:SS -> HH:MM:SS
	•	可加標題：影片標題,HH:MM:SS -> HH:MM:SS（標題將用於輸出檔名，需檢查重名）
	•	例：00:01:10 -> 00:01:45
	•	一次輸入多段時，區間順序即為輸出序號順序

3.3 影片裁切（核心）
	•	每個時間區間輸出一支影片片段
	•	預設採快速裁切（copy stream）
	•	目標：速度快、畫質不變
	•	注意：因為關鍵影格限制，片段起訖時間可能存在極小偏差（在規格的限制與注意事項中說明）

3.4 字幕裁切與同步（核心）
	•	每個時間區間輸出一份字幕檔（.srt）
	•	字幕處理規則：
	1.	只保留與區間有交集的字幕段落
	2.	若字幕段落部分落在區間外，需將字幕時間裁切到區間內
	3.	產出字幕時間需以片段起點為 00:00:00 重新計時（時間軸平移）
	4.	字幕序號需重新從 1 開始連續編號
	•	字幕內容（文字）保持原樣，不做改寫、不做斷行重排

3.5 多段輸出策略
	•	多段輸入 → 多支輸出
	•	每段產出：
	•	預設：clip_XXX.mp4 / clip_XXX.srt
	•	若提供標題，檔名使用標題（經檔名安全清理），需避免重名

⸻

4. 非功能需求

4.1 效能
	•	以快速裁切為預設，單段輸出時間以「接近複製檔案速度」為目標（視硬碟與影片大小而定）

4.2 相容性
	•	需依賴系統已安裝 ffmpeg（或可由工具提示使用者安裝）
	•	作業系統：macOS / Windows / Linux（以能執行 ffmpeg 為前提）

4.3 可用性
	•	提供清楚錯誤訊息，讓使用者知道是哪一個輸入錯（影片檔不存在、字幕檔不存在、時間格式錯誤、區間不合法等）
	•	輸出檔名規則清楚且不覆蓋原始檔

⸻

5. 輸入驗證規格

5.1 檔案驗證
	•	影片檔必須存在且可讀取
	•	字幕檔必須存在且可讀取
	•	若字幕檔非 SRT 格式：直接拒絕或提示「僅支援 .srt」

5.2 時間格式驗證
	•	僅接受 HH:MM:SS（兩位數時分秒）
	•	區間必須符合：start < end
	•	區間不可為空
-（選配）若可取得影片總長度：區間不得超出影片長度；否則提示錯誤

5.3 多段區間規則（本版本不強制，但需定義行為）
	•	允許重疊區間（視為獨立輸出）
	•	允許亂序區間（依輸入順序輸出）
	•	允許相同區間重複輸入（依輸入順序輸出）

⸻

6. 輸出規格

6.1 輸出資料夾
	•	使用者可指定 outdir
	•	若不存在，工具需自動建立

6.2 檔名規則
	•	每段輸出一組檔案：
	•	clip_001_... .mp4
	•	clip_001_... .srt
	•	檔名至少包含：序號（001/002/003…）
-（建議）可額外包含起訖時間或秒數，利於辨識（非必要但推薦）

6.3 輸出內容
	1.	影片片段
	•	保留原影片的音訊/影像串流（快速裁切 copy）
	2.	字幕片段
	•	只含該片段字幕，且時間軸從 00:00:00 起算

⸻

7. 錯誤處理與提示訊息

需至少涵蓋以下錯誤類型並提供可理解的訊息：
	•	找不到影片檔/字幕檔
	•	字幕檔格式不支援
	•	時間格式錯誤（非 HH:MM:SS）
	•	區間不合法（start >= end）
	•	ffmpeg 執行失敗（需回傳關鍵錯誤資訊）
	•	輸出資料夾無法建立或無寫入權限

⸻

8. 限制與注意事項（需寫在 README / 使用說明）
	•	本版本採用 快速裁切（-c copy），可能因關鍵影格造成：
	•	起始畫面可能略早或略晚於指定秒數
	•	字幕裁切是「按時間嚴格裁切」，若影片畫面有偏差，可能產生 0.x 秒左右的視覺落差
（此為 copy stream 的正常現象）
	•	僅支援 SRT 字幕（其他格式需先轉檔）
	•	不提供字幕燒錄、不提供多段合併

⸻

9. 驗收標準（測試案例）
	1.	單段裁切
	•	輸入 00:00:05 -> 00:00:10，輸出影片約 5 秒，字幕時間從 00:00:00 開始
	2.	多段裁切
	•	輸出兩組 mp4+srt，序號對應正確
	3.	字幕交集裁切
	•	有字幕跨越區間邊界時，字幕時間被裁掉並重置
	4.	錯誤輸入
	•	00:10:00 -> 00:09:00 必須報錯
	•	影片/字幕路徑錯誤必須報錯


打包指令：
MODE=onefile pyinstaller gui/__main__.py --noconsole --onefile --name FastVideoSliceGUI \
  --icon gui/icon.icns --hidden-import sip --add-binary "bin/ffmpeg:bin" --add-binary "bin/ffprobe:bin"
