"""
Reusable Concurrency Worker and Loading Overlay for PySide6 GUI.
Adheres strictly to the Qt moveToThread worker-object pattern.
Prevents GUI freezing during heavy operations (ML training, database imports/dumps, CSV ingestion, substitute search).
"""
from typing import Callable, Any, Optional
import traceback
from PySide6.QtCore import Qt, QThread, QObject, Signal, Slot, QEvent
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QProgressBar, QPushButton
from PySide6.QtGui import QPainter, QColor


class WorkerSignals(QObject):
    """Signals for background worker execution."""
    progress = Signal(int, str)      # percentage (0-100), status message
    result = Signal(object)          # return value from target func
    error = Signal(str)              # exception traceback or error string
    finished = Signal()              # worker execution completion


class WorkerObject(QObject):
    """
    Dedicated QObject worker designed for moveToThread execution.
    Never subclasses QThread; encapsulates task logic and cancellation state cleanly.
    """
    def __init__(self, target_func: Callable, *args, **kwargs):
        super().__init__()
        self._target_func = target_func
        self._args = args
        self._kwargs = kwargs
        self.signals = WorkerSignals()
        self._is_stopped = False

    @Slot()
    def do_work(self):
        """Executes the workload inside the worker thread."""
        try:
            if not self._is_stopped:
                res = self._target_func(*self._args, **self._kwargs)
                if not self._is_stopped:
                    self.signals.result.emit(res)
        except Exception as exc:
            if not self._is_stopped:
                self.signals.error.emit(traceback.format_exc())
        finally:
            self.signals.finished.emit()
            cur_thread = QThread.currentThread()
            if cur_thread:
                cur_thread.quit()

    def stop(self):
        """Flags cancellation so pending results or errors are suppressed."""
        self._is_stopped = True


class WorkerThread(QObject):
    """
    Worker-object concurrency wrapper adhering to the Qt moveToThread pattern.
    Provides a drop-in replacement for QThread subclasses with robust thread safety.
    """
    progress = Signal(int, str)
    result = Signal(object)
    error = Signal(str)
    finished = Signal()

    def __init__(self, target_func: Callable, *args, **kwargs):
        super().__init__()
        self._thread = QThread()
        self._worker = WorkerObject(target_func, *args, **kwargs)
        self._worker.moveToThread(self._thread)

        # Forward worker signals to public wrapper signals
        self._worker.signals.progress.connect(self.progress)
        self._worker.signals.result.connect(self.result)
        self._worker.signals.error.connect(self.error)
        self._worker.signals.finished.connect(self.finished)

        # Wire lifecycle
        self._thread.started.connect(self._worker.do_work)
        self._worker.signals.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup)

    def _cleanup(self):
        self._worker.deleteLater()
        self._thread.deleteLater()

    def start(self):
        """Starts the underlying QThread."""
        self._thread.start()

    def stop(self):
        """Stops the worker and quits the thread."""
        self._worker.stop()
        if self._thread.isRunning():
            self._thread.quit()

    def quit(self):
        """Alias for stop()."""
        self.stop()

    def isRunning(self) -> bool:
        """Returns True if the thread is currently executing."""
        return self._thread.isRunning()

    def wait(self, timeout_ms: int = 5000) -> bool:
        """Blocks until the worker thread has finished, or timeout expires."""
        return self._thread.wait(timeout_ms)

    def deleteLater(self):
        """Schedules thread and worker cleanup."""
        self.stop()
        super().deleteLater()


