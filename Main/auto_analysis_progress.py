# progress_display.py
import tkinter as tk
from tkinter import font as tkfont
from typing import Union, Optional


class auto_analysis_progress:

    DEFAULT_STEPS = [
        "Reading Data",
        "Splitting Data",
        "Sequence Detection",
        "Segment Selection",
        "Segment Analysis",
        "Output",
    ]

    def __init__(self, parent: tk.Widget, font_size: int = 10, pady=(20, 5), arrow: str = " -> "):
        self.parent = parent
        self.steps = list(self.DEFAULT_STEPS)
        self.arrow = arrow

        # Fonts
        self.base_font = tkfont.nametofont("TkDefaultFont").copy()
        self.base_font.configure(size=font_size)
        self.bold_font = self.base_font.copy()
        self.bold_font.configure(weight="bold")

        # Canvas height from font metrics
        line_height = max(self.base_font.metrics("linespace"), self.bold_font.metrics("linespace")) + 6
        self.canvas = tk.Canvas(parent, height=line_height, bd=0, highlightthickness=0, background=parent.cget("bg"))
        self.canvas.pack(pady=pady, fill="x")

        # State
        self.step_item_ids = []
        self._selected_index: Optional[int] = None

        # Prevent user interaction
        self.canvas.bind("<Button-1>", lambda e: "break")
        self.canvas.bind("<B1-Motion>", lambda e: "break")
        self.canvas.bind("<MouseWheel>", lambda e: "break")
        self.canvas.bind("<Key>", lambda e: "break")

        # Redraw when canvas resizes
        self.canvas.bind("<Configure>", self._redraw)

        # initial draw after geometry settles
        self.canvas.after(1, self._redraw)

    def _redraw(self, event=None):
        c = self.canvas
        c.delete("all")
        cw = c.winfo_width()
        ch = c.winfo_height()
        if cw <= 1:
            c.after(20, self._redraw)
            return

        # Build parts list
        parts = []
        for i, step in enumerate(self.steps):
            parts.append(("step", step))
            if i < len(self.steps) - 1:
                parts.append(("arrow", self.arrow))

        # Compute reserved widths
        reserved_widths = []
        for kind, text in parts:
            if kind == "step":
                reserved_widths.append(self.bold_font.measure(text))
            else:
                reserved_widths.append(self.base_font.measure(text))

        total_width = sum(reserved_widths)
        x = (cw - total_width) / 2
        y = ch / 2

        # Create text items at reserved positions
        self.step_item_ids = []
        for (kind, text), w in zip(parts, reserved_widths):
            tid = c.create_text(x, y, text=text, font=self.base_font, anchor="w")
            if kind == "step":
                self.step_item_ids.append(tid)
            x += w

        # Reapply selection (if any)
        self._apply_selection()

    def _apply_selection(self):
        for i, tid in enumerate(self.step_item_ids):
            font_to_use = self.bold_font if (self._selected_index == i) else self.base_font
            self.canvas.itemconfig(tid, font=font_to_use)

    def update_progress(self, index_or_name: Union[int, str]):
        if isinstance(index_or_name, int):
            if 0 <= index_or_name < len(self.steps):
                self._selected_index = index_or_name
            else:
                return
        else:
            try:
                self._selected_index = self.steps.index(index_or_name)
            except ValueError:
                return
        self._apply_selection()

    def clear(self):
        self._selected_index = None
        self._apply_selection()