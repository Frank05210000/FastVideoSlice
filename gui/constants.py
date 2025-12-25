"""
常數與樣式定義
"""

# 應用程式設定
APP_NAME = "FastVideoSlice"
APP_VERSION = "0.1.0"
SETTINGS_FILE = ".fastvideoslice_settings.json"

# 視窗預設大小
WINDOW_WIDTH = 900
WINDOW_HEIGHT = 700

# 時間格式（影格附檔位，預設 30fps：HH:MM:SS.ff）
TIME_FORMAT = "HH:MM:SS(.ff)"
TIME_PATTERN = r"^\d{2}:\d{2}:\d{2}(?:[.:]\d{1,2})?$"
RANGE_SEPARATOR = " -> "

# 顏色定義
COLORS = {
    "primary": "#2563EB",      # 主要按鈕藍色
    "primary_hover": "#1D4ED8",
    "error": "#DC2626",        # 錯誤紅色
    "error_bg": "#FEE2E2",     # 錯誤背景淺紅
    "success": "#16A34A",      # 成功綠色
    "warning": "#F59E0B",      # 警告橙色
    "background": "#F9FAFB",   # 背景色
    "surface": "#FFFFFF",      # 表面色
    "border": "#E5E7EB",       # 邊框色
    "text": "#111827",         # 主要文字
    "text_secondary": "#6B7280", # 次要文字
}

# 樣式表
STYLESHEET = f"""
QWidget {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 14px;
    color: {COLORS['text']};
}}

QMainWindow {{
    background-color: {COLORS['background']};
}}

QGroupBox {{
    font-weight: bold;
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 10px;
    background-color: {COLORS['surface']};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}}

QPushButton {{
    background-color: {COLORS['primary']};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}}

QPushButton:hover {{
    background-color: {COLORS['primary_hover']};
}}

QPushButton:disabled {{
    background-color: {COLORS['border']};
    color: {COLORS['text_secondary']};
}}

QPushButton[secondary="true"] {{
    background-color: {COLORS['surface']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
}}

QPushButton[secondary="true"]:hover {{
    background-color: {COLORS['background']};
}}

QLineEdit, QPlainTextEdit {{
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 6px 10px;
    background-color: {COLORS['surface']};
}}

QLineEdit:focus, QPlainTextEdit:focus {{
    border-color: {COLORS['primary']};
}}

QLineEdit[error="true"] {{
    border-color: {COLORS['error']};
    background-color: {COLORS['error_bg']};
}}

QTableWidget {{
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    background-color: {COLORS['surface']};
    gridline-color: {COLORS['border']};
}}

QTableWidget::item {{
    padding: 8px;
}}

QTableWidget::item:selected {{
    background-color: {COLORS['primary']};
    color: white;
}}

QHeaderView::section {{
    background-color: {COLORS['background']};
    border: none;
    border-bottom: 1px solid {COLORS['border']};
    padding: 8px;
    font-weight: bold;
}}

QProgressBar {{
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    text-align: center;
    background-color: {COLORS['background']};
}}

QProgressBar::chunk {{
    background-color: {COLORS['primary']};
    border-radius: 3px;
}}

QCheckBox {{
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid {COLORS['border']};
}}

QCheckBox::indicator:checked {{
    background-color: {COLORS['primary']};
    border-color: {COLORS['primary']};
}}

QLabel[heading="true"] {{
    font-size: 16px;
    font-weight: bold;
}}

QLabel[hint="true"] {{
    color: {COLORS['text_secondary']};
    font-size: 12px;
}}
"""
