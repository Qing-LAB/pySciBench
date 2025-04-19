import sys
import re

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel
from PyQt6.Qsci import QsciScintilla, QsciLexerPython, QsciAPIs
from PyQt6.QtGui import QFont, QKeyEvent, QPixmap, QImage
from PyQt6.QtCore import Qt

from IPython.core.interactiveshell import InteractiveShell
from IPython.utils.capture import capture_output
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

class ScintillaConsole(QsciScintilla):
    # Regex to match ANSI escape sequences (like \x1b[31m)
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    
    def __init__(self, prompt_str):
        super().__init__()

        self.prompt_str = prompt_str
        self.plot_window = PlotWindow()
        self.plot_window.hide()
        
        # IPython shell setup
        self.shell = InteractiveShell.instance()
        self.user_ns = self.shell.user_ns
        self.user_ns.update({'np': np, 'plt': plt})

        # Editor look
        self.setUtf8(True)
        font = QFont("Courier", 12)
        self.setFont(font)
        self.setMarginsFont(font)
        self.setMarginLineNumbers(1, True)
        self.setMarginsBackgroundColor(Qt.GlobalColor.lightGray)
        self.setCaretLineVisible(True)
        self.setCaretLineBackgroundColor(Qt.GlobalColor.yellow)

        # Syntax highlighting
        self.lexer = QsciLexerPython()
        self.lexer.setDefaultFont(font)
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
        self.appendText("# PyQt6 + IPython Console\n")
        self.appendText(self.prompt_str)
        self.prompt_line = self.lines() - 1
        
        self.STYLE_STDERR = 128
        self.SendScintilla(self.SCI_STYLESETFORE, self.STYLE_STDERR, Qt.GlobalColor.red)
        self.SendScintilla(self.SCI_STYLESETFONT, self.STYLE_STDERR, b"Courier")
        self.SendScintilla(self.SCI_STYLESETSIZE, self.STYLE_STDERR, 12)

    @staticmethod
    def remove_ansi_codes(text):
        return ScintillaConsole.ansi_escape.sub('', text)

    def get_current_input(self):
        total_lines = self.lines()
        return "\n".join([self.text(i) for i in range(self.prompt_line, total_lines)])

    # def mousePressEvent(self, event):
    #     x = int(event.position().x())
    #     y = int(event.position().y())
    #     pos = self.SendScintilla(self.SCI_POSITIONFROMPOINT, x, y)
    #     line, index = self.lineIndexFromPosition(pos)

    #     if line < self.prompt_line:
    #         return  # Block mouse interaction above prompt
    #     super().mousePressEvent(event)

    # def mouseMoveEvent(self, event):
    #     x = int(event.position().x())
    #     y = int(event.position().y())
    #     pos = self.SendScintilla(self.SCI_POSITIONFROMPOINT, x, y)
    #     line, index = self.lineIndexFromPosition(pos)

    #     if line < self.prompt_line:
    #         return
    #     super().mouseMoveEvent(event)
    
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
                cursor_line == self.prompt_line and cursor_index <= len(self.prompt_str)):
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

            matches = [h for h in self.history if h.startswith(self.history_pending_input.strip())]
            if matches:
                self.history_index = max(0, self.history_index - 1)
                match = matches[self.history_index % len(matches)]
                self.replace_current_input(match)
            return

        # Navigate forward in history, restore input if at the end
        elif key == Qt.Key.Key_Down:
            if not self.in_history_mode:
                return

            matches = [h for h in self.history if h.startswith(self.history_pending_input.strip())]

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
            self.appendText("\n"+self.prompt_line)
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
            self.appendTextStyled(ScintillaConsole.remove_ansi_codes(stderr), self.STYLE_STDERR)
        self.appendText("\n"+self.prompt_str)
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
            if not hasattr(self, 'api') or self.api is None:
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
        self.SendScintilla(self.SCI_STARTSTYLING, self.SendScintilla(self.SCI_GETCURRENTPOS))
        self.SendScintilla(self.SCI_SETSTYLING, len(text), style)
        self.insert(text)
        
    def render_inline_plot(self):
        """Captures the current matplotlib figure and displays it inline as a QLabel."""
        if not plt.get_fignums():
            self.plot_window.hide()
            return

        fig = plt.gcf()
        self.plot_window.update_plot(fig)
        plt.close(fig)  # prevent external popup

class PlotWindow(QWidget):
    def __init__(self):
        super().__init__()
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
        event.ignore()        # Prevent destruction
        self.hide()           # Just hide the window instead

class IPythonConsoleApp(QMainWindow):
    def __init__(self, parent_name : str = "", geometry : list = []):
        super().__init__()
        self.parent_window_name = parent_name
        
        if len(parent_name)>0:
            self.setWindowTitle(" ".join([self.parent_window_name, "Python Console"])
        else:
            self.setWindowTitle("Python Console")
            
        if len(geometry)!=4:
            self.geometry = [100, 100, 1000, 700]
        else:
            self.geomtry = geometry
        self.setGeometry(*self.geometry)

        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        self.console = ScintillaConsole(">>> ")
        layout.addWidget(self.console)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = IPythonConsoleApp("main", [100, 100, 1000, 700])
    window.show()
    sys.exit(app.exec())
