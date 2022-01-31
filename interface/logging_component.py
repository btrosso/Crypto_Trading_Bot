import tkinter as tk
from datetime import datetime

from interface.styling import *

class Logging(tk.Frame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.logging_text = tk.Text(self, height=10, width=50, state=tk.DISABLED, bg=BG_COLOR, fg=FG_COLOR_2,
                                    font=GLOBAL_FONT)
        self.logging_text.pack(side=tk.TOP)

    def add_log(self, message: str):
        self.logging_text.configure(state=tk.NORMAL)
        # if you want the local time of your machine displayed swap utc now() for now()
        # the 1.0 argument means the text will be added at the beginning (before the existing text)
        # if we substitute 1.0 for tk.END then the newest logs will be added at the bottom or after the existing text
        self.logging_text.insert("1.0", datetime.utcnow().strftime("%a %H:%M:%S :: ") + message + "\n")
        self.logging_text.configure(state=tk.DISABLED)