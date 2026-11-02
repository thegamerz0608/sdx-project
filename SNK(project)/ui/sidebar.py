"""
Modern Collapsible Navigation Sidebar for Faculty ERP.
Supports smooth animated collapsing, dynamic Role-Based Access Control (RBAC),
and active tab synchronization.
"""
from typing import List, Dict
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QScrollArea, QWidget
)


class SidebarNavButton(QPushButton):
    """Modern navigation button with icon, label, badge count, and active selection state."""

    def __init__(self, tab_index: int, label: str, icon_symbol: str, parent=None):
        super().__init__(parent)
        self.tab_index = tab_index
        self.label_text = label
        self.icon_symbol = icon_symbol
        self.badge_count = 0
        self.setCheckable(True)
        self.setFixedHeight(40)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("sidebarNavButton")
        self.update_display(collapsed=False)

    def set_badge_count(self, count: int, collapsed: bool = False):
        self.badge_count = max(0, int(count or 0))
        self.update_display(collapsed)

    def update_display(self, collapsed: bool):
        badge_str = f" ({self.badge_count})" if self.badge_count > 0 else ""
        if collapsed:
            self.setText(self.icon_symbol)
            self.setToolTip(f"{self.label_text}{badge_str}")
        else:
            self.setText(f"  {self.icon_symbol}   {self.label_text}{badge_str}")
            self.setToolTip("")