class LoadingOverlay(QWidget):
    """
    Semi-transparent modal overlay with indeterminate progress animation
    and optional error/retry states for long-running tasks.
    Tracks parent resize events automatically via eventFilter.
    """

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.hide()

        if parent:
            parent.installEventFilter(self)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        self.card = QFrame()
        self.card.setObjectName("loadingCard")
        self.card.setFixedSize(360, 160)
        self.card.setStyleSheet("""
            #loadingCard {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 12px;
            }
            #loadingTitle {
                color: #FFFFFF;
                font-size: 15px;
                font-weight: 700;
            }
            #loadingSubtext {
                color: #94A3B8;
                font-size: 12px;
            }
            #errorSubtext {
                color: #F87171;
                font-size: 12px;
            }
            QProgressBar {
                background-color: #334155;
                border-radius: 3px;
                height: 6px;
            }
            QProgressBar::chunk {
                background-color: #38BDF8;
                border-radius: 3px;
            }
            QPushButton#btnOverlayRetry {
                background-color: #2563EB;
                color: white;
                font-weight: 600;
                border-radius: 5px;
                padding: 6px 16px;
            }
            QPushButton#btnOverlayClose {
                background-color: #475569;
                color: white;
                font-weight: 600;
                border-radius: 5px;
                padding: 6px 16px;
            }
        """)

        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(24, 20, 24, 20)
        self.card_layout.setSpacing(10)

        self.lbl_title = QLabel("Processing Task...")
        self.lbl_title.setObjectName("loadingTitle")
        self.lbl_title.setAlignment(Qt.AlignCenter)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate animation
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)

        self.lbl_subtext = QLabel("Please wait while the operation completes.")
        self.lbl_subtext.setObjectName("loadingSubtext")
        self.lbl_subtext.setAlignment(Qt.AlignCenter)
        self.lbl_subtext.setWordWrap(True)

        # Button row for error/retry state
        self.btn_row = QWidget()
        btn_layout = QHBoxLayout(self.btn_row)
        btn_layout.setContentsMargins(0, 5, 0, 0)
        btn_layout.setAlignment(Qt.AlignCenter)

        self.btn_retry = QPushButton("Retry")
        self.btn_retry.setObjectName("btnOverlayRetry")
        self.btn_close = QPushButton("Dismiss")
        self.btn_close.setObjectName("btnOverlayClose")
        self.btn_close.clicked.connect(self.hide)

        btn_layout.addWidget(self.btn_retry)
        btn_layout.addWidget(self.btn_close)
        self.btn_row.hide()

        self.card_layout.addWidget(self.lbl_title)
        self.card_layout.addWidget(self.progress_bar)
        self.card_layout.addWidget(self.lbl_subtext)
        self.card_layout.addWidget(self.btn_row)
        layout.addWidget(self.card)

        self._retry_callback: Optional[Callable] = None
        self.btn_retry.clicked.connect(self._on_retry_clicked)

    def eventFilter(self, obj, event):
        """Automatically keeps overlay geometry synchronised with parent widget."""
        if obj == self.parent() and event.type() in (QEvent.Type.Resize, QEvent.Type.Move):
            self.resize(obj.size())
        return super().eventFilter(obj, event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(15, 23, 42, 160))  # Slate dark backdrop

    def show_message(self, title: str, subtext: str = "Please wait..."):
        """Displays indeterminate progress loading modal."""
        self.lbl_title.setText(title)
        self.lbl_subtext.setText(subtext)
        self.lbl_subtext.setObjectName("loadingSubtext")
        self.progress_bar.show()
        self.btn_row.hide()
        if self.parent():
            self.resize(self.parent().size())
        self.show()
        self.raise_()

    def show_error(self, title: str, message: str, retry_callback: Optional[Callable] = None):
        """Displays error modal state with optional Retry action."""
        self.lbl_title.setText(title)
        self.lbl_subtext.setText(message)
        self.lbl_subtext.setObjectName("errorSubtext")
        self.progress_bar.hide()
        self._retry_callback = retry_callback
        if retry_callback:
            self.btn_retry.show()
        else:
            self.btn_retry.hide()
        self.btn_row.show()
        if self.parent():
            self.resize(self.parent().size())
        self.show()
        self.raise_()

    def _on_retry_clicked(self):
        cb = self._retry_callback
        self.hide()
        if cb:
            cb()

