import re
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn as skl
from IPython.core.interactiveshell import InteractiveShell
from IPython.utils.capture import capture_output
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PyQt6.Qsci import QsciAPIs, QsciLexerPython, QsciScintilla
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QImage, QKeyEvent, QPalette, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QDockWidget,
    QLabel,
    QMainWindow,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class ScintillaConsole(QsciScintilla):
    # Regex to match ANSI escape sequences (like \x1b[31m)
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    def __init__(
        self,
        parent: QWidget,
        prompt_str: str,
        welcome_message: str,
        color_theme: str,
    ):
        super().__init__(parent=parent)

        self.prompt_str = prompt_str
        self.plot_window = PlotWindow(parent=self.parent())
        self.plot_window.hide()

        self.color_theme = color_theme
        # --- Core background colors
        bg_color = QColor("#1e1e1e")
        fg_color = QColor("#dcdcdc")

        # IPython shell setup
        self.shell = InteractiveShell.instance()
        self.user_ns = self.shell.user_ns
        self.user_ns.update({"np": np, "plt": plt, "pd": pd, "skl": skl})

        # Editor look
        self.setUtf8(True)
        font = QFont("Consolas", 12)
        self.setFont(font)
        self.setMarginsFont(font)

        # Basic colors
        self.setCaretLineVisible(True)
        self.setCaretLineBackgroundColor(Qt.GlobalColor.darkGray)

        self.setColor(Qt.GlobalColor.white)  # default text
        self.setPaper(Qt.GlobalColor.black)  # background

        # Editor text area and margins
        self.setPaper(bg_color)  # Text area
        self.setColor(fg_color)  # Default text
        self.setMarginsBackgroundColor(bg_color)
        self.setMarginsForegroundColor(QColor("#888"))  # Line numbers

        #self.setMarginLineNumbers(1, True)

        # Set background of whole widget (scrollbars etc)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Base, bg_color)
        palette.setColor(QPalette.ColorRole.Window, bg_color)
        self.setPalette(palette)

        # Viewport (extra coverage for some themes)
        self.viewport().setStyleSheet("background-color: #1e1e1e;")

        # Syntax highlighting
        self.lexer = QsciLexerPython()
        self.lexer.setDefaultFont(font)

        # Background & default
        self.lexer.setPaper(Qt.GlobalColor.black)
        self.lexer.setColor(Qt.GlobalColor.white)  # default text
        self.setLexer(self.lexer)

        # Auto-completion setup
        self.api = QsciAPIs(self.lexer)
        self.update_autocompletions()
        self.api.prepare()
        self.setAutoCompletionThreshold(1)
        self.setAutoCompletionSource(QsciScintilla.AutoCompletionSource.AcsAll)

        # Command history
        self.history = []
        self.in_history_mode = False
        self.history_pending_input = ""
        self.history_index = 0

        # Prompt management
        self.appendText(welcome_message)
        self.appendText("# The following modules have been imported: numpy as np, matplotlib.pyplot as plt, pandas as pd, sklearn as skl\n")
        self.appendText("\n")
        self.appendText(self.prompt_str)
        self.prompt_line = self.lines() - 1

        self.STYLE_STDERR = 128
        self.SendScintilla(self.SCI_STYLESETFONT, self.STYLE_STDERR, b"Consolas")
        self.SendScintilla(self.SCI_STYLESETSIZE, self.STYLE_STDERR, 12)
        self.SendScintilla(self.SCI_STYLESETBACK, self.STYLE_STDERR, QColor("#1e1e1e"))
        self.SendScintilla(self.SCI_STYLESETFORE, self.STYLE_STDERR, QColor("red"))

        if self.color_theme == "light":
            self.set_light_theme()
        else:
            self.set_dark_theme()

    @staticmethod
    def remove_ansi_codes(text):
        return ScintillaConsole.ansi_escape.sub("", text)

    def get_current_input(self):
        total_lines = self.lines()
        return "\n".join([self.text(i) for i in range(self.prompt_line, total_lines)])

    def set_dark_theme(self):
        from PyQt6.QtGui import QColor, QPalette

        bg_color = QColor("#1e1e1e")
        fg_color = QColor("#dcdcdc")

        self.setPaper(bg_color)
        self.setColor(fg_color)
        self.setMarginsBackgroundColor(bg_color)
        self.setMarginsForegroundColor(QColor("#888888"))
        self.setCaretLineBackgroundColor(QColor("#2a2a2a"))

        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Base, bg_color)
        palette.setColor(QPalette.ColorRole.Window, bg_color)
        self.setPalette(palette)
        self.viewport().setStyleSheet("background-color: #1e1e1e;")

        self.lexer.setColor(fg_color)
        self.lexer.setPaper(bg_color)

        self.lexer.setColor(QColor("#569CD6"), QsciLexerPython.Keyword)
        self.lexer.setColor(QColor("#6A9955"), QsciLexerPython.Comment)
        self.lexer.setColor(QColor("#DCDCAA"), QsciLexerPython.Number)
        self.lexer.setColor(QColor("#CE9178"), QsciLexerPython.DoubleQuotedString)
        self.lexer.setColor(QColor("#CE9178"), QsciLexerPython.SingleQuotedString)
        self.lexer.setColor(QColor("#4EC9B0"), QsciLexerPython.ClassName)
        self.lexer.setColor(QColor("#DCDCDC"), QsciLexerPython.FunctionMethodName)
        self.lexer.setColor(QColor("#D16969"), QsciLexerPython.Operator)
        self.lexer.setColor(QColor("#C586C0"), QsciLexerPython.Decorator)

    def set_light_theme(self):
        bg_color = QColor("#ffffff")
        fg_color = QColor("#000000")

        self.setPaper(bg_color)
        self.setColor(fg_color)
        self.setMarginsBackgroundColor(QColor("#f0f0f0"))
        self.setMarginsForegroundColor(QColor("#888888"))
        self.setCaretLineBackgroundColor(QColor("#e8e8ff"))

        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Base, bg_color)
        palette.setColor(QPalette.ColorRole.Window, bg_color)
        self.setPalette(palette)
        self.viewport().setStyleSheet("background-color: white;")

        # 👇 Persistent lexer object
        self.lexer.setColor(fg_color)
        self.lexer.setPaper(bg_color)

        self.lexer.setColor(QColor("#0000ff"), QsciLexerPython.Keyword)
        self.lexer.setColor(QColor("#008000"), QsciLexerPython.Comment)
        self.lexer.setColor(QColor("#800000"), QsciLexerPython.Number)
        self.lexer.setColor(QColor("#a31515"), QsciLexerPython.DoubleQuotedString)
        self.lexer.setColor(QColor("#a31515"), QsciLexerPython.SingleQuotedString)
        self.lexer.setColor(QColor("#267f99"), QsciLexerPython.ClassName)
        self.lexer.setColor(QColor("#795E26"), QsciLexerPython.FunctionMethodName)
        self.lexer.setColor(QColor("#000000"), QsciLexerPython.Operator)
        self.lexer.setColor(QColor("#AF00DB"), QsciLexerPython.Decorator)

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        modifiers = event.modifiers()
        cursor_line, cursor_index = self.getCursorPosition()

        # Prevent any editing above the prompt
        if self.hasSelectedText():
            sel_start_line, _, sel_end_line, _ = self.getSelection()
            if sel_start_line < self.prompt_line:
                return

        # Prevent backspace/delete into prompt
        if key in [Qt.Key.Key_Backspace, Qt.Key.Key_Delete]:
            if cursor_line < self.prompt_line or (
                cursor_line == self.prompt_line and cursor_index <= len(self.prompt_str)
            ):
                return

        # Execute code on Enter (without Shift)
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if modifiers & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)  # allow multi-line input
            else:
                self.run_current_input()
            return

        # Navigate backward in history
        elif key == Qt.Key.Key_Up:
            if not self.in_history_mode:
                # Save what's currently typed before entering history navigation
                self.history_pending_input = self.get_current_input()
                self.in_history_mode = True
                self.history_index = len(self.history)

            matches = [
                h
                for h in self.history
                if h.startswith(self.history_pending_input.strip())
            ]
            if matches:
                self.history_index = max(0, self.history_index - 1)
                match = matches[self.history_index % len(matches)]
                self.replace_current_input(match)
            return

        # Navigate forward in history, restore input if at the end
        elif key == Qt.Key.Key_Down:
            if not self.in_history_mode:
                return

            matches = [
                h
                for h in self.history
                if h.startswith(self.history_pending_input.strip())
            ]

            if matches:
                if self.history_index + 1 >= len(matches):
                    # End of history — restore what was originally typed
                    self.replace_current_input(self.history_pending_input)
                    self.in_history_mode = False
                    self.history_index = len(self.history)
                else:
                    self.history_index += 1
                    match = matches[self.history_index % len(matches)]
                    self.replace_current_input(match)
            else:
                self.replace_current_input(self.history_pending_input)
                self.in_history_mode = False
                self.history_index = len(self.history)
            return

        # Block typing before prompt line
        if cursor_line < self.prompt_line:
            return

        # If none of the above, allow normal behavior
        super().keyPressEvent(event)

    def run_current_input(self):
        # Extract code from the current prompt line to end
        total_lines = self.lines()
        code_lines = []
        for line_num in range(self.prompt_line, total_lines):
            code_lines.append(self.text(line_num))
        code = "\n".join(code_lines).strip()

        if not code:
            self.appendText("\n" + self.prompt_line)
            self.prompt_line = self.lines() - 1
            return

        self.history.append(code)
        self.history_index = len(self.history)

        complete_status = self.shell.input_transformer_manager.check_complete(code)[0]
        if complete_status != "complete":
            self.appendText("\n... ")
            return

        with capture_output() as captured:
            try:
                self.shell.run_cell(code, store_history=True)
            except Exception as e:
                print(f"Error: {e}")

        stdout = captured.stdout
        stderr = captured.stderr
        if stdout:
            self.appendText(f"\n{ScintillaConsole.remove_ansi_codes(stdout)}")
        if stderr:
            self.appendTextStyled(
                ScintillaConsole.remove_ansi_codes(stderr), self.STYLE_STDERR
            )
        self.appendText("\n" + self.prompt_str)
        self.prompt_line = self.lines() - 1
        self.update_autocompletions()
        self.render_inline_plot()

    def appendText(self, text: str):
        self.setText(self.text() + text)
        self.moveCursorToEnd()

    def replace_current_input(self, new_text: str):
        """Replaces current input (from prompt line to end) with `new_text`."""
        total_lines = self.lines()
        last_line_index = len(self.text(total_lines - 1))

        # Clear current input area
        self.setSelection(self.prompt_line, 0, total_lines - 1, last_line_index)
        self.removeSelectedText()

        # Insert new history text at prompt line
        if len(new_text) == 0:
            new_text = self.prompt_str
        self.insertAt(new_text, self.prompt_line, 0)

        # Move cursor to end of inserted text
        self.moveCursorToEnd()

    def moveCursorToEnd(self):
        line = self.lines() - 1
        index = len(self.text(line))
        self.setCursorPosition(line, index)
        self.ensureLineVisible(line)

    def update_autocompletions(self):
        """Safely updates the API list for autocompletion using the current IPython namespace."""
        try:
            if not hasattr(self, "api") or self.api is None:
                return  # No API object to update

            self.api.clear()

            for name in self.user_ns:
                if not name.startswith("_"):
                    self.api.add(name)

            self.api.prepare()
        except RuntimeError as e:
            print(f"[AutoCompletion Error] {e}")

    def appendTextStyled(self, text: str, style: int):
        """Appends text with a specific style (e.g., red for errors)."""
        self.moveCursorToEnd()
        self.SendScintilla(
            self.SCI_STARTSTYLING, self.SendScintilla(self.SCI_GETCURRENTPOS)
        )
        self.SendScintilla(self.SCI_SETSTYLING, len(text), style)
        self.insert(text)

    def render_inline_plot(self):
        """Captures the current matplotlib figure and displays it inline as a QLabel."""
        if not plt.get_fignums():
            self.plot_window.hide()
            return

        fig = plt.gcf()
        self.plot_window.update_plot(fig)
        # plt.close(fig)  # prevent external popup


class PlotWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Inline Plot Viewer")
        self.setGeometry(200, 200, 800, 600)

        self.label = QLabel()
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

    def update_plot(self, fig):
        canvas = FigureCanvas(fig)
        canvas.draw()

        width, height = fig.get_size_inches() * fig.dpi
        img = canvas.buffer_rgba()
        qimg = QImage(img, int(width), int(height), QImage.Format.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qimg)

        self.label.setPixmap(pixmap)
        self.resize(pixmap.width(), pixmap.height())
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        event.ignore()  # Prevent destruction
        self.hide()  # Just hide the window instead


class ConsolePanel(QWidget):
    def __init__(
        self,
        parent=None,
        prompt_str: str = ">>> ",
        welcome_message: str = "# QNEP IPython console\n",
        color_theme: str = "dark",
    ):
        super().__init__(parent)
        self.console = ScintillaConsole(
            self,
            prompt_str=prompt_str,
            welcome_message=welcome_message,
            color_theme=color_theme,
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.console)
        self.setLayout(layout)


class ConsoleDock(QDockWidget):
    def __init__(self, title, parent=None):
        super().__init__(title, parent)

    def closeEvent(self, event):
        self.setFloating(False)
        self.parent().addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self)
        event.ignore()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Main Application with Docked Python Console")
        self.setGeometry(100, 100, 1200, 800)

        # Central widget (placeholder for main content)
        self.editor = QTextEdit()
        self.editor.setPlainText("This is the main application area.")
        self.setCentralWidget(self.editor)

        # Console dock
        self.console_dock = ConsoleDock("Python Console", self)
        self.console_panel = ConsolePanel()
        self.console_dock.setWidget(self.console_panel)
        self.console_dock.setAllowedAreas(
            Qt.DockWidgetArea.BottomDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.console_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable
            | QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )

        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.console_dock)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
