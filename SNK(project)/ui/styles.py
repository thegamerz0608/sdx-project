"""
Enterprise Qt Style Sheet (QSS) & UI Design System
Provides clean, consistent typography, responsive sizing, modern web-like data grids,
sleek custom scrollbars, and interactive states matching Windows 11 Fluent and Tailwind design principles.
"""
from PySide6.QtWidgets import QApplication, QWidget


ENTERPRISE_QSS = """
/* ==========================================================================
   1. GLOBAL TYPOGRAPHY & APPLICATION ROOT
   ========================================================================== */
* {
    font-family: 'Segoe UI', 'Roboto', 'Inter', -apple-system, sans-serif;
    color: #0F172A;
    outline: none;
}

QMainWindow, QDialog {
    background-color: #F8FAFC;
    color: #0F172A;
    font-size: 13px;
}

QWidget {
    font-size: 13px;
}

/* ==========================================================================
   2. MODERN SIDEBAR & NAVIGATION
   ========================================================================== */
#modernSidebar {
    background-color: #0F172A;
    border-right: 1px solid #1E293B;
}

#sidebarBrand {
    color: #FFFFFF;
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0.5px;
}

#sidebarToggle {
    background-color: #1E293B;
    color: #94A3B8;
    border: none;
    border-radius: 6px;
    font-size: 16px;
    font-weight: bold;
}

#sidebarToggle:hover {
    background-color: #334155;
    color: #FFFFFF;
}

#sidebarToggle:pressed {
    background-color: #0F172A;
}

#sidebarNavButton {
    background-color: transparent;
    color: #94A3B8;
    border: none;
    border-radius: 8px;
    text-align: left;
    padding-left: 12px;
    font-size: 13px;
    font-weight: 500;
    min-height: 38px;
}

#sidebarNavButton:hover {
    background-color: #1E293B;
    color: #F8FAFC;
}

#sidebarNavButton:checked {
    background-color: #2563EB;
    color: #FFFFFF;
    font-weight: 600;
}

#sidebarAuthBtn {
    background-color: #1E293B;
    color: #38BDF8;
    border: 1px solid #334155;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    padding: 8px;
}

#sidebarAuthBtn:hover {
    background-color: #0284C7;
    color: #FFFFFF;
    border-color: #0284C7;
}

/* ==========================================================================
   3. TOP APP BAR & PROFILE HEADER
   ========================================================================== */
#modernTopBar {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E2E8F0;
}

#topBarBreadcrumb {
    color: #475569;
    font-size: 14px;
    font-weight: 600;
}

#roleChip {
    border-radius: 12px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
}

/* ==========================================================================
   4. DASHBOARD BANNER & KPI CARDS
   ========================================================================== */
#dashboardWelcomeCard {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E3A8A, stop:1 #2563EB);
    border-radius: 12px;
}

#headerWelcome {
    color: #FFFFFF;
    font-size: 24px;
    font-weight: 800;
    letter-spacing: -0.4px;
}

#headerDesc {
    color: #BFDBFE;
    font-size: 13px;
    font-weight: 400;
}

#kpiCard {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
}

#kpiTitle {
    color: #64748B;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.6px;
}

#kpiValue {
    color: #0F172A;
    font-size: 22px;
    font-weight: 800;
}

#kpiSubtext {
    color: #94A3B8;
    font-size: 11.5px;
}

#workbenchCard {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
}

#workbenchTitle {
    color: #1E293B;
    font-size: 14px;
    font-weight: 700;
}

#workbenchCard QPushButton {
    background-color: #F8FAFC;
    color: #334155;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 9px 16px;
    font-size: 13px;
    font-weight: 600;
}

#workbenchCard QPushButton:hover {
    background-color: #2563EB;
    color: #FFFFFF;
    border-color: #2563EB;
}

/* ==========================================================================
   5. MODERN DATA GRIDS (QTableWidget & QHeaderView)
   ========================================================================== */
QTableWidget {
    background-color: #FFFFFF;
    alternate-background-color: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    gridline-color: transparent;
    selection-background-color: #EFF6FF;
    selection-color: #1E40AF;
    font-size: 13px;
    padding: 0px;
}

QTableWidget::item {
    padding: 6px 10px;
    border-bottom: 1px solid #F1F5F9;
    color: #1E293B;
}

QTableWidget::item:hover {
    background-color: #F1F5F9;
}

QTableWidget::item:selected {
    background-color: #EFF6FF;
    color: #1E40AF;
    font-weight: 600;
}

QHeaderView {
    background-color: #F8FAFC;
    border: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}

QHeaderView::section {
    background-color: #F8FAFC;
    color: #475569;
    font-weight: 700;
    font-size: 12.5px;
    padding: 6px 10px;
    border: none;
    border-bottom: 2px solid #E2E8F0;
}

QHeaderView::section:hover {
    background-color: #F1F5F9;
    color: #0F172A;
}

/* ==========================================================================
   6. SLEEK CUSTOM SCROLLBARS (QScrollBar)
   ========================================================================== */
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 2px 0px 2px 0px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #CBD5E1;
    min-height: 28px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #94A3B8;
}

QScrollBar::handle:vertical:pressed {
    background: #64748B;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
    width: 0px;
    background: transparent;
    border: none;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}

QScrollBar:horizontal {
    background: transparent;
    height: 8px;
    margin: 0px 2px 0px 2px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal {
    background: #CBD5E1;
    min-width: 28px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal:hover {
    background: #94A3B8;
}

QScrollBar::handle:horizontal:pressed {
    background: #64748B;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    height: 0px;
    width: 0px;
    background: transparent;
    border: none;
}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: transparent;
}

/* ==========================================================================
   7. INTERACTIVE BUTTONS & FORM INPUTS
   ========================================================================== */
QPushButton {
    background-color: #2563EB;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #1D4ED8;
}

QPushButton:pressed {
    background-color: #1E40AF;
}

QPushButton:disabled {
    background-color: #E2E8F0;
    color: #94A3B8;
}

QLineEdit, QSpinBox, QDateEdit, QTimeEdit {
    background-color: #FFFFFF;
    border: 1.5px solid #CBD5E1;
    border-radius: 6px;
    padding: 7px 12px;
    font-size: 13px;
    color: #0F172A;
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
}

QLineEdit:hover, QSpinBox:hover, QDateEdit:hover, QTimeEdit:hover {
    border-color: #94A3B8;
}

QLineEdit:focus, QSpinBox:focus, QDateEdit:focus, QTimeEdit:focus {
    border: 1.5px solid #2563EB;
    background-color: #FFFFFF;
}

QLineEdit:disabled, QSpinBox:disabled, QDateEdit:disabled, QTimeEdit:disabled {
    background-color: #F1F5F9;
    color: #94A3B8;
    border-color: #E2E8F0;
}

QCheckBox {
    font-size: 13px;
    color: #1E293B;
    spacing: 10px;
    font-weight: 500;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1.5px solid #CBD5E1;
    border-radius: 4px;
    background-color: #FFFFFF;
}

QCheckBox::indicator:hover {
    border-color: #2563EB;
}

QCheckBox::indicator:checked {
    background-color: #2563EB;
    border-color: #2563EB;
}

QComboBox {
    background-color: #FFFFFF;
    border: 1.5px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
    color: #0F172A;
    min-height: 22px;
}

QComboBox:hover {
    border-color: #94A3B8;
}

QComboBox:focus {
    border: 1.5px solid #2563EB;
}

QComboBox:disabled {
    background-color: #F1F5F9;
    color: #94A3B8;
    border-color: #E2E8F0;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border-left: 1px solid #E2E8F0;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}

QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    selection-background-color: #EFF6FF;
    selection-color: #1E40AF;
    padding: 4px;
}

/* ==========================================================================
   8. CARD GROUPS, TABS, CONSOLES & STATUS
   ========================================================================== */
QGroupBox {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    margin-top: 14px;
    padding: 16px 14px 14px 14px;
    font-size: 13px;
    font-weight: 700;
    color: #1E293B;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 8px;
    background-color: #FFFFFF;
    color: #1E293B;
}

QTabWidget::pane {
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    background-color: #FFFFFF;
    top: -1px;
    padding: 10px;
}

QTabBar::tab {
    background-color: #F1F5F9;
    color: #64748B;
    font-weight: 600;
    font-size: 13px;
    padding: 8px 18px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    border: 1px solid #E2E8F0;
    border-bottom: none;
}

QTabBar::tab:hover {
    background-color: #E2E8F0;
    color: #1E293B;
}

QTabBar::tab:selected {
    background-color: #FFFFFF;
    color: #2563EB;
    border-color: #E2E8F0;
    border-bottom: 2px solid #FFFFFF;
}

QTextEdit, QPlainTextEdit {
    background-color: #FFFFFF;
    color: #0F172A;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 13px;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 8px 12px;
}

QTextEdit:focus, QPlainTextEdit:focus {
    border: 1.5px solid #2563EB;
    background-color: #FFFFFF;
}

QTextEdit#codeConsole, QPlainTextEdit#codeConsole {
    background-color: #0F172A;
    color: #38BDF8;
    font-family: 'Consolas', monospace;
    font-size: 12px;
    border: 1px solid #1E293B;
}

QStatusBar {
    background-color: #FFFFFF;
    color: #64748B;
    border-top: 1px solid #E2E8F0;
    font-size: 12px;
    padding: 4px;
}

QToolTip {
    background-color: #0F172A;
    color: #F8FAFC;
    border: 1px solid #334155;
    border-radius: 4px;
    padding: 5px 8px;
    font-size: 12px;
}

/* ==========================================================================
   9. SPLITTERS & PROGRESS BARS
   ========================================================================== */
QSplitter::handle {
    background-color: #E2E8F0;
}

QSplitter::handle:horizontal {
    width: 2px;
}

QSplitter::handle:vertical {
    height: 2px;
}

QProgressBar {
    background-color: #E2E8F0;
    border-radius: 6px;
    text-align: center;
    font-size: 11px;
    font-weight: bold;
    color: #1E293B;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #38BDF8);
    border-radius: 6px;
}

/* Secondary Button Variant */
QPushButton#btnSecondary, QPushButton[class="btnSecondary"] {
    background-color: #F1F5F9;
    color: #334155;
    border: 1px solid #CBD5E1;
}

QPushButton#btnSecondary:hover, QPushButton[class="btnSecondary"]:hover {
    background-color: #E2E8F0;
    color: #0F172A;
    border-color: #94A3B8;
}

QPushButton#btnSuccess, QPushButton[class="btnSuccess"] {
    background-color: #10B981;
    color: #FFFFFF;
}

QPushButton#btnSuccess:hover, QPushButton[class="btnSuccess"]:hover {
    background-color: #059669;
}

QPushButton#btnDanger, QPushButton[class="btnDanger"] {
    background-color: #EF4444;
    color: #FFFFFF;
}

QPushButton#btnDanger:hover, QPushButton[class="btnDanger"]:hover {
    background-color: #DC2626;
}
"""

