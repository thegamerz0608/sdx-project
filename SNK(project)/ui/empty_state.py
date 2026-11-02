"""
Modern Empty State Component (PySide6)
Renders a polished, friendly placeholder when tables, rosters, or query results are empty,
preventing stark blank grids and guiding user actions.
"""
from typing import Optional, Callable
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QSizePolicy,
)
from PySide6.QtGui import QFont


class EmptyStateWidget(QFrame):
    """
    Enterprise Empty State Container.
    Features centered icon/graphic, bold title, descriptive subtitle,
    and an optional call-to-action button.
    """

    def __init__(
        self,
        icon: str = "🔍",
        title: str = "No Records Found",
        message: str = "There are currently no records matching your active filters.",
        action_text: Optional[str] = None,
        action_callback: Optional[Callable] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setObjectName("emptyStateWidget")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet(
            """
            #emptyStateWidget {
                background-color: #FFFFFF;
                border: 1.5px dashed #CBD5E1;
                border-radius: 12px;
                padding: 32px 20px;
            }
            #emptyStateIcon {
                font-size: 42px;
                color: #64748B;
            }
            #emptyStateTitle {
                font-size: 17px;
                font-weight: 700;
                color: #1E293B;
                margin-top: 6px;
            }
            #emptyStateMessage {
                font-size: 13px;
                color: #64748B;
                line-height: 1.4;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(8)

        # 1. Icon Label
        self.lbl_icon = QLabel(icon)
        self.lbl_icon.setObjectName("emptyStateIcon")
        self.lbl_icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_icon)

        # 2. Title Label
        self.lbl_title = QLabel(title)
        self.lbl_title.setObjectName("emptyStateTitle")
        self.lbl_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_title)

        # 3. Message / Subtext
        self.lbl_message = QLabel(message)
        self.lbl_message.setObjectName("emptyStateMessage")
        self.lbl_message.setAlignment(Qt.AlignCenter)
        self.lbl_message.setWordWrap(True)
        self.lbl_message.setMaximumWidth(420)
        layout.addWidget(self.lbl_message)

        # 4. Optional Call-To-Action Button
        self.btn_action = QPushButton(action_text or "Refresh")
        self.btn_action.setFixedWidth(160)
        self.btn_action.setCursor(Qt.PointingHandCursor)
        self.btn_action.setStyleSheet(
            "background-color: #2563EB; color: #FFFFFF; font-weight: 600; padding: 8px 14px; border-radius: 6px;"
        )
        if action_callback:
            self.btn_action.clicked.connect(action_callback)
        self.btn_action.setVisible(bool(action_text))
        layout.addWidget(self.btn_action, alignment=Qt.AlignCenter)

    def set_state(
        self,
        icon: str,
        title: str,
        message: str,
        action_text: Optional[str] = None,
        action_callback: Optional[Callable] = None,
    ):
        """Dynamically updates the displayed icon, title, message, and action."""
        self.lbl_icon.setText(icon)
        self.lbl_title.setText(title)
        self.lbl_message.setText(message)

        if action_text:
            self.btn_action.setText(action_text)
            self.btn_action.setVisible(True)
            if action_callback:
                try:
                    self.btn_action.clicked.disconnect()
                except Exception:
                    pass
                self.btn_action.clicked.connect(action_callback)
        else:
            self.btn_action.setVisible(False)

    @property
    def has_action_button(self) -> bool:
        """Returns True if the action button is active/visible in the layout."""
        return not self.btn_action.isHidden()
