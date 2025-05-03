import sys

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QApplication, QFileDialog, QListWidget,
                             QListWidgetItem, QMainWindow, QMenu, QMessageBox,
                             QTextEdit, QVBoxLayout, QWidget)


class FigureWindow(QMainWindow):
    """This window class shows one figure as a separate window. When the user
    closes the figure window, the parent will be notified to keep track of the
    status of individual figures.

    Args:
        parent : 
            parent window that will receive notification when the user closes
            the figure window.
    """
    def __init__(self, fig: Figure, parent=None):
        super().__init__(parent)
        self.fig = fig
        self.canvas = FigureCanvas(fig)
        self.setCentralWidget(self.canvas)
        self.setWindowTitle(f"Figure {fig.number}")
        self.setGeometry(300, 300, 600, 400)

    def closeEvent(self, event):
        try:
            if self.parent() is not None:
                if hasattr(self.parent(), 'notify_figure_window_closed'):
                    self.parent().notify_figure_window_closed(self.fig.number)
        except Exception as e:
            print("Error when FigureWindow try to invoke parent window notify_figure_window_closed() method.")
            print(e)
        finally:
            super().closeEvent(event)


# --- PlotWindow: main plot manager window ---
class PlotWindow(QMainWindow):
    """This is the Matplotlib figure manager. Overall it will list the existing 
    matplotlib.pyplot figures, and display the info associated with each figure.
    For listed figures, if the figure has been closed by the function call 
    plt.close(), the status will be shown as (closed). Otherwise the figure
    will be marked as not closed. When clicking the figure that is not closed, 
    a call to plt.figure(fig_num) will be made such that the later call to 
    pyplot functions will modify this "active" figure.
    Double click the figure will bring up the figure as a separate window.
    In addition, the window provides save function to export the figure into 
    PNG, PDF or SVG formats.

    Args:
        parent : 
            give the parent object for this window.
        allow_full_close : 
            if True, when the user clicks the close button of the window,
            the window will be closed. Otherwise, the window will only
            hide and the parent/user can bring the window shown/active again
            later by calling the function show_window()        

    """
    figure_switched = pyqtSignal(int)

    def __init__(self, parent=None, allow_full_close=False):
        super().__init__(parent)
        self.setWindowTitle("Plot Manager")
        self.setGeometry(100, 100, 400, 600)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)

        self.allow_full_close = allow_full_close

        self.list_widget = QListWidget()
        self.info_window = QTextEdit()
        self.info_window.setReadOnly(True)

        layout = QVBoxLayout()
        layout.addWidget(self.list_widget)
        layout.addWidget(self.info_window)

        main_widget = QWidget()
        main_widget.setLayout(layout)
        self.setCentralWidget(main_widget)

        self.figure_info_list = list()
        self.figure_windows = {}  # fig_num -> FigureWindow
        self.figures_status = {}  # fig_num -> bool (open/closed)
        self.figures_refs = {}  # fig_num -> Figure
        self.active_figure_num = None

        self.list_widget.itemClicked.connect(self._on_figure_selected)
        self.list_widget.itemDoubleClicked.connect(self._on_figure_double_clicked)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._open_context_menu)

    def update_figure_info_list(self):
        try:
            all_figure_num_list = plt.get_fignums()
            current_active_figure = plt.gcf()

            for fig_num in all_figure_num_list:
                fig_suptitle = plt.figure(fig_num).get_suptitle()

                    fig_suptitle = fig_suptitle.get_text()

        except Exception as e:
            print(e)
            return
        finally:
            if current_active_figure:
                plt.figure(current_active_figure)

    def add_figure(self, fig: Figure):
        fig_num = fig.number
        if fig_num in self.figures_refs:
            return

        self.figures_refs[fig_num] = fig
        self.figures_status[fig_num] = True
        item = QListWidgetItem(f"Figure {fig_num}")
        item.setForeground(QColor("green"))
        item.setData(Qt.ItemDataRole.UserRole, fig_num)
        self.list_widget.addItem(item)

    def mark_figure_closed(self, fig_num: int):
        if fig_num in self.figures_status:
            self.figures_status[fig_num] = False
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == fig_num:
                    item.setForeground(QColor("red"))
                    item.setText(f"Figure {fig_num} (Closed)")

    def _update_info_panel(self, fig_num: int):
        if fig_num in self.figures_refs:
            fig = self.figures_refs[fig_num]
            text = f"""Figure {fig_num}\nAxes: {len(fig.get_axes())}\nClosed: {not self.figures_status.get(fig_num, True)}"""
            self.info_window.setText(text)

    def _on_figure_selected(self, item: QListWidgetItem):
        fig_num = item.data(Qt.ItemDataRole.UserRole)
        self._update_info_panel(fig_num)

        if not self.figures_status.get(fig_num, False):
            self.active_figure_num = None
            # self.show_closed_figure_window(fig_num)
        else:
            fig = self.figures_refs[fig_num]
            plt.figure(fig_num)
            self.active_figure_num = fig_num
            self.figure_switched.emit(fig_num)

        self._update_active_marker()

    def _on_figure_double_clicked(self, item: QListWidgetItem):
        fig_num = item.data(Qt.ItemDataRole.UserRole)
        if not self.figures_status.get(fig_num, False):
            self.show_closed_figure_window(fig_num)
        else:
            self.active_figure_num = fig_num
            self._update_active_marker()
            self.show_active_figure_window()

    def _open_context_menu(self, position):
        menu = QMenu(self)
        close_action = menu.addAction("Close Figure")
        save_action = menu.addAction("Save Figure")

        selected_item = self.list_widget.itemAt(position)
        if selected_item is None:
            return

        fig_num = selected_item.data(Qt.ItemDataRole.UserRole)
        action = menu.exec(self.list_widget.mapToGlobal(position))

        if action == close_action:
            self.mark_figure_closed(fig_num)
        elif action == save_action:
            self._save_figure(fig_num)

    def _save_figure(self, fig_num: int):
        if fig_num in self.figures_refs:
            fig = self.figures_refs[fig_num]
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                f"Save Figure {fig_num}",
                f"figure_{fig_num}",
                "Images (*.png *.pdf *.svg)",
            )
            if file_path:
                if file_path.endswith(".pdf"):
                    fig.savefig(file_path, format="pdf")
                elif file_path.endswith(".svg"):
                    fig.savefig(file_path, format="svg")
                else:
                    fig.savefig(file_path, format="png")

    def show_closed_figure_window(self, fig_num: int):
        if fig_num in self.figure_windows:
            window = self.figure_windows[fig_num]
            window.showNormal()
            window.raise_()
            window.activateWindow()
        else:
            if fig_num in self.figures_refs:
                fig = self.figures_refs[fig_num]
                window = FigureWindow(fig, parent=self)
                self.figure_windows[fig_num] = window
                window.show()

    def show_active_figure_window(self):
        if self.active_figure_num is None:
            return

        fig_num = self.active_figure_num

        if fig_num not in self.figure_windows:
            if fig_num in self.figures_refs:
                fig = self.figures_refs[fig_num]
                window = FigureWindow(fig, parent=self)
                self.figure_windows[fig_num] = window
                window.show()
        else:
            window = self.figure_windows[fig_num]
            window.showNormal()
            window.raise_()
            window.activateWindow()

    def refresh_figure(self, fig: Figure):
        fig_num = fig.number
        self.figures_refs[fig_num] = fig
        if fig_num in self.figure_windows:
            window = self.figure_windows[fig_num]
            window.canvas.draw()

    def notify_figure_window_closed(self, fig_num: int):
        if fig_num in self.figure_windows:
            del self.figure_windows[fig_num]

    def has_figure(self, fig_num: int) -> bool:
        return fig_num in self.figures_refs

    def show_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def force_close_all(self):
        reply = QMessageBox.question(
            self,
            "Confirm Exit",
            "Are you sure you want to close Plot Manager and all figures?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            window_list = self.figure_windows.copy().values()
            for window in window_list:
                if window:
                    window.close()
            self.figure_windows.clear()
            self.close()

    def closeEvent(self, event):
        if self.allow_full_close:
            self.force_close_all()
        else:
            self.hide()
            event.ignore()

    def _update_active_marker(self):
        """Append ‘*’ to the active figure’s name and remove it elsewhere."""
        for i in range(self.list_widget.count()):
            it = self.list_widget.item(i)
            num = it.data(Qt.ItemDataRole.UserRole)
            if not self.figures_status.get(num, True):
                text = f"Figure {num} (Closed)"
            else:
                text = f"Figure {num}"
                if num == self.active_figure_num:
                    text += " *"
            it.setText(text)


# --- Test Script ---
if __name__ == "__main__":
    app = QApplication(sys.argv)

    plot_window = PlotWindow(allow_full_close=True)
    plot_window.show()

    fig1 = plt.figure(1)
    x = np.linspace(0, 2 * np.pi, 100)
    plt.plot(x, np.sin(x))
    plot_window.add_figure(fig1)

    fig2 = plt.figure(2)
    plt.plot(x, np.cos(x))
    plot_window.add_figure(fig2)

    plt.close(fig1)
    plot_window.mark_figure_closed(1)

    fig3 = plt.figure(3)
    plt.plot([1, 2, 3, 4], [1, 4, 9, 16])
    plot_window.add_figure(fig3)

    sys.exit(app.exec())
