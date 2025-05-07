from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QPoint, QPointF
from PySide6.QtGui import QGuiApplication, QFont, QColor
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QFileDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QProgressBar,
    QGraphicsDropShadowEffect,
    QButtonGroup,
)

from src import core

# Fixed logical size
WIN_W, WIN_H = 560, 420

# Style constants
CORNER_RADIUS = 10
BORDER_WIDTH = 1
SHADOW_BLUR = 22
ACCENT = "#4da3ff"
BG = "#1e1e1e"
FG = "#e8e8e8"
FONT_FAMILY = "Segoe UI"
FONT_SIZE = 11

QUALITY_MAP = {
    "Very Fast": "VeryFast",
    "Fast": "Fast",
    "Default": "Default",
    "High": "High",
    "Ultra2": "Ultra2",
}


def qss() -> str:
    return f"""
        QWidget {{ background:{BG}; color:{FG}; font-family:{FONT_FAMILY};
                  font-size:{FONT_SIZE}pt; border:none;
                  border-radius:{CORNER_RADIUS}px; }}
        QLineEdit {{ background:#2b2b2b; padding:6px 8px;
                     border:{BORDER_WIDTH}px solid #444; }}
        QPushButton {{ background:{ACCENT}; color:#fff; padding:6px 14px;
                       border-radius:{CORNER_RADIUS-2}px; }}
        QPushButton:disabled {{ background:#666; }}
        QPushButton[checkable="true"] {{ background:#333; border:1px solid #555;
                                         padding:4px 10px; }}
        QPushButton[checkable="true"]:checked {{ background:{ACCENT};
                                                border:1px solid {ACCENT}; }}
        QProgressBar {{ background:#2b2b2b; border:none; height:10px;
                        border-radius:5px; }}
        QProgressBar::chunk {{ background:{ACCENT}; border-radius:5px; }}
    """


class Worker(QThread):
    finished = Signal()

    def __init__(self, tm: Path, folder: str, quality: str):
        super().__init__()
        self.tm, self.folder, self.quality = tm, folder, quality

    def run(self):
        core.start_compute_shadows(self.tm, self.folder, self.quality)
        self.finished.emit()


# --- Main window ----------------------------------------
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Trackmania – Shadow Calculator")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.setFixedSize(WIN_W, WIN_H)

        self.container = QWidget(self)
        self.container.setStyleSheet(qss())
        self.container.setGeometry(0, 0, WIN_W, WIN_H)
        self._apply_shadow()

        v = QVBoxLayout(self.container)
        v.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Batch Calculate Shadows")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:18pt; font-weight:bold;")
        title.setFixedHeight(30)
        v.addWidget(title)

        row = QHBoxLayout()
        row.addWidget(QLabel("Trackmania.exe"))
        self.tm_edit = QLineEdit(placeholderText="Choose or auto-detect…")
        row.addWidget(self.tm_edit, 1)
        row.addWidget(QPushButton("Browse…", clicked=self.browse_tm))
        row.addWidget(QPushButton("Auto", clicked=self.auto_detect))
        v.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Map folder"))
        self.map_edit = QLineEdit(placeholderText="e.g. WinterCampaign")
        row.addWidget(self.map_edit, 1)
        v.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Quality"))
        self.qual_group = QButtonGroup(self)
        self.qual_group.setExclusive(True)
        for txt in QUALITY_MAP:
            b = QPushButton(txt, checkable=True)
            self.qual_group.addButton(b)
            row.addWidget(b)
            if txt == "High":
                b.setChecked(True)
        v.addLayout(row)

        self.run_btn = QPushButton("Compute Shadows", clicked=self.run)
        self.run_btn.setFixedHeight(36)
        v.addWidget(self.run_btn)

        row_close = QHBoxLayout()
        row_close.setContentsMargins(0, 0, 0, 0)
        row_close.addStretch()
        close_btn = QPushButton("Close", clicked=self.close)
        close_btn.setFixedHeight(30)
        close_btn.setStyleSheet(
            "color:#888; background:#2b2b2b; border:1px solid #444; border-radius:4px;"
        )
        row_close.addWidget(close_btn)
        v.addLayout(row_close)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        v.addWidget(self.progress)

        self._drag_off: QPoint | None = None

        if saved := core.load_saved_tm_path():
            self.tm_edit.setText(str(saved))

    def _apply_shadow(self):
        eff = QGraphicsDropShadowEffect(self)
        eff.setBlurRadius(SHADOW_BLUR)
        eff.setOffset(QPointF(0, 0))
        eff.setColor(QColor(0, 0, 0, 160))
        self.container.setGraphicsEffect(eff)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_off = e.position().toPoint()

    def mouseMoveEvent(self, e):
        if self._drag_off:
            self.move(e.globalPosition().toPoint() - self._drag_off)

    def mouseReleaseEvent(self, _):
        self._drag_off = None

    def browse_tm(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Select Trackmania.exe", "C:\\", "Executable (*.exe)"
        )
        if file:
            self.tm_edit.setText(file)

    def auto_detect(self):
        self.setDisabled(True)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        found = core.brute_force_search()
        QApplication.restoreOverrideCursor()
        self.setDisabled(False)

        if not found:
            QMessageBox.warning(
                self, "Not found", "Trackmania.exe could not be located."
            )
            return
        if len(found) == 1:
            self.tm_edit.setText(str(found[0]))
            return
        choice, ok = QFileDialog.getOpenFileName(
            self,
            "Multiple copies found – choose one",
            str(found[0].parent),
            "Executable (*.exe)",
        )
        if ok:
            self.tm_edit.setText(choice)

    def run(self):
        try:
            core.running_inside_maps_folder()
        except ValueError as err:
            QMessageBox.critical(self, "Wrong folder", str(err))
            return

        tm_path = Path(self.tm_edit.text())
        if not tm_path.exists():
            QMessageBox.warning(
                self, "Missing path", "Choose a valid Trackmania.exe first."
            )
            return

        map_sub = self.map_edit.text().strip()
        if not map_sub:
            QMessageBox.warning(
                self, "Missing name", "Enter the name of the folder to process."
            )
            return

        quality_cli = QUALITY_MAP[self.qual_group.checkedButton().text()]
        core.save_tm_path(tm_path)

        self.run_btn.setDisabled(True)
        self.progress.show()
        self.worker = Worker(tm_path, map_sub, quality_cli)
        self.worker.finished.connect(self.done)
        self.worker.start()

    def done(self):
        self.progress.hide()
        self.run_btn.setDisabled(False)
        QMessageBox.information(
            self, "Finished", "Shadow calculation completed successfully."
        )


def launch():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont(FONT_FAMILY, FONT_SIZE))

    w = MainWindow()
    scr_geo = QGuiApplication.primaryScreen().availableGeometry()
    w.move(scr_geo.center() - QPoint(WIN_W // 2, WIN_H // 2))
    w.show()
    sys.exit(app.exec())
