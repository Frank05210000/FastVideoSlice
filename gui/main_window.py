"""
FastVideoSlice GUI 主視窗

整合所有元件，提供完整的圖形介面。
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QProgressBar,
    QPlainTextEdit,
    QFileDialog,
    QMessageBox,
    QSplitter,
    QTableWidgetItem,
)
from PyQt5.QtGui import QPalette, QColor

from .constants import (
    APP_NAME,
    APP_VERSION,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    STYLESHEET,
)
from .range_table import RangeTableWidget
from .settings_manager import SettingsManager
from .worker import SliceWorker
from .preview_dialog import PreviewDialog

import fast_video_slice as fvs


class MainWindow(QMainWindow):
    """FastVideoSlice 主視窗"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

        self.settings = SettingsManager()
        self.worker: Optional[SliceWorker] = None
        self.subs_overrides: dict[int, str] = {}

        self._build_ui()
        self._load_settings()
        self._connect_signals()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(12)

        # ---- 檔案選擇區 ----
        file_group = QGroupBox("檔案選擇")
        file_layout = QVBoxLayout(file_group)

        # 影片檔
        video_row = QHBoxLayout()
        video_row.addWidget(QLabel("影片檔："))
        self.video_edit = QLineEdit()
        self.video_edit.setPlaceholderText("選擇來源影片...")
        video_row.addWidget(self.video_edit, 1)
        self.video_browse_btn = QPushButton("瀏覽")
        self.video_browse_btn.setProperty("secondary", True)
        video_row.addWidget(self.video_browse_btn)
        file_layout.addLayout(video_row)

        # 字幕檔
        subs_row = QHBoxLayout()
        subs_row.addWidget(QLabel("字幕檔："))
        self.subs_edit = QLineEdit()
        self.subs_edit.setPlaceholderText("選擇 .srt 字幕檔...")
        subs_row.addWidget(self.subs_edit, 1)
        self.subs_browse_btn = QPushButton("瀏覽")
        self.subs_browse_btn.setProperty("secondary", True)
        subs_row.addWidget(self.subs_browse_btn)
        file_layout.addLayout(subs_row)

        # 輸出資料夾
        outdir_row = QHBoxLayout()
        outdir_row.addWidget(QLabel("輸出資料夾："))
        self.outdir_edit = QLineEdit()
        self.outdir_edit.setPlaceholderText("預設 clips/")
        outdir_row.addWidget(self.outdir_edit, 1)
        self.outdir_browse_btn = QPushButton("瀏覽")
        self.outdir_browse_btn.setProperty("secondary", True)
        outdir_row.addWidget(self.outdir_browse_btn)
        file_layout.addLayout(outdir_row)

        main_layout.addWidget(file_group)

        # ---- 區間管理區 ----
        range_group = QGroupBox("時間區間")
        range_layout = QVBoxLayout(range_group)
        self.range_table = RangeTableWidget()
        range_layout.addWidget(self.range_table)
        main_layout.addWidget(range_group, 1)

        # ---- 設定區 ----
        options_group = QGroupBox("選項")
        options_layout = QHBoxLayout(options_group)

        self.check_duration_cb = QCheckBox("檢查影片長度")
        self.check_duration_cb.setChecked(True)
        self.check_duration_cb.setToolTip("裁切前先確認區間不超出影片長度")
        options_layout.addWidget(self.check_duration_cb)

        self.verbose_cb = QCheckBox("詳細日誌")
        self.verbose_cb.setToolTip("顯示 ffmpeg 命令等詳細資訊")
        options_layout.addWidget(self.verbose_cb)

        self.append_time_cb = QCheckBox("檔名附加時間")
        self.append_time_cb.setToolTip("輸出檔名加入起訖時間，如 clip_001__00-01-10__00-01-45")
        options_layout.addWidget(self.append_time_cb)

        self.hwaccel_cb = QCheckBox("精準輸出使用硬體編碼")
        self.hwaccel_cb.setToolTip("精準輸出/預覽時使用 VideoToolbox（Apple Silicon）加速，降低等待時間")
        options_layout.addWidget(self.hwaccel_cb)

        options_layout.addStretch()
        main_layout.addWidget(options_group)

        # ---- 執行區 ----
        exec_group = QGroupBox("執行")
        exec_layout = QVBoxLayout(exec_group)

        # 進度條
        progress_row = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        progress_row.addWidget(self.progress_bar, 1)
        self.progress_label = QLabel("")
        progress_row.addWidget(self.progress_label)
        exec_layout.addLayout(progress_row)

        # 按鈕
        btn_row = QHBoxLayout()
        self.run_btn = QPushButton("🎬 開始裁切")
        self.run_btn.setMinimumHeight(40)
        btn_row.addWidget(self.run_btn, 1)

        self.open_folder_btn = QPushButton("📂 開啟輸出資料夾")
        self.open_folder_btn.setProperty("secondary", True)
        btn_row.addWidget(self.open_folder_btn)
        exec_layout.addLayout(btn_row)

        main_layout.addWidget(exec_group)

        # ---- Log 區 ----
        log_group = QGroupBox("日誌")
        log_layout = QVBoxLayout(log_group)

        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMinimumHeight(120)
        log_layout.addWidget(self.log_box)

        log_btn_row = QHBoxLayout()
        self.clear_log_btn = QPushButton("清空")
        self.clear_log_btn.setProperty("secondary", True)
        log_btn_row.addWidget(self.clear_log_btn)

        self.save_log_btn = QPushButton("另存日誌")
        self.save_log_btn.setProperty("secondary", True)
        log_btn_row.addWidget(self.save_log_btn)

        log_btn_row.addStretch()
        log_layout.addLayout(log_btn_row)

        main_layout.addWidget(log_group)

    def _connect_signals(self) -> None:
        # 瀏覽按鈕
        self.video_browse_btn.clicked.connect(self._browse_video)
        self.subs_browse_btn.clicked.connect(self._browse_subs)
        self.outdir_browse_btn.clicked.connect(self._browse_outdir)

        # 執行按鈕
        self.run_btn.clicked.connect(self._on_run)
        self.open_folder_btn.clicked.connect(self._open_output_folder)

        # 預覽/微調
        self.range_table.preview_btn.clicked.connect(self._on_preview_range)

        # Log 按鈕
        self.clear_log_btn.clicked.connect(self.log_box.clear)
        self.save_log_btn.clicked.connect(self._save_log)

        # 區間變更後清理不符行數的覆寫字幕（避免 stale）
        self.range_table.ranges_changed.connect(self._prune_sub_overrides)

    def _browse_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "選擇影片檔",
            self.video_edit.text() or str(Path.home()),
            "影片檔 (*.mp4 *.mkv *.avi *.mov *.webm);;所有檔案 (*)",
        )
        if path:
            self.video_edit.setText(path)
            # 自動填入同名字幕檔（如果存在）
            srt_path = Path(path).with_suffix(".srt")
            if srt_path.exists() and not self.subs_edit.text():
                self.subs_edit.setText(str(srt_path))

    def _browse_subs(self) -> None:
        start_dir = self.subs_edit.text() or self.video_edit.text() or str(Path.home())
        path, _ = QFileDialog.getOpenFileName(
            self,
            "選擇字幕檔",
            start_dir,
            "字幕檔 (*.srt);;所有檔案 (*)",
        )
        if path:
            self.subs_edit.setText(path)

    def _browse_outdir(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "選擇輸出資料夾",
            self.outdir_edit.text() or str(Path.cwd()),
        )
        if path:
            self.outdir_edit.setText(path)

    def _on_preview_range(self) -> None:
        row = self.range_table.table.currentRow()
        rng = self.range_table.get_range_at(row)
        if rng is None:
            QMessageBox.information(self, "提示", "請先選擇一個有效的區間")
            return

        video = self.video_edit.text().strip()
        subs = self.subs_edit.text().strip()
        if not video or not subs:
            QMessageBox.warning(self, "缺少欄位", "請先選擇影片與字幕檔再預覽")
            return

        try:
            fvs.check_files(Path(video), Path(subs))
        except fvs.UserError as exc:
            QMessageBox.warning(self, "檔案錯誤", str(exc))
            return

        dialog = PreviewDialog(
            video_path=Path(video),
            subs_path=Path(subs),
            start=rng["start"],
            end=rng["end"],
            title=rng.get("title", ""),
            initial_subs_text=self.subs_overrides.get(row),
            initial_precise=rng.get("precise", False),
            use_hwaccel_default=self.hwaccel_cb.isChecked(),
            parent=self,
        )
        dialog.range_applied.connect(
            lambda start, end, subs_text, precise, r=row: self._apply_preview_range(
                r, start, end, subs_text, precise
            )
        )
        dialog.exec_()

    def _on_run(self) -> None:
        # 驗證輸入
        video = self.video_edit.text().strip()
        subs = self.subs_edit.text().strip()
        outdir = self.outdir_edit.text().strip() or "clips"

        if not video:
            QMessageBox.warning(self, "缺少欄位", "請選擇影片檔")
            self.video_edit.setFocus()
            return

        if not subs:
            QMessageBox.warning(self, "缺少欄位", "請選擇字幕檔")
            self.subs_edit.setFocus()
            return

        ranges = self.range_table.get_ranges()
        if not ranges:
            QMessageBox.warning(self, "缺少欄位", "請至少新增一個時間區間")
            return

        # 驗證區間格式
        is_valid, error_rows = self.range_table.validate()
        if not is_valid:
            self.range_table.highlight_error_rows(error_rows)
            QMessageBox.warning(
                self,
                "格式錯誤",
                f"有 {len(error_rows)} 個區間格式錯誤或不合法，請修正高亮的列。",
            )
            return

        # 儲存設定
        self._save_settings()

        # 禁用按鈕
        self._set_running(True)
        self.progress_bar.setValue(0)
        self.log_box.clear()

        # 準備字幕覆寫（按行號對應）
        subs_overrides = []
        for idx in range(len(ranges)):
            subs_overrides.append(self.subs_overrides.get(idx))

        precise_flags = [r.get("precise", False) for r in ranges]

        # 啟動工作執行緒
        self.worker = SliceWorker(
            video=Path(video),
            subs=Path(subs),
            ranges=ranges,
            outdir=Path(outdir),
            check_duration=self.check_duration_cb.isChecked(),
            verbose=self.verbose_cb.isChecked(),
            append_time=self.append_time_cb.isChecked(),
            subs_overrides=subs_overrides,
            precise_flags=precise_flags,
            use_hwaccel=self.hwaccel_cb.isChecked(),
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.log.connect(self._on_log)
        self.worker.finished_ok.connect(self._on_finished_ok)
        self.worker.finished_error.connect(self._on_finished_error)
        self.worker.start()

    def _set_running(self, running: bool) -> None:
        self.run_btn.setEnabled(not running)
        self.video_browse_btn.setEnabled(not running)
        self.subs_browse_btn.setEnabled(not running)
        self.outdir_browse_btn.setEnabled(not running)

    def _on_progress(self, current: int, total: int, message: str) -> None:
        percent = int(current / total * 100) if total > 0 else 0
        self.progress_bar.setValue(percent)
        self.progress_label.setText(message)

    def _on_log(self, message: str) -> None:
        self.log_box.appendPlainText(message)

    def _on_finished_ok(self, output_files: list) -> None:
        self._set_running(False)
        self.progress_bar.setValue(100)
        self.progress_label.setText("完成！")

        QMessageBox.information(
            self,
            "完成",
            f"成功裁切 {len(output_files) // 2} 個區間！\n\n輸出目錄：{self.outdir_edit.text() or 'clips'}",
        )
        self.worker = None

    def _on_finished_error(self, error: str) -> None:
        self._set_running(False)
        self.progress_label.setText("發生錯誤")

        QMessageBox.critical(self, "錯誤", error)
        self.worker = None

    def _open_output_folder(self) -> None:
        outdir = self.outdir_edit.text().strip() or "clips"
        path = Path(outdir)
        if not path.exists():
            QMessageBox.warning(self, "資料夾不存在", f"找不到資料夾：{outdir}")
            return

        # 跨平台開啟資料夾
        if sys.platform == "darwin":
            subprocess.run(["open", str(path)])
        elif sys.platform == "win32":
            subprocess.run(["explorer", str(path)])
        else:
            subprocess.run(["xdg-open", str(path)])

    def _save_log(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "另存日誌",
            "fastvideoslice_log.txt",
            "文字檔 (*.txt);;所有檔案 (*)",
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self.log_box.toPlainText())
                QMessageBox.information(self, "已儲存", f"日誌已儲存至：{path}")
            except IOError as e:
                QMessageBox.warning(self, "儲存失敗", str(e))

    def _apply_preview_range(self, row: int, start: str, end: str, subs_text: str, precise: bool) -> None:
        """將預覽調整後的時間/字幕/精準設定寫回表格"""
        if row < 0 or row >= self.range_table.table.rowCount():
            return
        table = self.range_table.table
        table.blockSignals(True)
        table.setItem(row, 2, QTableWidgetItem(start))
        table.setItem(row, 3, QTableWidgetItem(end))
        precise_item = QTableWidgetItem("精準輸出")
        precise_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        precise_item.setCheckState(Qt.Checked if precise else Qt.Unchecked)
        table.setItem(row, 5, precise_item)
        # 重置背景色
        table.item(row, 2).setBackground(Qt.white)
        table.item(row, 3).setBackground(Qt.white)
        table.blockSignals(False)
        self.subs_overrides[row] = subs_text
        self.range_table.ranges_changed.emit()

    def _prune_sub_overrides(self) -> None:
        """移除超出表格行數的字幕覆寫"""
        max_row = self.range_table.table.rowCount() - 1
        stale_keys = [k for k in self.subs_overrides if k > max_row]
        for k in stale_keys:
            self.subs_overrides.pop(k, None)

    def _load_settings(self) -> None:
        """從設定檔載入上次的設定"""
        self.video_edit.setText(self.settings.last_video_path)
        self.subs_edit.setText(self.settings.last_subs_path)
        self.outdir_edit.setText(self.settings.last_outdir)
        self.check_duration_cb.setChecked(self.settings.check_duration)
        self.verbose_cb.setChecked(self.settings.verbose)
        self.append_time_cb.setChecked(self.settings.append_time_to_filename)
        self.hwaccel_cb.setChecked(self.settings.precise_use_hwaccel)
        self.range_table.set_ranges(self.settings.last_ranges)

        # 視窗位置
        geom = self.settings.window_geometry
        if geom:
            self.setGeometry(geom.get("x", 100), geom.get("y", 100),
                           geom.get("width", WINDOW_WIDTH), geom.get("height", WINDOW_HEIGHT))

    def _save_settings(self) -> None:
        """儲存目前設定"""
        self.settings.last_video_path = self.video_edit.text()
        self.settings.last_subs_path = self.subs_edit.text()
        self.settings.last_outdir = self.outdir_edit.text()
        self.settings.check_duration = self.check_duration_cb.isChecked()
        self.settings.verbose = self.verbose_cb.isChecked()
        self.settings.append_time_to_filename = self.append_time_cb.isChecked()
        self.settings.precise_use_hwaccel = self.hwaccel_cb.isChecked()
        self.settings.last_ranges = self.range_table.get_ranges()
        self.settings.window_geometry = {
            "x": self.x(),
            "y": self.y(),
            "width": self.width(),
            "height": self.height(),
        }
        self.settings.save()

    def closeEvent(self, event) -> None:
        """關閉視窗時儲存設定"""
        self._save_settings()
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                "確認關閉",
                "正在處理中，確定要關閉嗎？",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.No:
                event.ignore()
                return
            self.worker.cancel()
            self.worker.wait()
        event.accept()


def run_app() -> int:
    """啟動應用程式"""
    import tempfile

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 強制使用淺色系調色盤，避免系統深色主題影響
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#FFFFFF"))
    palette.setColor(QPalette.Base, QColor("#FFFFFF"))
    palette.setColor(QPalette.AlternateBase, QColor("#F8FAFC"))
    palette.setColor(QPalette.Text, QColor("#0F172A"))
    palette.setColor(QPalette.WindowText, QColor("#0F172A"))
    palette.setColor(QPalette.Button, QColor("#F8FAFC"))
    palette.setColor(QPalette.ButtonText, QColor("#0F172A"))
    palette.setColor(QPalette.Highlight, QColor("#2563EB"))
    palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(palette)

    # 啟動時清理殘留的預覽暫存
    try:
        temp_dir = Path(tempfile.gettempdir()) / "fastvideoslice_preview"
        if temp_dir.exists():
            for p in temp_dir.glob("*.mp4"):
                p.unlink()
    except Exception:
        pass  # 清理失敗不影響啟動

    app.setStyleSheet(STYLESHEET)

    window = MainWindow()
    window.show()

    return app.exec_()
