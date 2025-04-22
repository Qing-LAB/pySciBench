from PyQt6.QtWidgets import (
    QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QToolBar, QFileDialog,
    QAction, QMainWindow, QMenuBar, QMenu
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
import os

class PlotWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Plot Viewer")
        self.setGeometry(200, 200, 900, 700)
        self.setWindowFlags(
            Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint
        )

        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        self._figures = []  # Keep track of figures
        self._setup_menu()

    def _setup_menu(self):
        # Menu bar and File > Save actions
        menubar = QMenuBar(self)
        file_menu = QMenu("File", self)

        self.save_png_action = QAction("Save as PNG", self)
        self.save_svg_action = QAction("Save as SVG", self)
        self.save_pdf_action = QAction("Save as PDF", self)

        self.save_png_action.triggered.connect(lambda: self._save_current_figure("png"))
        self.save_svg_action.triggered.connect(lambda: self._save_current_figure("svg"))
        self.save_pdf_action.triggered.connect(lambda: self._save_current_figure("pdf"))

        file_menu.addAction(self.save_png_action)
        file_menu.addAction(self.save_svg_action)
        file_menu.addAction(self.save_pdf_action)
        menubar.addMenu(file_menu)

        self.setMenuBar(menubar)

    def add_figure(self, fig: Figure):
        canvas = FigureCanvasQTAgg(fig)
        toolbar = NavigationToolbar2QT(canvas, self)

        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        layout.addWidget(toolbar)
        layout.addWidget(canvas)
        container.setLayout(layout)

        index = len(self._figures) + 1
        tab_name = f"Figure {index}"
        self.tab_widget.addTab(container, tab_name)

        self._figures.append((fig, canvas))
        self.tab_widget.setCurrentIndex(self.tab_widget.count() - 1)

        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _save_current_figure(self, fmt: str):
        current_index = self.tab_widget.currentIndex()
        if current_index < 0 or current_index >= len(self._figures):
            return

        fig, _ = self._figures[current_index]
        default_name = f"figure_{current_index + 1}.{fmt}"
        file_path, _ = QFileDialog.getSaveFileName(
            self, f"Save as {fmt.upper()}", default_name, f"*.{fmt}"
        )
        if file_path:
            fig.savefig(file_path, format=fmt)
