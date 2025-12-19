#!/usr/bin/env python3
"""
PyQt 測試介面：包裝 fast_video_slice 核心邏輯，便於手動輸入與跑 ffmpeg。

需求：已安裝 PyQt5、系統 ffmpeg/ffprobe 可用。
"""

import sys
from pathlib import Path
from typing import List

from PyQt5 import QtCore, QtWidgets  # type: ignore

import fast_video_slice as fvs


class Worker(QtCore.QThread):
    finished = QtCore.pyqtSignal(str)
    failed = QtCore.pyqtSignal(str)

    def __init__(
        self,
        video: Path,
        subs: Path,
        ranges: List[str],
        outdir: Path,
        check_duration: bool,
        verbose: bool,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.video = video
        self.subs = subs
        self.ranges = ranges
        self.outdir = outdir
        self.check_duration = check_duration
        self.verbose = verbose

    def run(self) -> None:
        try:
            fvs.check_files(self.video, self.subs)
            parsed_ranges = [fvs.parse_range(r) for r in self.ranges]
            fvs.ensure_outdir(self.outdir)
            fvs.ensure_ffmpeg_exists()
            cues = fvs.read_srt(self.subs)
            video_duration = (
                fvs.probe_duration(self.video) if self.check_duration else None
            )
            if video_duration is not None:
                for rng in parsed_ranges:
                    if rng.end > video_duration:
                        raise fvs.UserError(
                            f"區間超出影片長度（影片約 {video_duration:.2f} 秒）: {rng.label}"
                        )
            for idx, rng in enumerate(parsed_ranges, start=1):
                base = f"clip_{idx:03d}"
                video_out = self.outdir / f"{base}.mp4"
                subs_out = self.outdir / f"{base}.srt"
                if self.verbose:
                    print(f"[處理] {rng.label} -> {video_out.name}")
                fvs.run_ffmpeg(self.video, rng, video_out, self.verbose)
                sliced_cues = fvs.slice_cues(cues, rng)
                fvs.write_srt(subs_out, sliced_cues)
            self.finished.emit("完成")
        except fvs.UserError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # pragma: no cover - GUI safety net
            self.failed.emit(f"非預期錯誤: {exc}")


class MainWindow(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FastVideoSlice GUI 測試版")
        self.resize(640, 560)
        self.worker: Worker | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)

        self.video_edit = self._add_path_row(layout, "影片檔", True)
        self.subs_edit = self._add_path_row(layout, "字幕檔 (.srt)", True)
        self.outdir_edit = self._add_path_row(layout, "輸出資料夾", False, default="clips")

        layout.addWidget(QtWidgets.QLabel("時間區間（每行一段，格式 HH:MM:SS -> HH:MM:SS）"))
        self.range_edit = QtWidgets.QPlainTextEdit()
        self.range_edit.setPlaceholderText("例如：\n00:01:10 -> 00:01:45\n00:05:00->00:05:15")
        self.range_edit.setMinimumHeight(100)
        layout.addWidget(self.range_edit)

        opts_layout = QtWidgets.QHBoxLayout()
        self.check_duration_cb = QtWidgets.QCheckBox("檢查影片長度")
        self.check_duration_cb.setChecked(True)
        self.verbose_cb = QtWidgets.QCheckBox("Verbose")
        opts_layout.addWidget(self.check_duration_cb)
        opts_layout.addWidget(self.verbose_cb)
        opts_layout.addStretch()
        layout.addLayout(opts_layout)

        self.run_btn = QtWidgets.QPushButton("開始裁切")
        self.run_btn.clicked.connect(self.on_run)
        layout.addWidget(self.run_btn)

        layout.addWidget(QtWidgets.QLabel("Log"))
        self.log_box = QtWidgets.QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMinimumHeight(200)
        layout.addWidget(self.log_box)

    def _add_path_row(
        self, parent: QtWidgets.QVBoxLayout, label: str, is_file: bool, default: str | None = None
    ) -> QtWidgets.QLineEdit:
        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel(label))
        edit = QtWidgets.QLineEdit()
        if default:
            edit.setText(default)
        browse_btn = QtWidgets.QPushButton("瀏覽")
        browse_btn.clicked.connect(lambda _, e=edit, f=is_file: self._browse(e, f))
        row.addWidget(edit, 1)
        row.addWidget(browse_btn)
        parent.addLayout(row)
        return edit

    def _browse(self, target: QtWidgets.QLineEdit, is_file: bool) -> None:
        if is_file:
            path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "選擇檔案")
        else:
            path = QtWidgets.QFileDialog.getExistingDirectory(self, "選擇資料夾")
        if path:
            target.setText(path)

    def on_run(self) -> None:
        video = self.video_edit.text().strip()
        subs = self.subs_edit.text().strip()
        outdir = self.outdir_edit.text().strip() or "clips"
        ranges_text = [line.strip() for line in self.range_edit.toPlainText().splitlines() if line.strip()]
        if not video or not subs or not ranges_text:
            QtWidgets.QMessageBox.warning(self, "缺少欄位", "請填寫影片、字幕與至少一個時間區間。")
            return
        self.run_btn.setEnabled(False)
        self.log_box.appendPlainText("開始處理...")
        self.worker = Worker(
            video=Path(video),
            subs=Path(subs),
            ranges=ranges_text,
            outdir=Path(outdir),
            check_duration=self.check_duration_cb.isChecked(),
            verbose=self.verbose_cb.isChecked(),
        )
        self.worker.finished.connect(self.on_finished)
        self.worker.failed.connect(self.on_failed)
        self.worker.start()

    def on_finished(self, msg: str) -> None:
        self.log_box.appendPlainText(msg)
        QtWidgets.QMessageBox.information(self, "完成", msg)
        self.run_btn.setEnabled(True)
        self.worker = None

    def on_failed(self, msg: str) -> None:
        self.log_box.appendPlainText(f"[ERR] {msg}")
        QtWidgets.QMessageBox.critical(self, "錯誤", msg)
        self.run_btn.setEnabled(True)
        self.worker = None


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
