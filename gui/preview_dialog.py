"""
預覽與微調對話框

使用 ffmpeg 先產生暫存預覽檔，再用 QMediaPlayer 播放，
同時顯示該區間的字幕片段，允許使用者用毫秒精度微調時間。
"""

import tempfile
import uuid
from pathlib import Path

from PyQt5.QtCore import Qt, QUrl, pyqtSignal, QProcess
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QPlainTextEdit,
    QMessageBox,
    QSlider,
    QProgressBar,
    QCheckBox,
        QApplication,
    )
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer  # type: ignore
from PyQt5.QtMultimediaWidgets import QVideoWidget  # type: ignore

import fast_video_slice as fvs


class PreviewDialog(QDialog):
    """預覽並微調時間的對話框"""

    range_applied = pyqtSignal(str, str, str, bool)  # start, end, edited_subs, precise

    def __init__(
        self,
        video_path: Path,
        subs_path: Path,
        start: str,
        end: str,
        title: str = "",
        initial_subs_text: str | None = None,
        initial_precise: bool = False,
        use_hwaccel_default: bool = True,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("預覽與微調")
        self.resize(960, 640)

        self.video_path = video_path
        self.subs_path = subs_path
        self.title = title
        self._cues = None
        self._ffmpeg_cmd = None
        self._subs_dirty = False
        self._busy = False
        self._proc: QProcess | None = None
        self._hwaccel_config: fvs.HWAccelConfig | None = None
        self._sliced_cues: list[fvs.SRTCue] = []
        self._suppress_errors = False
        self._sliced_cues = []

        self.temp_dir = Path(tempfile.gettempdir()) / "fastvideoslice_preview"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.preview_path = self.temp_dir / f"preview_{uuid.uuid4().hex}.mp4"

        self._build_ui(start, end, initial_precise, use_hwaccel_default)
        if initial_subs_text:
            self._set_subs_text(initial_subs_text, mark_dirty=True)
        # 初次載入
        self._generate_preview()

    def _build_ui(self, start: str, end: str, initial_precise: bool, use_hwaccel_default: bool) -> None:
        layout = QVBoxLayout(self)

        # 影片區
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumHeight(480)  # 放大預覽區域（即使源為 360p 也可放大顯示）
        layout.addWidget(self.video_widget, 3)

        # 即時字幕顯示（置於影片下方，非疊加）
        self.live_sub_label = QLabel("")
        self.live_sub_label.setWordWrap(True)
        self.live_sub_label.setAlignment(Qt.AlignCenter)
        self.live_sub_label.setStyleSheet(
            "background: rgba(0,0,0,0.05);"
            "border: 1px solid #D1D5DB;"
            "border-radius: 6px;"
            "padding: 8px;"
            "margin-top: 6px;"
            "font-size: 14px;"
        )
        layout.addWidget(self.live_sub_label)

        # 播放控制
        self.player = QMediaPlayer(self)
        self.player.setVideoOutput(self.video_widget)
        self.player.setVolume(70)
        self._duration_ms = 0
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.positionChanged.connect(self._on_position_changed)

        playback_controls = QHBoxLayout()
        self.play_btn = QPushButton("播放")
        self.play_btn.clicked.connect(self.player.play)
        playback_controls.addWidget(self.play_btn)

        self.pause_btn = QPushButton("暫停")
        self.pause_btn.clicked.connect(self.player.pause)
        playback_controls.addWidget(self.pause_btn)

        self.stop_btn = QPushButton("停止")
        self.stop_btn.setProperty("secondary", True)
        self.stop_btn.clicked.connect(self.player.stop)
        playback_controls.addWidget(self.stop_btn)

        self.position_label = QLabel("00:00 / 00:00")
        self.position_label.setProperty("hint", True)
        playback_controls.addWidget(self.position_label)

        playback_controls.addStretch()
        layout.addLayout(playback_controls)

        # 時間軸
        slider_row = QHBoxLayout()
        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.setEnabled(False)
        self.seek_slider.sliderMoved.connect(self._on_slider_moved)
        slider_row.addWidget(self.seek_slider)
        layout.addLayout(slider_row)

        # 時間輸入與按鈕
        controls = QHBoxLayout()
        controls.addWidget(QLabel("開始"))
        self.start_edit = QLineEdit(start)
        self.start_edit.setPlaceholderText("HH:MM:SS.ff（ff 為影格，預設 30fps）")
        controls.addWidget(self.start_edit)

        controls.addWidget(QLabel("結束"))
        self.end_edit = QLineEdit(end)
        self.end_edit.setPlaceholderText("HH:MM:SS.ff（ff 為影格，預設 30fps）")
        controls.addWidget(self.end_edit)

        self.refresh_btn = QPushButton("重新產生預覽")
        self.refresh_btn.clicked.connect(self._generate_preview)
        controls.addWidget(self.refresh_btn)

        self.cancel_btn = QPushButton("取消產生")
        self.cancel_btn.setProperty("secondary", True)
        self.cancel_btn.clicked.connect(self._cancel_preview)
        self.cancel_btn.setEnabled(False)
        controls.addWidget(self.cancel_btn)

        self.apply_btn = QPushButton("套用到列表")
        self.apply_btn.setProperty("secondary", True)
        self.apply_btn.clicked.connect(self._apply_range)
        controls.addWidget(self.apply_btn)

        controls.addStretch()
        layout.addLayout(controls)

        # 精準輸出切換
        precise_layout = QHBoxLayout()
        self.precise_cb = QPushButton("精準輸出：關")
        self.precise_cb.setCheckable(True)
        self.precise_cb.setChecked(initial_precise)
        self.precise_cb.clicked.connect(self._toggle_precise_label)
        self._toggle_precise_label()
        precise_layout.addWidget(self.precise_cb)

        self.hwaccel_cb = QCheckBox("硬體加速 (VideoToolbox)")
        self.hwaccel_cb.setChecked(use_hwaccel_default)
        precise_layout.addWidget(self.hwaccel_cb)

        precise_layout.addStretch()
        layout.addLayout(precise_layout)

        # 狀態
        self.status_label = QLabel("")
        self.status_label.setProperty("hint", True)
        layout.addWidget(self.status_label)

        # 簡易進度條（不使用執行緒，僅顯示工作中）
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # 無限動畫
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # 字幕預覽
        layout.addWidget(QLabel("字幕預覽"))
        self.subs_preview = QPlainTextEdit()
        self.subs_preview.setReadOnly(False)
        self.subs_preview.setMinimumHeight(160)
        self.subs_preview.textChanged.connect(self._on_subs_changed)
        layout.addWidget(self.subs_preview, 1)

    def _generate_preview(self) -> None:
        if self._busy:
            return
        self._set_busy(True, "產生預覽中...")
        start_text = self.start_edit.text().strip()
        end_text = self.end_edit.text().strip()

        try:
            start_sec = fvs.parse_hms(start_text)
            end_sec = fvs.parse_hms(end_text)
            if start_sec >= end_sec:
                raise fvs.UserError("開始時間需小於結束時間")
        except fvs.UserError as exc:
            QMessageBox.warning(self, "時間格式錯誤", str(exc))
            return

        try:
            if self._ffmpeg_cmd is None:
                ffmpeg_cmd, _ = fvs.ensure_ffmpeg_exists()
                self._ffmpeg_cmd = ffmpeg_cmd
            if self._cues is None:
                self._cues = fvs.read_srt(self.subs_path)
            if self._hwaccel_config is None and self.hwaccel_cb.isChecked():
                self._hwaccel_config = fvs.detect_hwaccel(self._ffmpeg_cmd)

            rng = fvs.TimeRange(
                start=start_sec,
                end=end_sec,
                label=f"{start_text} -> {end_text}",
                title=self.title or None,
                safe_title=fvs.sanitize_title(self.title) if self.title else None,
            )

            if self.preview_path.exists():
                self.preview_path.unlink()

            cmd = self._build_ffmpeg_cmd(rng)
            self._start_process(cmd, rng)
        except fvs.UserError as exc:
            QMessageBox.warning(self, "預覽失敗", str(exc))
            self._set_busy(False)
        except Exception as exc:  # pragma: no cover - GUI safety net
            QMessageBox.critical(self, "預覽失敗", f"非預期錯誤：{exc}")
            self._set_busy(False)

    def _apply_range(self) -> None:
        start_text = self.start_edit.text().strip()
        end_text = self.end_edit.text().strip()
        try:
            start_sec = fvs.parse_hms(start_text)
            end_sec = fvs.parse_hms(end_text)
            if start_sec >= end_sec:
                raise fvs.UserError("開始時間需小於結束時間")
        except fvs.UserError as exc:
            QMessageBox.warning(self, "時間格式錯誤", str(exc))
            return

        edited_subs = self.subs_preview.toPlainText()
        self.range_applied.emit(
            start_text,
            end_text,
            edited_subs,
            self.precise_cb.isChecked(),
        )
        self.status_label.setText("已套用至列表（時間、字幕、精準模式）")

    def _set_subs_text(self, text: str, mark_dirty: bool) -> None:
        """設定字幕文字並控制 dirty 標記"""
        self.subs_preview.blockSignals(True)
        self.subs_preview.setPlainText(text)
        self.subs_preview.blockSignals(False)
        self._subs_dirty = mark_dirty

    def _on_subs_changed(self) -> None:
        self._subs_dirty = True

    # ---- 播放器狀態 ----
    def _on_duration_changed(self, duration_ms: int) -> None:
        self._duration_ms = duration_ms
        self.seek_slider.setEnabled(duration_ms > 0)
        self._update_position_label(self.player.position(), duration_ms)

    def _on_position_changed(self, pos_ms: int) -> None:
        if self._duration_ms > 0:
            ratio = pos_ms / self._duration_ms
            self.seek_slider.blockSignals(True)
            self.seek_slider.setValue(int(ratio * 1000))
            self.seek_slider.blockSignals(False)
        self._update_position_label(pos_ms, self._duration_ms)
        self._update_live_sub(pos_ms)

    def _on_slider_moved(self, value: int) -> None:
        if self._duration_ms > 0:
            target = int(self._duration_ms * (value / 1000))
            self.player.setPosition(target)

    def _update_position_label(self, pos_ms: int, duration_ms: int) -> None:
        self.position_label.setText(f"{_format_ms(pos_ms)} / {_format_ms(duration_ms)}")

    def _toggle_precise_label(self) -> None:
        self.precise_cb.setText("精準輸出：開" if self.precise_cb.isChecked() else "精準輸出：關")

    def _build_ffmpeg_cmd(self, rng: fvs.TimeRange) -> list[str]:
        if self.precise_cb.isChecked():
            cfg = self._hwaccel_config if self.hwaccel_cb.isChecked() else None
            vcodec = cfg.vcodec if cfg else ("h264_videotoolbox" if self.hwaccel_cb.isChecked() else "libx264")
            vopts = cfg.vopts if cfg else (["-b:v", "8M", "-pix_fmt", "yuv420p"] if self.hwaccel_cb.isChecked() else ["-preset", "ultrafast", "-crf", "20"])
            cmd = [self._ffmpeg_cmd, "-y"]
            if cfg and cfg.hwaccel_args:
                cmd += cfg.hwaccel_args
            elif self.hwaccel_cb.isChecked():
                cmd += ["-hwaccel", "videotoolbox"]
            cmd += [
                "-i",
                str(self.video_path),
                "-ss",
                fvs.format_ffmpeg_time(rng.start),
                "-t",
                fvs.format_ffmpeg_time(rng.end - rng.start),
                "-c:v",
                vcodec,
                *vopts,
                "-vf",
                "scale=-2:360",
                "-c:a",
                "aac",
                "-ac",
                "2",
                "-b:a",
                "96k",
                "-movflags",
                "+faststart",
                str(self.preview_path),
            ]
        else:
            cmd = [
                self._ffmpeg_cmd,
                "-y",
                "-ss",
                fvs.format_ffmpeg_time(rng.start),
                "-to",
                fvs.format_ffmpeg_time(rng.end),
                "-i",
                str(self.video_path),
                "-c",
                "copy",
                str(self.preview_path),
            ]
        return cmd

    def _start_process(self, cmd: list[str], rng: fvs.TimeRange) -> None:
        if self._proc:
            self._proc.kill()
            self._proc.waitForFinished(2000)
            self._proc.deleteLater()
            self._proc = None
        self._proc = QProcess(self)
        env = self._proc.processEnvironment()
        for key in ("LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH", "DYLD_FALLBACK_LIBRARY_PATH", "DYLD_FRAMEWORK_PATH", "DYLD_VERSIONED_LIBRARY_PATH", "PYTHONHOME", "PYTHONPATH"):
            env.remove(key)
        self._proc.setProcessEnvironment(env)
        self._proc.finished.connect(lambda *_: self._on_proc_finished(rng))
        self._proc.errorOccurred.connect(self._on_proc_error)
        self._proc.start(cmd[0], cmd[1:])

    def _on_proc_finished(self, rng: fvs.TimeRange) -> None:
        if not self._proc:
            return
        if self._proc.exitStatus() == QProcess.NormalExit and self._proc.exitCode() == 0:
            try:
                sliced_cues = fvs.slice_cues(self._cues, rng)
                self._sliced_cues = sliced_cues
                if not self._subs_dirty:
                    self._set_subs_text(fvs.format_srt(sliced_cues), mark_dirty=False)
                # 初始字幕顯示
                self._update_live_sub(0)

                media = QMediaContent(QUrl.fromLocalFile(str(self.preview_path)))
                self.player.setMedia(media)
                self.player.play()

                self.status_label.setText("預覽已更新")
            except Exception as exc:  # pragma: no cover
                if not self._suppress_errors:
                    QMessageBox.warning(self, "預覽失敗", f"處理結果時發生錯誤: {exc}")
        else:
            if not self._suppress_errors:
                QMessageBox.warning(self, "預覽取消/失敗", "預覽已中斷或失敗")
        self._set_busy(False)
        self._cleanup_proc()

    def _on_proc_error(self, error) -> None:
        if not self._suppress_errors:
            QMessageBox.warning(self, "預覽失敗", f"ffmpeg 執行失敗: {error}")
        self._set_busy(False)
        self._cleanup_proc()

    def _cancel_preview(self) -> None:
        if self._proc:
            self._proc.kill()
            self._proc.waitForFinished(2000)
        self._set_busy(False, "已取消產生")
        self._cleanup_proc()

    def _cleanup_proc(self) -> None:
        if self._proc:
            self._proc.deleteLater()
            self._proc = None
        # 保留 _sliced_cues，供即時字幕使用

    def _update_live_sub(self, pos_ms: int) -> None:
        """根據播放時間更新下方字幕顯示"""
        if not self._sliced_cues:
            self.live_sub_label.setText("")
            return
        pos_s = pos_ms / 1000.0
        text = ""
        for cue in self._sliced_cues:
            if cue.start <= pos_s <= cue.end:
                text = "\n".join(cue.lines)
                break
        self.live_sub_label.setText(text)

    def closeEvent(self, event) -> None:
        if self._proc:
            self._suppress_errors = True
            proc = self._proc
            self._proc = None
            proc.kill()
            proc.waitForFinished(2000)
            proc.deleteLater()
        self.player.stop()
        try:
            if self.preview_path.exists():
                self.preview_path.unlink()
        except OSError:
            pass
        super().closeEvent(event)

    def _set_busy(self, busy: bool, message: str | None = None) -> None:
        """簡易 busy 標記，禁用互動並顯示進度條"""
        self._busy = busy
        widgets = [
            self.refresh_btn,
            self.apply_btn,
            self.play_btn,
            self.pause_btn,
            self.stop_btn,
            self.seek_slider,
            self.start_edit,
            self.end_edit,
            self.precise_cb,
            self.cancel_btn,
        ]
        for w in widgets:
            w.setEnabled(not busy)
        self.progress.setVisible(busy)
        if message:
            self.status_label.setText(message)
        # 不切換全域游標，避免等待圖標干擾


def _format_ms(ms: int) -> str:
    if ms <= 0:
        return "00:00"
    total_seconds, milli = divmod(ms, 1000)
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"