from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QTableWidgetItem, QLabel
from PySide6.QtCore import Qt


def get_status_colors(status: str) -> tuple:
    """Returns (bg_hex, fg_hex) tuple for any given attendance or leave status."""
    st = str(status).strip().upper()
    if st in ["PRESENT", "APPROVED", "ACTIVE", "CONNECTED", "ONLINE", "VALID"]:
        return "#ECFDF5", "#065F46"  # Emerald / Mint
    elif st in ["LATE", "PENDING", "HALF_DAY", "IN_REVIEW", "WARNING", "SUSPENDED"]:
        return "#FFFBEB", "#B45309"  # Amber
    elif st in ["ABSENT", "REJECTED", "CANCELLED", "OFFLINE", "ERROR", "INVALID", "EXHAUSTED"]:
        return "#FEF2F2", "#991B1B"  # Rose / Crimson
    elif st in ["CHECK_IN", "FACULTY", "TEST"]:
        return "#EFF6FF", "#1E40AF"  # Blue
    elif st in ["CHECK_OUT", "LAB_INSTRUCTOR"]:
        return "#F5F3FF", "#6D28D9"  # Purple
    return "#F1F5F9", "#475569"      # Slate default


def style_table_cell_badge(item: QTableWidgetItem, status: str, text: str = None):
    """
    Applies standard enterprise pill styling to a QTableWidgetItem.
    """
    bg_hex, fg_hex = get_status_colors(status)
    if text is not None:
        item.setText(text)
    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    item.setBackground(QColor(bg_hex))
    item.setForeground(QColor(fg_hex))
    font = item.font()
    font.setBold(True)
    item.setFont(font)


def create_status_badge_label(status: str, text: str = None) -> QLabel:
    """Creates a stylized pill badge QLabel for forms or table cell widgets."""
    bg_hex, fg_hex = get_status_colors(status)
    display_text = text if text is not None else status.upper()
    lbl = QLabel(display_text)
    lbl.setStyleSheet(
        f"background-color: {bg_hex}; color: {fg_hex}; "
        f"font-size: 11px; font-weight: 700; border-radius: 10px; "
        f"padding: 3px 10px; border: 1px solid {bg_hex};"
    )
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return lbl


def apply_enterprise_theme(target: QWidget = None):
    """
    Applies the enterprise stylesheet to a QApplication instance or specific top-level widget.
    """
    if target is None:
        target = QApplication.instance()
    if target:
        target.setStyleSheet(ENTERPRISE_QSS)
