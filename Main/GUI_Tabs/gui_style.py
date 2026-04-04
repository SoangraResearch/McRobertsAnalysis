"""Application-wide ttk look (clam): action buttons, notebook tab focus, tab-bar cursor.

- Sets theme and App.TButton (gray idle, white hover, pointer cursor on macOS).
- Optional notebook helpers: pointer over tabs, suppress dotted focus ring on the tab row."""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk

_IDLE_BG = "#d4d4d4"
_HOVER_BG = "#ffffff"
_FG = "#000000"
_DISABLED_BG = "#a0a0a0"
_DISABLED_FG = "#505050"

_style_roots: set[int] = set()


def _pointer_cursor() -> str:
    if sys.platform == "darwin":
        return "pointinghand"
    return "hand2"


def ensure_gui_style(root: tk.Misc) -> None:
    """Apply clam theme, App.TButton, and notebook focus styling once per toplevel (idempotent)."""
    key = id(root)
    if key in _style_roots:
        return
    _style_roots.add(key)

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(
        "App.TButton",
        background=_IDLE_BG,
        foreground=_FG,
        borderwidth=1,
        relief="raised",
        padding=(10, 5),
        focuscolor="none",
    )
    try:
        style.configure("App.TButton", focusthickness=0)
    except tk.TclError:
        pass

    style.map(
        "App.TButton",
        background=[
            ("disabled", _DISABLED_BG),
            ("pressed", "#c0c0c0"),
            ("active", _HOVER_BG),
            ("!disabled", _IDLE_BG),
        ],
        foreground=[
            ("disabled", _DISABLED_FG),
            ("!disabled", _FG),
        ],
    )

    style.configure("TNotebook", focuscolor="none")
    try:
        style.configure("TNotebook", focusthickness=0)
    except tk.TclError:
        pass
    style.configure("TNotebook.Tab", focuscolor="none")
    try:
        style.configure("TNotebook.Tab", focusthickness=0)
    except tk.TclError:
        pass


def make_action_button(master, **kwargs) -> ttk.Button:
    """Styled ttk.Button: gray idle, white hover, pointer cursor on macOS."""
    root = master.winfo_toplevel()
    ensure_gui_style(root)
    kwargs.setdefault("style", "App.TButton")
    kwargs.setdefault("takefocus", False)
    kwargs.setdefault("cursor", _pointer_cursor())
    return ttk.Button(master, **kwargs)


def apply_notebook_tab_pointer_cursor(notebook: ttk.Notebook) -> None:
    """Pointer cursor over tabs; move focus into the page to avoid dotted outline on the tab row. Idempotent."""
    if getattr(notebook, "_gui_style_notebook_helpers", False):
        return
    notebook._gui_style_notebook_helpers = True
    root = notebook.winfo_toplevel()
    ensure_gui_style(root)
    cur = _pointer_cursor()
    try:
        notebook.configure(takefocus=False, highlightthickness=0)
    except tk.TclError:
        pass

    def focus_selected_tab_content(_event: tk.Event | None = None) -> None:
        try:
            wid = notebook.select()
            if not wid:
                return
            tab = notebook.nametowidget(wid)
            tab.focus_set()
        except (tk.TclError, KeyError):
            pass

    notebook.bind(
        "<<NotebookTabChanged>>",
        lambda _e: notebook.after_idle(focus_selected_tab_content),
        add="+",
    )

    def on_tab_click(event: tk.Event) -> None:
        try:
            notebook.index(f"@{event.x},{event.y}")
        except tk.TclError:
            return
        notebook.after_idle(focus_selected_tab_content)

    notebook.bind("<Button-1>", on_tab_click, add="+")

    def on_motion(event: tk.Event) -> None:
        try:
            notebook.index(f"@{event.x},{event.y}")
            notebook.configure(cursor=cur)
        except tk.TclError:
            notebook.configure(cursor="")

    def on_leave(_event: tk.Event) -> None:
        notebook.configure(cursor="")

    notebook.bind("<Motion>", on_motion, add="+")
    notebook.bind("<Leave>", on_leave, add="+")
