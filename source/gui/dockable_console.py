import re
import sys

import matplotlib

matplotlib.use("QtAgg", force=True)
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn as skl
from IPython.terminal.interactiveshell import TerminalInteractiveShell
from IPython.utils.capture import capture_output
from plot_window import PlotWindow
from PyQt6.Qsci import QsciAPIs, QsciLexerPython, QsciScintilla
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QImage, QKeyEvent, QPalette, QPixmap
from PyQt6.QtWidgets import (QApplication, QDockWidget, QLabel, QMainWindow,
                             QTextEdit, QVBoxLayout, QWidget)


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
        self.plot_window = PlotWindow(parent=self.window())
        self.plot_window.figure_switched.connect(self._on_figure_switched)

        self.color_theme = color_theme
        # --- Core background colors
        bg_color = QColor("#1e1e1e")
        fg_color = QColor("#dcdcdc")

        # IPython shell setup
        self.shell = TerminalInteractiveShell.instance()
        self.install_display_hook()
        self.shell.enable_matplotlib(gui="qt")
        self.shell.run_line_magic("matplotlib", "qt")  # safe now
        from IPython.core.getipython import get_ipython

        ip = get_ipython()
        ip.display_formatter.active_types = ["text/plain", "text/html"]

        plt.ioff()
        plt.show = lambda *a, **kw: None  # prevent GUI popups from matplotlib

        self.user_ns = self.shell.user_ns
        from IPython.display import display

        self.user_ns["display"] = display

        self.user_ns.update(
            {"np": np, "pd": pd, "plt": plt, "skl": skl, "display": display}
        )

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

        # self.setMarginLineNumbers(1, True)

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
        self.appendText(
            "# The following modules have been imported: \n# numpy as np, matplotlib.pyplot as plt, pandas as pd, sklearn as skl\n"
        )
        self.appendText("\n")
        self.appendText(self.prompt_str)
        self.prompt_line = self.lines() - 1

        self.STYLE_STDERR = 128
        self.SendScintilla(self.SCI_STYLESETFONT, self.STYLE_STDERR, b"Consolas")
        self.SendScintilla(self.SCI_STYLESETSIZE, self.STYLE_STDERR, 12)
        self.SendScintilla(self.SCI_STYLESETBACK, self.STYLE_STDERR, QColor("#1e1e1e"))
        self.SendScintilla(self.SCI_STYLESETFORE, self.STYLE_STDERR, QColor("red"))

        self.STYLE_SYSTEM = 129
        self.SendScintilla(self.SCI_STYLESETFONT, self.STYLE_SYSTEM, b"Consolas")
        self.SendScintilla(self.SCI_STYLESETSIZE, self.STYLE_SYSTEM, 12)
        self.SendScintilla(
            self.SCI_STYLESETFORE, self.STYLE_SYSTEM, QColor("#888888")
        )  # Light gray
        self.SendScintilla(self.SCI_STYLESETITALIC, self.STYLE_SYSTEM, True)
        self.SendScintilla(
            self.SCI_STYLESETBACK, self.STYLE_SYSTEM, QColor("#1e1e1e")
        )  # Match dark bg

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

        if key in (Qt.Key.Key_PageUp, Qt.Key.Key_PageDown):
            super().keyPressEvent(event)  # allow normal scrolling
            return

        if cursor_line < self.prompt_line:
            if event.text().isprintable() and len(event.text()) > 0 and not modifiers:
                self.setSelection(-1, -1, -1, -1)
                self.moveCursorToEnd()
                self.insert(event.text())
                self.moveCursorToEnd()
                return

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

    def insert_system_message(self, message: str):
        self.moveCursorToEnd()
        self.SendScintilla(
            self.SCI_STARTSTYLING, self.SendScintilla(self.SCI_GETCURRENTPOS)
        )
        self.SendScintilla(self.SCI_SETSTYLING, len(message), self.STYLE_SYSTEM)
        self.insert(message)

    def insert_message_above_prompt(self, message: str):
        total_lines = self.lines()

        # Extract only user-typed input after the prompt (excluding prompt prefix like ">>> ")
        input_lines = []
        for i in range(self.prompt_line, total_lines):
            line_text = self.text(i)
            if line_text.startswith(self.prompt_str):
                input_lines.append(line_text[len(self.prompt_str) :])
            else:
                input_lines.append(line_text)
        user_input = "\n".join(input_lines).rstrip()

        # Remove prompt + current input
        last_line_index = len(self.text(self.lines() - 1))
        self.setSelection(self.prompt_line, 0, self.lines() - 1, last_line_index)
        self.removeSelectedText()

        # Insert the system message in styled form
        self.appendText("\n")
        self.insert_system_message(f"{message}\n")

        # Re-insert prompt and original user input
        self.appendText(self.prompt_str)
        self.prompt_line = self.lines() - 1
        if user_input:
            self.insert(user_input)
            self.moveCursorToEnd()

    def ensure_active_figure(self):
        if plt.get_fignums() == []:
            plt.figure()

    def install_display_hook(self):
        from IPython.core.interactiveshell import InteractiveShell

        shell = self.shell

        def custom_displayhook(result):
            if result is not None:
                # Save _ and _N variables
                shell.user_ns["_"] = result
                shell.user_ns[f"_{shell.execution_count}"] = result

                # Format the output
                formatted = shell.display_formatter.format(result)
                if "text/plain" in formatted[0]:
                    text_output = formatted[0]["text/plain"]
                    self.appendText("\n" + text_output + "\n")

        shell.displayhook.write_output_prompt = lambda: None
        shell.displayhook.write_format_data = (
            lambda data, fmt=None: None
        )  # suppress default
        shell.displayhook.__call__ = custom_displayhook

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

        self.ensure_active_figure()
        before_plt = set(plt.get_fignums())

        with capture_output() as captured:
            try:
                self.shell.run_cell(code, store_history=True)
            except Exception as e:
                print(f"Error: {e}")

        after_plt = set(plt.get_fignums())
        closed_plt = before_plt - after_plt
        for fig_num in closed_plt:
            self.plot_window.mark_figure_closed(fig_num)

        stdout = captured.stdout
        stderr = captured.stderr
        if stdout:
            self.appendText(f"\n{ScintillaConsole.remove_ansi_codes(stdout)}")
        if stderr:
            self.appendTextStyled(
                ScintillaConsole.remove_ansi_codes(stderr), self.STYLE_STDERR
            )

        self.update_autocompletions()
        self.render_inline_plot()

        self.appendText("\n")
        self.reset_prompt()
        self.setFocus()

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

    def reset_prompt(self):
        self.appendText(self.prompt_str)
        self.prompt_line = self.lines() - 1

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
        print("rendering inline figures.")
        if not plt.get_fignums():
            self.plot_window.hide()
            return

        fig = plt.gcf()
        fig_num = fig.number

        if not fig.get_axes():
            return

        if self.plot_window.has_figure(fig_num):
            self.plot_window.refresh_figure(fig)
        else:
            added = self.plot_window.add_figure(fig)

            if added:
                self.plot_window.showNormal()
                self.plot_window.raise_()
                self.plot_window.activateWindow()

    def _on_figure_switched(self, fig_num):
        if fig_num == -1:
            # A closed figure was selected or invalid selection
            self.insert_message_above_prompt(
                "# Warning: Attempted to switch to a closed figure.\n"
            )
        else:
            import matplotlib.pyplot as plt

            plt.figure(fig_num)
            self.insert_message_above_prompt(f"# Switched to Figure {fig_num}\n")


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
        self.console_panel = ConsolePanel(
            self.console_dock,
            ">>> ",
            "# Welcome to pyElecular Python Console.\n",
            "light",
        )
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
        # sys.stdout = ConsoleOutputStream(self.console_panel.console.appendText)
        # sys.stderr = ConsoleOutputStream(lambda text: self.console_panel.console.appendTextStyled(text, self.STYLE_STDERR))


class ConsoleOutputStream:
    def __init__(self, append_func):
        self.append = append_func

    def write(self, text):
        if text.strip():
            self.append(text)

    def flush(self):
        pass  # No-op for compatibility


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
