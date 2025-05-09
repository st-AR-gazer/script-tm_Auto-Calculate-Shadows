import sys, os, ctypes, time, psutil
from pathlib import Path
from ctypes import wintypes
from PySide6.QtCore import Qt, QThread, Signal, QPoint, QPointF
from PySide6.QtGui import QGuiApplication, QFont, QColor
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QTextEdit,
    QProgressBar,
    QMessageBox,
    QGraphicsDropShadowEffect,
    QButtonGroup,
    QInputDialog,
    QSizePolicy,
)

from src import core

WIN_W, WIN_H = 560, 450
ACCENT = "#4da3ff"
BG = "#1e1e1e"
FG = "#e8e8e8"
FONT_FAMILY = "Segoe UI"
QUALITY_MAP = {
    "Very Fast": "VeryFast",
    "Fast": "Fast",
    "Default": "Default",
    "High": "High",
    "Ultra2": "Ultra2",
}


def qss() -> str:
    return f"""
        QWidget {{ background:{BG}; color:{FG}; font-family:{FONT_FAMILY}; font-size:11pt; border:none; border-radius:10px; }}
        QLineEdit {{ background:#2b2b2b; padding:6px 8px; border:1px solid #444; }}
        QPushButton {{ background:{ACCENT}; color:#fff; padding:6px 14px; border-radius:8px; }}
        QPushButton:disabled {{ background:#666; }}
        QPushButton[checkable="true"] {{ background:#333; border:1px solid #555; padding:4px 10px; }}
        QPushButton[checkable="true"]:checked {{ background:{ACCENT}; border:1px solid {ACCENT}; }}
        QProgressBar {{ background:#2b2b2b; border:none; height:10px; border-radius:5px; }}
        QProgressBar::chunk {{ background:{ACCENT}; border-radius:5px; }}
        QTextEdit {{ background:#1a1a1a; border:1px solid #333; }}
    """


class ScanWorker(QThread):
    folder_msg = Signal(str)
    drive_prog = Signal(str, int)
    finished = Signal(list)

    def run(self):
        DRIVE_FIXED = 3
        kernel = ctypes.windll.kernel32
        mask = kernel.GetLogicalDrives()
        results = []
        for letter in (chr(65 + i) for i in range(26)):
            if not mask & 1 << (ord(letter) - 65):
                continue
            drive = f"{letter}:\\"
            if kernel.GetDriveTypeW(drive) != DRIVE_FIXED:
                continue
            total = wintypes.ULARGE_INTEGER()
            free = wintypes.ULARGE_INTEGER()
            kernel.GetDiskFreeSpaceExW(
                ctypes.c_wchar_p(drive), None, ctypes.byref(total), ctypes.byref(free)
            )
            used = total.value - free.value if total.value else 0
            seen = 0
            last = 0.0
            for root, _, files in os.walk(drive, topdown=True):
                if time.time() - last > 0.05:
                    self.folder_msg.emit(root)
                    last = time.time()
                for f in files:
                    try:
                        seen += os.path.getsize(os.path.join(root, f))
                    except:
                        pass
                pct = min(100, int(seen * 100 / used)) if used else 0
                self.drive_prog.emit(letter, pct)
                if "Trackmania.exe" in files:
                    results.append(Path(root) / "Trackmania.exe")
            self.drive_prog.emit(letter, 100)
        self.finished.emit(results)