class Sidebar(QFrame):
    """
    Animated collapsible left sidebar that dynamically reconfigures
    navigation items according to the active user's RBAC role.
    """
    tab_selected = Signal(int)       # Emits target tab index
    auth_action_clicked = Signal()   # Emits when login/logout button is clicked

    # Navigation mapping: (tab_index, label, icon)
    # Mapping matches the 16 core views in MainWindow
    NAV_DEFINITIONS = [
        (0, "System Dashboard", "📊"),
        (1, "Faculty Roster", "👨‍🏫"),
        (2, "Department Management", "🏢"),
        (3, "Attendance Management", "⏱️"),
        (4, "Grace Policy Engine", "⏳"),
        (5, "Leave Policies && Rules", "📜"),
        (6, "Leave Applications", "📝"),
        (7, "Substitute Management", "🤝"),
        (8, "NLP Leave Classifier", "🧠"),
        (9, "TF-IDF Feature Matrix", "📈"),
        (10, "ML Classifier Studio", "🔬"),
        (11, "AI Recommendation Engine", "⚡"),
        (12, "Attendance Analytics", "📉"),
        (13, "Automated Reports", "📄"),
        (14, "Audit && Security Logs", "🛡️"),
        (15, "System Maintenance", "💾"),
        (16, "Lab Instructors", "🔬"),
        (17, "Student Directory", "🎓"),
        (18, "Multi-Stage Leave Review", "⚖️"),
        (19, "Student Marks Entry", "📊"),
        (20, "Stationery Requests", "📦"),
        (21, "Profile Approvals", "🛡️"),
    ]

    # Role Visibility filters (Indices of views visible to each role)
    # Strict Restriction: Tab 14 (Audit) and Tab 15 (Maintenance) strictly ADMIN only
    ROLE_PERMISSIONS = {
        "ADMIN": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21],  # Full institutional access
        "HOD": [0, 1, 3, 4, 6, 7, 11, 12, 13, 16, 17, 19, 20],                                     # Departmental leadership & students
        "FACULTY": [0, 3, 4, 6, 7, 17, 19, 20],                                                     # Faculty portal + Marks & Stationery
        "LAB_INSTRUCTOR": [0, 3, 4, 6, 17, 19, 20],                                                 # Lab Instructor portal + Marks & Stationery
        "HR": [0, 1, 3, 4, 6, 13, 16, 17, 18, 19, 20, 21],                                          # HR leave review, roster, profile approvals, students
        "PRINCIPAL": [0, 1, 2, 3, 6, 12, 13, 17, 18, 19, 20, 21],                                   # Executive oversight, final approvals, analytics
        "GUEST": [0],                                                                               # Unauthenticated landing view
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("modernSidebar")
        self.setFixedWidth(240)
        self.is_collapsed = False
        self.buttons: List[SidebarNavButton] = []
        self.current_role = "GUEST"

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 14, 10, 14)
        main_layout.setSpacing(6)

        # 1. Header with Hamburger Toggle
        header_row = QHBoxLayout()
        self.btn_toggle = QPushButton("☰")
        self.btn_toggle.setObjectName("sidebarToggle")
        self.btn_toggle.setFixedSize(36, 36)
        self.btn_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_toggle.clicked.connect(self.toggle_collapse)
        header_row.addWidget(self.btn_toggle)

        self.lbl_brand = QLabel("Faculty ERP")
        self.lbl_brand.setObjectName("sidebarBrand")
        header_row.addWidget(self.lbl_brand)
        header_row.addStretch()
        main_layout.addLayout(header_row)

        main_layout.addSpacing(6)

        # 2. Scrollable Navigation Menu
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("sidebarScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("border: none; background: transparent;")

        self.menu_widget = QWidget()
        self.menu_widget.setStyleSheet("background: transparent;")
        self.menu_layout = QVBoxLayout(self.menu_widget)
        self.menu_layout.setContentsMargins(0, 0, 0, 0)
        self.menu_layout.setSpacing(4)
        self.scroll_area.setWidget(self.menu_widget)

        main_layout.addWidget(self.scroll_area, stretch=1)

        # 3. Bottom Auth Button
        self.btn_auth = QPushButton("🔑  Log In / Switch")
        self.btn_auth.setObjectName("sidebarAuthBtn")
        self.btn_auth.setFixedHeight(38)
        self.btn_auth.setCursor(Qt.PointingHandCursor)
        self.btn_auth.clicked.connect(self.auth_action_clicked.emit)
        main_layout.addWidget(self.btn_auth)

    def set_role(self, role: str):
        """Re-renders sidebar navigation buttons matching the active user role."""
        self.current_role = role.upper()
        allowed_indices = self.ROLE_PERMISSIONS.get(self.current_role, self.ROLE_PERMISSIONS["GUEST"])

        # Clear existing buttons
        for btn in self.buttons:
            self.menu_layout.removeWidget(btn)
            btn.deleteLater()
        self.buttons.clear()

        # Rebuild navigation
        for idx, label, icon in self.NAV_DEFINITIONS:
            if idx in allowed_indices:
                btn = SidebarNavButton(idx, label, icon)
                btn.clicked.connect(lambda checked, i=idx: self._on_button_clicked(i))
                btn.update_display(self.is_collapsed)
                self.menu_layout.addWidget(btn)
                self.buttons.append(btn)

        self.menu_layout.addStretch()

        if self.buttons:
            self.select_tab(self.buttons[0].tab_index)

    def _on_button_clicked(self, tab_index: int):
        self.select_tab(tab_index)
        self.tab_selected.emit(tab_index)

    def select_tab(self, tab_index: int):
        """Visually marks the button for the active tab index as checked."""
        for btn in self.buttons:
            btn.setChecked(btn.tab_index == tab_index)

    def update_badge(self, tab_index: int, count: int):
        """Updates the numerical notification badge on a specific navigation button."""
        for btn in self.buttons:
            if btn.tab_index == tab_index:
                btn.set_badge_count(count, self.is_collapsed)
                break

    def update_auth_button_text(self, is_authenticated: bool):
        if is_authenticated:
            self.btn_auth.setText("🚪" if self.is_collapsed else "🚪  Logout / Switch")
        else:
            self.btn_auth.setText("🔑" if self.is_collapsed else "🔑  Log In")

    def toggle_collapse(self):
        """Animates sidebar width smoothly between expanded (240px) and compact (68px)."""
        target_width = 68 if not self.is_collapsed else 240

        self.anim = QPropertyAnimation(self, b"maximumWidth")
        self.anim.setDuration(160)
        self.anim.setStartValue(self.width())
        self.anim.setEndValue(target_width)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.start()

        self.setMinimumWidth(target_width)
        self.is_collapsed = not self.is_collapsed
        self.lbl_brand.setVisible(not self.is_collapsed)

        for btn in self.buttons:
            btn.update_display(self.is_collapsed)

        self.update_auth_button_text("Logout" in self.btn_auth.text() or "🚪" in self.btn_auth.text())
