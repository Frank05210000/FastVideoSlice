"""
區間管理表格元件

提供時間區間的表格式管理，支援新增/刪除/複製/排序功能。
"""

import re
from typing import List, Optional, Tuple

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QHeaderView,
    QAbstractItemView,
    QLabel,
    QMessageBox,
    QDialog,
    QFormLayout,
    QLineEdit,
    QDialogButtonBox,
)

from .constants import TIME_PATTERN, COLORS
import fast_video_slice as fvs


def _to_seconds(text: str) -> float:
    """將 HH:MM:SS(.ff) 轉為秒數（ff 依 30fps 解讀為影格）"""
    return fvs.parse_hms(text)


class TimeRangeDialog(QDialog):
    """新增/編輯時間區間的對話框"""

    def __init__(self, parent=None, title: str = "", start: str = "", end: str = "", note: str = ""):
        super().__init__(parent)
        self.setWindowTitle("時間區間")
        self.setMinimumWidth(350)
        self._build_ui(title, start, end, note)

    def _build_ui(self, title: str, start: str, end: str, note: str) -> None:
        layout = QFormLayout(self)

        self.title_edit = QLineEdit(title)
        self.title_edit.setPlaceholderText("（選填，作為輸出檔名）")
        layout.addRow("標題：", self.title_edit)

        self.start_edit = QLineEdit(start)
        self.start_edit.setPlaceholderText("HH:MM:SS 或 HH:MM:SS.ff（ff 為影格，預設 30fps）")
        layout.addRow("開始時間：", self.start_edit)

        self.end_edit = QLineEdit(end)
        self.end_edit.setPlaceholderText("HH:MM:SS 或 HH:MM:SS.ff（ff 為影格，預設 30fps）")
        layout.addRow("結束時間：", self.end_edit)

        self.note_edit = QLineEdit(note)
        self.note_edit.setPlaceholderText("（選填）")
        layout.addRow("備註：", self.note_edit)

        hint = QLabel("格式：HH:MM:SS 或 HH:MM:SS.ff（ff 以 30fps 計算影格，例如 00:01:30.15）")
        hint.setProperty("hint", True)
        layout.addRow(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _validate_and_accept(self) -> None:
        start = self.start_edit.text().strip()
        end = self.end_edit.text().strip()

        try:
            # 會檢查格式與影格範圍
            if not re.match(TIME_PATTERN, start) or not re.match(TIME_PATTERN, end):
                raise ValueError
            if not self._validate_time_order(start, end):
                raise ValueError("開始時間必須小於結束時間")
        except Exception as exc:
            msg = str(exc) if str(exc) else "時間格式需為 HH:MM:SS 或 HH:MM:SS.ff（ff 為影格，預設 30fps）"
            QMessageBox.warning(self, "格式錯誤", msg)
            return

        self.accept()

    def _validate_time_order(self, start: str, end: str) -> bool:
        """驗證開始時間小於結束時間"""
        return _to_seconds(start) < _to_seconds(end)

    def get_values(self) -> Tuple[str, str, str, str]:
        return (
            self.title_edit.text().strip(),
            self.start_edit.text().strip(),
            self.end_edit.text().strip(),
            self.note_edit.text().strip(),
        )


class RangeTableWidget(QWidget):
    """區間管理表格元件"""

    # 當區間變更時發出信號
    ranges_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["#", "標題", "開始時間", "結束時間", "備註", "精準"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        header.setSectionResizeMode(4, QHeaderView.Interactive)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 200)
        self.table.setColumnWidth(2, 130)
        self.table.setColumnWidth(3, 130)
        self.table.setColumnWidth(4, 200)
        self.table.setColumnWidth(5, 80)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.doubleClicked.connect(lambda idx: self._edit_row(idx.row()))
        self.table.cellChanged.connect(self._on_cell_changed)
        layout.addWidget(self.table)

        # 操作按鈕列
        btn_layout = QHBoxLayout()

        self.add_btn = QPushButton("＋ 新增")
        self.add_btn.clicked.connect(self._on_add)
        btn_layout.addWidget(self.add_btn)

        self.delete_btn = QPushButton("刪除")
        self.delete_btn.setProperty("secondary", True)
        self.delete_btn.clicked.connect(self._on_delete)
        btn_layout.addWidget(self.delete_btn)

        self.copy_btn = QPushButton("複製")
        self.copy_btn.setProperty("secondary", True)
        self.copy_btn.clicked.connect(self._on_copy)
        btn_layout.addWidget(self.copy_btn)

        self.edit_btn = QPushButton("編輯")
        self.edit_btn.setProperty("secondary", True)
        self.edit_btn.clicked.connect(self._on_edit_clicked)
        btn_layout.addWidget(self.edit_btn)

        self.preview_btn = QPushButton("預覽/微調")
        self.preview_btn.setProperty("secondary", True)
        btn_layout.addWidget(self.preview_btn)

        btn_layout.addSpacing(20)

        self.up_btn = QPushButton("↑ 上移")
        self.up_btn.setProperty("secondary", True)
        self.up_btn.clicked.connect(self._on_move_up)
        btn_layout.addWidget(self.up_btn)

        self.down_btn = QPushButton("↓ 下移")
        self.down_btn.setProperty("secondary", True)
        self.down_btn.clicked.connect(self._on_move_down)
        btn_layout.addWidget(self.down_btn)

        btn_layout.addStretch()

        # 匯入/匯出
        self.import_btn = QPushButton("匯入")
        self.import_btn.setProperty("secondary", True)
        self.import_btn.clicked.connect(self._on_import)
        btn_layout.addWidget(self.import_btn)

        self.export_btn = QPushButton("匯出")
        self.export_btn.setProperty("secondary", True)
        self.export_btn.clicked.connect(self._on_export)
        btn_layout.addWidget(self.export_btn)

        self.prompt_btn = QPushButton("📋 AI 提示詞")
        self.prompt_btn.setProperty("secondary", True)
        self.prompt_btn.setToolTip("複製區間格式範本，可貼給 AI 產生區間列表")
        self.prompt_btn.clicked.connect(self._on_copy_prompt)
        btn_layout.addWidget(self.prompt_btn)

        layout.addLayout(btn_layout)

        # 格式提示
        hint = QLabel("格式：HH:MM:SS 或 HH:MM:SS.ff（ff 以 30fps 計算影格，雙擊表格內直接編輯）")
        hint.setProperty("hint", True)
        layout.addWidget(hint)

    def _update_row_numbers(self) -> None:
        """更新序號欄"""
        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            item = QTableWidgetItem(str(row + 1))
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, item)
        self.table.blockSignals(False)

    def _on_add(self) -> None:
        dialog = TimeRangeDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            title, start, end, note = dialog.get_values()
            self._add_row(title, start, end, note)
            self.ranges_changed.emit()

    def _add_row(self, title: str = "", start: str = "", end: str = "", note: str = "", precise: bool = False) -> None:
        row = self.table.rowCount()
        self.table.blockSignals(True)
        self.table.insertRow(row)

        # 序號（不可編輯）
        num_item = QTableWidgetItem(str(row + 1))
        num_item.setFlags(num_item.flags() & ~Qt.ItemIsEditable)
        num_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, 0, num_item)

        # 標題
        self.table.setItem(row, 1, QTableWidgetItem(title))
        # 開始時間
        self.table.setItem(row, 2, QTableWidgetItem(start))
        # 結束時間
        self.table.setItem(row, 3, QTableWidgetItem(end))
        # 備註
        self.table.setItem(row, 4, QTableWidgetItem(note))

        # 精準輸出勾選
        precise_item = QTableWidgetItem("精準輸出")
        precise_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        precise_item.setCheckState(Qt.Checked if precise else Qt.Unchecked)
        self.table.setItem(row, 5, precise_item)

        self.table.blockSignals(False)

    def _on_delete(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
            self._update_row_numbers()
            self.ranges_changed.emit()

    def _on_copy(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            title = self.table.item(row, 1).text() if self.table.item(row, 1) else ""
            start = self.table.item(row, 2).text() if self.table.item(row, 2) else ""
            end = self.table.item(row, 3).text() if self.table.item(row, 3) else ""
            note = self.table.item(row, 4).text() if self.table.item(row, 4) else ""
            precise = self.table.item(row, 5).checkState() == Qt.Checked if self.table.item(row, 5) else False
            self._add_row(title, start, end, note, precise)
            self.ranges_changed.emit()

    def _on_edit_clicked(self) -> None:
        self._edit_row(self.table.currentRow())

    def _edit_row(self, row: int) -> None:
        if row < 0:
            return
        title = self.table.item(row, 1).text() if self.table.item(row, 1) else ""
        start = self.table.item(row, 2).text() if self.table.item(row, 2) else ""
        end = self.table.item(row, 3).text() if self.table.item(row, 3) else ""
        note = self.table.item(row, 4).text() if self.table.item(row, 4) else ""
        precise = self.table.item(row, 5).checkState() == Qt.Checked if self.table.item(row, 5) else False

        dialog = TimeRangeDialog(self, title=title, start=start, end=end, note=note)
        if dialog.exec_() == QDialog.Accepted:
            new_title, new_start, new_end, new_note = dialog.get_values()
            self.table.blockSignals(True)
            self.table.setItem(row, 1, QTableWidgetItem(new_title))
            self.table.setItem(row, 2, QTableWidgetItem(new_start))
            self.table.setItem(row, 3, QTableWidgetItem(new_end))
            self.table.setItem(row, 4, QTableWidgetItem(new_note))
            # 保留原有精準選擇
            precise_item = QTableWidgetItem("精準輸出")
            precise_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            precise_item.setCheckState(Qt.Checked if precise else Qt.Unchecked)
            self.table.setItem(row, 5, precise_item)
            self.table.blockSignals(False)
            self.ranges_changed.emit()

    def _on_move_up(self) -> None:
        row = self.table.currentRow()
        if row > 0:
            self._swap_rows(row, row - 1)
            self.table.selectRow(row - 1)
            self.ranges_changed.emit()

    def _on_move_down(self) -> None:
        row = self.table.currentRow()
        if row >= 0 and row < self.table.rowCount() - 1:
            self._swap_rows(row, row + 1)
            self.table.selectRow(row + 1)
            self.ranges_changed.emit()

    def _swap_rows(self, row1: int, row2: int) -> None:
        self.table.blockSignals(True)
        for col in range(1, 6):  # 跳過序號欄
            item1 = self.table.takeItem(row1, col)
            item2 = self.table.takeItem(row2, col)
            self.table.setItem(row1, col, item2)
            self.table.setItem(row2, col, item1)
        self.table.blockSignals(False)

    def _on_cell_changed(self, row: int, col: int) -> None:
        if col in (2, 3):  # 時間欄位變更時驗證格式
            item = self.table.item(row, col)
            if item:
                text = item.text().strip()
                if text and not re.match(TIME_PATTERN, text):
                    item.setBackground(Qt.red)
                else:
                    item.setBackground(Qt.white)
        self.ranges_changed.emit()

    def _on_import(self) -> None:
        """從文字匯入區間（容錯：以核心 parse_hms 驗證）"""
        from PyQt5.QtWidgets import QInputDialog
        text, ok = QInputDialog.getMultiLineText(
            self,
            "匯入區間",
            "每行一個區間，格式：標題,HH:MM:SS(.ff) -> HH:MM:SS(.ff) 或 HH:MM:SS(.ff) -> HH:MM:SS(.ff)",
        )
        if not (ok and text.strip()):
            return

        lines = text.strip().split("\n")
        invalid_lines = []
        added = 0

        for raw in lines:
            line = raw.strip()
            if not line:
                continue

            title = ""
            times_part = line
            if "," in line:
                title, times_part = line.split(",", 1)
                title = title.strip()
                times_part = times_part.strip()

            parts = re.split(r"\s*->\s*", times_part)
            if len(parts) != 2:
                invalid_lines.append(raw)
                continue

            start_str, end_str = parts[0].strip(), parts[1].strip()
            try:
                start_s = fvs.parse_hms(start_str)
                end_s = fvs.parse_hms(end_str)
                if start_s >= end_s:
                    raise ValueError("start>=end")
            except Exception:
                invalid_lines.append(raw)
                continue

            self._add_row(title, start_str, end_str)
            added += 1

        self._update_row_numbers()
        self.ranges_changed.emit()

        if invalid_lines:
            QMessageBox.warning(
                self,
                "部分匯入失敗",
                f"{len(invalid_lines)} 行格式無效或 start>=end，已略過。\n\n無效行：\n" + "\n".join(invalid_lines[:5]),
            )

    def _on_export(self) -> None:
        """匯出區間為文字"""
        ranges = self.get_ranges()
        if not ranges:
            QMessageBox.information(self, "匯出", "沒有區間可匯出")
            return
        lines = []
        for r in ranges:
            if r.get("title"):
                lines.append(f"{r['title']},{r['start']} -> {r['end']}")
            else:
                lines.append(f"{r['start']} -> {r['end']}")
        text = "\n".join(lines)
        from PyQt5.QtWidgets import QInputDialog
        dialog = QInputDialog(self)
        dialog.setWindowTitle("匯出區間")
        dialog.setLabelText("複製以下內容：")
        dialog.setTextValue(text)
        dialog.setOption(QInputDialog.UsePlainTextEditForTextInput, True)
        dialog.exec_()

    def _on_copy_prompt(self) -> None:
        """複製 AI 提示詞樣式到剪貼簿"""
        from PyQt5.QtWidgets import QApplication
        template = """請依照以下格式輸出影片裁切區間，每行一段：
標題,HH:MM:SS(.ff) -> HH:MM:SS(.ff)   （ff 為影格，預設 30fps）

規則：
- 標題需唯一（不可重複）
- 標題會用於輸出檔名，非法字元會轉為底線
- 若不需標題可省略：HH:MM:SS(.ff) -> HH:MM:SS(.ff)

範例：
精華片段一,00:01:10.00 -> 00:01:45.15
重點說明,00:05:00 -> 00:05:30.25
結尾彩蛋,00:10:00 -> 00:10:20"""
        clipboard = QApplication.clipboard()
        clipboard.setText(template)
        QMessageBox.information(self, "已複製", "AI 提示詞樣式已複製到剪貼簿，可貼給 AI 產生區間列表")

    def get_ranges(self) -> List[dict]:
        """取得所有區間資料"""
        ranges = []
        for row in range(self.table.rowCount()):
            title_item = self.table.item(row, 1)
            start_item = self.table.item(row, 2)
            end_item = self.table.item(row, 3)
            note_item = self.table.item(row, 4)
            precise_item = self.table.item(row, 5)
            if start_item and end_item:
                title = title_item.text().strip() if title_item else ""
                start = start_item.text().strip()
                end = end_item.text().strip()
                note = note_item.text().strip() if note_item else ""
                precise = precise_item.checkState() == Qt.Checked if precise_item else False
                if start and end:
                    ranges.append(
                        {
                            "title": title,
                            "start": start,
                            "end": end,
                            "note": note,
                            "precise": precise,
                        }
                    )
        return ranges

    def get_range_at(self, row: int) -> Optional[dict]:
        """取得指定列的區間資料"""
        if row < 0 or row >= self.table.rowCount():
            return None
        title_item = self.table.item(row, 1)
        start_item = self.table.item(row, 2)
        end_item = self.table.item(row, 3)
        note_item = self.table.item(row, 4)
        precise_item = self.table.item(row, 5)
        if not start_item or not end_item:
            return None
        title = title_item.text().strip() if title_item else ""
        start = start_item.text().strip()
        end = end_item.text().strip()
        note = note_item.text().strip() if note_item else ""
        precise = precise_item.checkState() == Qt.Checked if precise_item else False
        if not start or not end:
            return None
        return {"title": title, "start": start, "end": end, "note": note, "precise": precise}

    def set_ranges(self, ranges: List[dict]) -> None:
        """設定區間資料（用於載入設定）"""
        self.table.setRowCount(0)
        for r in ranges:
            self._add_row(
                r.get("title", ""),
                r.get("start", ""),
                r.get("end", ""),
                r.get("note", ""),
                r.get("precise", False),
            )

    def clear(self) -> None:
        """清空表格"""
        self.table.setRowCount(0)

    def validate(self) -> Tuple[bool, List[int]]:
        """
        驗證所有區間格式是否正確
        
        Returns:
            (is_valid, error_rows): 是否全部有效，以及錯誤的行號列表
        """
        error_rows = []
        for row in range(self.table.rowCount()):
            start_item = self.table.item(row, 2)
            end_item = self.table.item(row, 3)

            start = start_item.text().strip() if start_item else ""
            end = end_item.text().strip() if end_item else ""

            if not re.match(TIME_PATTERN, start) or not re.match(TIME_PATTERN, end):
                error_rows.append(row)
                continue

            # 驗證 start < end，並讓 parse_hms 幫忙檢查影格範圍
            try:
                if _to_seconds(start) >= _to_seconds(end):
                    error_rows.append(row)
            except Exception:
                error_rows.append(row)

        return len(error_rows) == 0, error_rows

    def highlight_error_rows(self, rows: List[int]) -> None:
        """高亮錯誤行"""
        for row in range(self.table.rowCount()):
            for col in range(2, 4):  # 時間欄位
                item = self.table.item(row, col)
                if item:
                    if row in rows:
                        item.setBackground(Qt.red)
                    else:
                        item.setBackground(Qt.white)