class RunWorker(QThread):
    error = Signal(str)

    def __init__(self, exe: Path, folder: str, quality: str):
        super().__init__()
        self.exe, self.folder, self.quality = exe, folder, quality

    def run(self):
        try:
            core.start_compute_shadows(self.exe, self.folder, self.quality)
        except Exception as exc:
            self.error.emit(str(exc))


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Trackmania – Shadow Calculator")
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(WIN_W, WIN_H)

        cont = QWidget(self)
        cont.setGeometry(0, 0, WIN_W, WIN_H)
        cont.setStyleSheet(qss())
        sh = QGraphicsDropShadowEffect(self)
        sh.setBlurRadius(22)
        sh.setOffset(QPointF(0, 0))
        sh.setColor(QColor(0, 0, 0, 160))
        cont.setGraphicsEffect(sh)
        v = QVBoxLayout(cont)
        v.setContentsMargins(24, 24, 24, 24)
        v.setSpacing(18)
        head = QLabel("Batch Calculate Shadows")
        head.setAlignment(Qt.AlignCenter)
        head.setStyleSheet("font-size:18pt;font-weight:bold;")
        v.addWidget(head)

        row = QHBoxLayout()
        row.addWidget(QLabel("Trackmania.exe"))
        self.tm_edit = QLineEdit(placeholderText="Choose or auto-detect…")
        row.addWidget(self.tm_edit, 1)
        row.addWidget(QPushButton("Browse…", clicked=self.browse_tm))
        row.addWidget(QPushButton("Auto", clicked=self.auto_scan))
        v.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Map folder"))
        self.map_edit = QLineEdit(placeholderText="e.g. WinterCampaign")
        row.addWidget(self.map_edit, 1)
        row.addWidget(QPushButton("Browse…", clicked=self.browse_maps))
        v.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Quality"))
        self.qual_grp = QButtonGroup(self)
        self.qual_grp.setExclusive(True)
        for txt in QUALITY_MAP:
            btn = QPushButton(txt, checkable=True)
            self.qual_grp.addButton(btn)
            row.addWidget(btn)
            if txt == "High":
                btn.setChecked(True)
        v.addLayout(row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.run_btn = QPushButton("Calculate Shadows", clicked=self.run)
        self.run_btn.setFixedHeight(36)
        self.run_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn_row.addWidget(self.run_btn, 1)

        self.close_btn = QPushButton("Close", clicked=self.close)
        self.close_btn.setFixedHeight(30)
        self.close_btn.setFixedWidth(80)
        self.close_btn.setStyleSheet(
            "background:#555;" "color:#fff;" "padding:4px 10px;" "border-radius:8px;"
        )
        btn_row.addWidget(self.close_btn)

        v.addLayout(btn_row)

        self.busy = QProgressBar()
        self.busy.setRange(0, 0)
        self.busy.hide()
        v.addWidget(self.busy)

        self.log = QTextEdit(readOnly=True)
        self.log.hide()
        v.addWidget(self.log, 1)
        self.drive_box = QVBoxLayout()
        v.addLayout(self.drive_box)
        self.drive_rows: dict[str, tuple[QLabel, QProgressBar]] = {}

        self.interactive = [
            self.tm_edit,
            self.map_edit,
            self.run_btn,
            *self.qual_grp.buttons(),
        ]
        self._drag = None
        saved = core.load_saved_tm_path()
        if saved and saved.exists():
            self.tm_edit.setText(str(saved))

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag = e.position().toPoint()

    def mouseMoveEvent(self, e):
        if self._drag:
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, _):
        self._drag = None

    def browse_tm(self):
        p, _ = QFileDialog.getOpenFileName(
            self, "Select Trackmania.exe", "C:\\", "Executable (*.exe)"
        )
        if p:
            self.tm_edit.setText(p)
            core.save_tm_path(Path(p))

    def browse_maps(self):
        docs = Path.home() / "Documents"
        base = docs / "Trackmania2020/Maps"
        if not base.exists():
            base = docs / "Trackmania/Maps"
        folder = QFileDialog.getExistingDirectory(self, "Select Map folder", str(base))
        if folder:
            self.map_edit.setText(core.normalize_subfolder(folder))

    def _clear_drive_rows(self):
        for lbl, bar in self.drive_rows.values():
            lbl.deleteLater()
            bar.deleteLater()
        self.drive_rows.clear()

    def auto_scan(self):
        self._toggle(False)
        self.busy.show()
        self.log.clear()
        self.log.show()
        self._clear_drive_rows()
        self.scan = ScanWorker()
        self.scan.folder_msg.connect(self._log)
        self.scan.drive_prog.connect(self._drive)
        self.scan.finished.connect(self._scan_done)
        self.scan.start()

    def _log(self, t: str):
        self.log.append(t)
        self.log.ensureCursorVisible()

    def _drive(self, d: str, p: int):
        if d not in self.drive_rows:
            h = QHBoxLayout()
            lbl = QLabel(f"{d}:")
            bar = QProgressBar()
            bar.setRange(0, 100)
            h.addWidget(lbl)
            h.addWidget(bar, 1)
            self.drive_box.addLayout(h)
            self.drive_rows[d] = (lbl, bar)
        self.drive_rows[d][1].setValue(p)

    def _scan_done(self, found: list[Path]):
        self.busy.hide()
        self._toggle(True)
        self._clear_drive_rows()
        if not found:
            QMessageBox.warning(
                self, "Not found", "Trackmania.exe could not be located."
            )
            self.log.hide()
            return
        if len(found) == 1:
            self.tm_edit.setText(str(found[0]))
            core.save_tm_path(found[0])
            self.log.hide()
            return
        opts = [str(p) for p in found]
        idx, ok = QInputDialog.getInt(
            self,
            "Choose Trackmania.exe",
            "\n".join(f"{i+1}. {p}" for i, p in enumerate(opts)),
            1,
            1,
            len(opts),
        )
        if ok:
            self.tm_edit.setText(opts[idx - 1])
            core.save_tm_path(Path(opts[idx - 1]))
        self.log.hide()

    def run(self) -> None:
        exe = Path(self.tm_edit.text())
        if not exe.exists():
            QMessageBox.warning(
                self,
                "Missing path",
                "Choose a valid Trackmania.exe first.",
            )
            return

        folder = self.map_edit.text().strip()
        if not folder:
            QMessageBox.warning(
                self,
                "Missing name",
                "Enter the name of the folder to process.",
            )
            return

        quality = QUALITY_MAP[self.qual_grp.checkedButton().text()]

        core.save_tm_path(exe)

        self._toggle(False)
        self.busy.show()

        self.runwork = RunWorker(exe, folder, quality)
        self.runwork.finished.connect(self._done)
        self.runwork.error.connect(lambda msg: QMessageBox.critical(self, "Error", msg))
        self.runwork.start()

    def _done(self):
        self.busy.hide()
        self._toggle(True)
        QMessageBox.information(
            self, "Finished", "Shadow calculation exited."
        )

    def _toggle(self, on: bool):
        for w in self.interactive:
            w.setEnabled(on)


def launch():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont(FONT_FAMILY, 11))
    w = MainWindow()
    geo = QGuiApplication.primaryScreen().availableGeometry()
    w.move(geo.center() - QPoint(WIN_W // 2, WIN_H // 2))
    w.show()
    sys.exit(app.exec())
