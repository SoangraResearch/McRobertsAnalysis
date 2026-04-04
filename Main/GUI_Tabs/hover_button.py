"""tk.Button helpers: gray by default, white while hovered, pointer cursor.

Does not change the global ttk theme."""

from __future__ import annotations

import sys
import tkinter as tk

_IDLE_BG = "#d4d4d4"
_HOVER_BG = "#ffffff"
_FG = "#000000"


def _pointer_cursor() -> str:
    if sys.platform == "darwin":
        return "pointinghand"
    return "hand2"


def apply_hover_button_style(btn: tk.Button) -> None:
    btn.configure(
        bg=_IDLE_BG,
        fg=_FG,
        activebackground=_HOVER_BG,
        activeforeground=_FG,
        relief="raised",
        bd=2,
        highlightthickness=0,
        highlightbackground=_IDLE_BG,
        cursor=_pointer_cursor(),
    )

    def on_enter(_: tk.Event) -> None:
        if str(btn.cget("state")) != "disabled":
            btn.configure(bg=_HOVER_BG)

    def on_leave(_: tk.Event) -> None:
        if str(btn.cget("state")) != "disabled":
            btn.configure(bg=_IDLE_BG)

    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)


def make_hover_button(master, **kwargs) -> tk.Button:
    kwargs.setdefault("takefocus", False)
    btn = tk.Button(master, **kwargs)
    apply_hover_button_style(btn)
    return btn
