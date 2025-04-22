from PyQt6.QtWidgets import (
    QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QToolBar, QFileDialog,
    QMainWindow, QMenuBar, QMenu, QMessageBox
)
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import Qt, pyqtSignal
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import os

class PlotWindow(QMainWindow):
    figure_switched = pyqtSignal(int)  # Emit figure number on tab change

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Plot Viewer")
        self.setGeometry(200, 200, 900, 700)
        self.setWindowFlags(
            Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint
        )

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.setCentralWidget(self.tab_widget)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        self.tab_widget.tabCloseRequested.connect(self._on_tab_close_requested)

        self._figures = []  # List of tuples: (fig_num, Figure, canvas, toolbar)
        self._closed_figures = set()  # Track closed figures
        self._setup_menu()

    def _setup_menu(self):
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

    def has_figure(self, fig_num: int) -> bool:
        return any(fnum == fig_num for fnum, _, _, _ in self._figures)

    def add_figure(self, fig: Figure) -> bool:
        fig_num = fig.number
        if self.has_figure(fig_num):
            return False  # Already exists, handled elsewhere

        canvas = FigureCanvasQTAgg(fig)
        toolbar = NavigationToolbar2QT(canvas, self)

        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        layout.addWidget(toolbar)
        layout.addWidget(canvas)
        container.setLayout(layout)

        tab_name = f"Figure {fig_num}"
        self.tab_widget.addTab(container, tab_name)
        self._figures.append((fig_num, fig, canvas, toolbar))
        self.tab_widget.setCurrentIndex(self.tab_widget.count() - 1)

        return True

    def refresh_figure_tab(self, fig: Figure):
        fig_num = fig.number
        for i, (fnum, _, old_canvas, old_toolbar) in enumerate(self._figures):
            if fnum == fig_num:
                new_canvas = FigureCanvasQTAgg(fig)
                new_toolbar = NavigationToolbar2QT(new_canvas, self)

                tab_widget = self.tab_widget.widget(i)
                layout = tab_widget.layout()

                # Disconnect the old toolbar safely to avoid runtime errors
                if old_toolbar:
                    old_toolbar.setParent(None)
                    old_toolbar.deleteLater()
                if old_canvas:
                    old_canvas.setParent(None)
                    old_canvas.deleteLater()

                layout.addWidget(new_toolbar)
                layout.addWidget(new_canvas)

                self._figures[i] = (fig_num, fig, new_canvas, new_toolbar)
                new_canvas.draw()
                break

    def _save_current_figure(self, fmt: str):
        current_index = self.tab_widget.currentIndex()
        if current_index < 0 or current_index >= len(self._figures):
            return

        fig_num, fig, _, _ = self._figures[current_index]
        default_name = f"figure_{fig_num}.{fmt}"
        file_path, _ = QFileDialog.getSaveFileName(
            self, f"Save as {fmt.upper()}", default_name, f"*.{fmt}"
        )
        if file_path:
            fig.savefig(file_path, format=fmt)

    def _on_tab_changed(self, index):
        if 0 <= index < len(self._figures):
            fig_num, _, _, _ = self._figures[index]
            if fig_num not in self._closed_figures:
                self.figure_switched.emit(fig_num)

    def _on_tab_close_requested(self, index):
        if 0 <= index < len(self._figures):
            widget = self.tab_widget.widget(index)
            self.tab_widget.removeTab(index)
            if widget:
                widget.deleteLater()

    def get_active_figure(self):
        index = self.tab_widget.currentIndex()
        if 0 <= index < len(self._figures):
            fig_num, fig, _, _ = self._figures[index]
            if fig_num not in self._closed_figures:
                return fig
        return None

    def get_active_figure_num(self):
        index = self.tab_widget.currentIndex()
        if 0 <= index < len(self._figures):
            fig_num, _, _, _ = self._figures[index]
            if fig_num not in self._closed_figures:
                return fig_num
        return None

    def mark_figure_closed(self, fig_num: int):
        self._closed_figures.add(fig_num)
