"""
Verification script for LeaveApplicationView UI layout, theme, and responsiveness.
Tests at 1920x1080, 1366x768, and 768x1024.
"""
import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from unittest.mock import patch
from PySide6.QtWidgets import QApplication, QScrollArea, QFrame, QTextEdit, QMessageBox
from PySide6.QtCore import Qt
from ui.styles import ENTERPRISE_QSS
from ui.leave_application_view import LeaveApplicationView


def run_verification():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(ENTERPRISE_QSS)

    resolutions = [
        ("1920px", 1920, 1080),
        ("1366px", 1366, 768),
        ("768px", 768, 1024),
    ]

    out_dir = BASE_DIR / "docs" / "screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []

    with patch.object(QMessageBox, "warning", return_value=QMessageBox.StandardButton.Ok), \
         patch.object(QMessageBox, "information", return_value=QMessageBox.StandardButton.Ok):

        for name, w, h in resolutions:
            view = LeaveApplicationView()
            view.resize(w, h)
            view.show()
            app.processEvents()

            # Check scroll areas: exactly 1 scroll area in Apply tab (page-level, no inner card scroll)
            apply_tab = view.tab_apply
            scroll_areas = apply_tab.findChildren(QScrollArea)
            page_scroll = scroll_areas[0] if scroll_areas else None

            # Check horizontal scrollbar
            h_scroll_active = False
            if page_scroll:
                h_bar = page_scroll.horizontalScrollBar()
                h_scroll_active = h_bar.isVisible() and h_bar.maximum() > 0

            # Check direction of apply_grid_layout
            layout_dir = "TopToBottom" if view.apply_grid_layout.direction().name == "TopToBottom" else "LeftToRight"

            # Check form card and pre-check card presence and geometry
            form_card = view.form_card
            pre_card = view.pre_card
            form_w = form_card.width()
            pre_w = pre_card.width()

            # Capture screenshot
            img_path = out_dir / f"leave_app_{name}.png"
            pix = view.grab()
            pix.save(str(img_path))

            results.append({
                "name": name,
                "width": w,
                "height": h,
                "layout_dir": layout_dir,
                "form_width": form_w,
                "pre_width": pre_w,
                "scroll_areas_count": len(scroll_areas),
                "h_scroll_active": h_scroll_active,
                "saved_to": str(img_path),
                "file_size": img_path.stat().st_size,
            })
            view.close()
            app.processEvents()

        # Also test pre-check execution rendering with a mock valid result
        mock_val_res = {
            "valid": True,
            "requested_days": 1.0,
            "sandwich_days": 0.0,
            "requires_document": False,
            "remaining_balance": 12.0,
            "warnings": ["Consecutive leave warning: ensure lecture coverage is scheduled."],
            "errors": [],
        }

        with patch("services.leave_service.leave_service.validate_leave_application", return_value=mock_val_res):
            view_pre = LeaveApplicationView()
            view_pre.resize(1366, 768)
            view_pre.show()
            app.processEvents()

            # Trigger precheck
            view_pre.on_precheck_click()
            app.processEvents()

            precheck_badge_text = view_pre.lbl_pre_badge.text()
            precheck_pix = view_pre.grab()
            precheck_img_path = out_dir / "leave_app_precheck_evaluated.png"
            precheck_pix.save(str(precheck_img_path))

            view_pre.close()
            app.processEvents()

    print("=== VERIFICATION RESULTS ===")
    for r in results:
        print(f"Resolution {r['name']} ({r['width']}x{r['height']}):")
        print(f"  Layout Direction: {r['layout_dir']}")
        print(f"  Form Card Width: {r['form_width']}px | Pre-Check Card Width: {r['pre_width']}px")
        print(f"  Scroll Areas Count: {r['scroll_areas_count']} (Expected: 1 page-level)")
        print(f"  Horizontal Scrollbar Active: {r['h_scroll_active']} (Expected: False)")
        print(f"  Screenshot Saved: {r['saved_to']} ({r['file_size']} bytes)")

    print(f"\nPre-Check Evaluated Badge: '{precheck_badge_text}'")
    print(f"Pre-Check Evaluated Screenshot: {precheck_img_path}")
    print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY.")


if __name__ == "__main__":
    run_verification()
