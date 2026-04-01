"""Run long tasks on a worker thread while keeping Tk responsive.

GUI updates, dialogs, and Matplotlib must run on the main thread; use schedule_main()
from a worker to post short callbacks to the Tk event loop.
"""

from __future__ import annotations

import sys
import threading
import traceback
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable, List, Optional


class HeavyJobRunner:
    def __init__(self, root: tk.Misc, status_frame: ttk.Frame):
        self.root = root
        self._status_frame = status_frame

        self._label = ttk.Label(status_frame, text="")
        self._progress = ttk.Progressbar(
            status_frame, mode="indeterminate", length=240
        )

        self._busy = False
        self._disable_widgets: List[tk.Widget] = []

    def register_disable_widgets(self, *widgets: tk.Widget) -> None:
        """Buttons (and similar) to disable while a job runs."""
        for w in widgets:
            if w is not None:
                self._disable_widgets.append(w)

    def schedule_main(self, fn: Callable[[], Any]) -> None:
        """Thread-safe: run *fn* on the Tk main thread."""
        self.root.after(0, fn)

    @property
    def is_busy(self) -> bool:
        return self._busy

    def run(
        self,
        message: str,
        worker: Callable[[], Any],
        on_success: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """Start *worker* in a daemon thread. Returns False if already busy."""
        if self._busy:
            messagebox.showwarning(
                "Busy",
                "Another operation is already running. Please wait for it to finish.",
            )
            return False

        self._show_busy(message)

        def wrap() -> None:
            try:
                result = worker()

                def finish_ok() -> None:
                    self._finish_busy()
                    if on_success is not None:
                        on_success(result)

                self.schedule_main(finish_ok)
            except Exception:
                traceback.print_exc()
                err_msg = str(sys.exc_info()[1])

                def finish_err(msg: str = err_msg) -> None:
                    self._finish_busy()
                    if on_error is not None:
                        on_error(msg)
                    else:
                        messagebox.showerror("Error", msg)

                self.schedule_main(finish_err)

        threading.Thread(target=wrap, daemon=True).start()
        return True

    # --- internals ---

    def _show_busy(self, message: str) -> None:
        self._busy = True
        self._label.configure(text=message)
        self._label.pack(fill=tk.X, padx=6, pady=(4, 0))
        self._progress.pack(fill=tk.X, padx=6, pady=(0, 4))
        self._progress.start(12)
        try:
            self.root.configure(cursor="watch")
        except tk.TclError:
            pass
        self._apply_widget_states(disabled=True)
        self.root.update_idletasks()

    def _finish_busy(self) -> None:
        self._progress.stop()
        self._progress.pack_forget()
        self._label.pack_forget()
        self._label.configure(text="")
        self._busy = False
        try:
            self.root.configure(cursor="")
        except tk.TclError:
            pass
        self._apply_widget_states(disabled=False)
        self.root.update_idletasks()

    def _apply_widget_states(self, *, disabled: bool) -> None:
        for w in self._disable_widgets:
            try:
                if hasattr(w, "state") and callable(w.state):
                    # ttk.* uses state(['disabled']) / state(['!disabled'])
                    w.state(["disabled"] if disabled else ["!disabled"])
                else:
                    w.configure(
                        state=tk.DISABLED if disabled else tk.NORMAL
                    )
            except (tk.TclError, AttributeError):
                continue
