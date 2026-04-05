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
from typing import Any, Callable, Dict, List, Optional

# How long to show the green check after a successful heavy job (indeterminate bar).
_SUCCESS_FLASH_MS = 3000


class HeavyJobRunner:
    def __init__(self, root: tk.Misc, status_frame: ttk.Frame):
        self.root = root
        self._status_frame = status_frame

        self._label_style_normal = "TLabel"
        self._label_style_success = "HeavyJobSuccess.TLabel"
        style = ttk.Style(root)
        try:
            style.configure(self._label_style_success, foreground="#1b5e20")
        except tk.TclError:
            pass

        self._label = ttk.Label(status_frame, text="", style=self._label_style_normal)
        self._progress = ttk.Progressbar(
            status_frame, mode="indeterminate", length=240
        )

        self._busy = False
        self._disable_widgets: List[tk.Widget] = []
        self._entry_state_restore: Dict[int, str] = {}
        self._success_after_id: Optional[str] = None

    def register_disable_widgets(self, *widgets: tk.Widget) -> None:
        """Buttons (and similar) to disable while a job runs."""
        for w in widgets:
            if w is not None:
                self._disable_widgets.append(w)

    def schedule_main(self, fn: Callable[[], Any]) -> None:
        """Thread-safe: run *fn* on the Tk main thread."""
        self.root.after(0, fn)

    def schedule_status_message(self, text: str) -> None:
        """Thread-safe: update the busy status label from a worker thread.

        Used for granular progress (e.g. Tab 3 nonlinear analysis per period).
        Ignored if no job is active so stray callbacks do not repopulate the bar.
        """

        def apply() -> None:
            if not self._busy:
                return
            self._label.configure(text=text)
            try:
                self.root.update_idletasks()
            except tk.TclError:
                pass

        self.schedule_main(apply)

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
                    self._finish_busy_success(on_success, result)

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
        if self._success_after_id is not None:
            try:
                self.root.after_cancel(self._success_after_id)
            except (tk.TclError, ValueError):
                pass
            self._success_after_id = None

        self._busy = True
        try:
            self._label.configure(text=message, style=self._label_style_normal)
        except tk.TclError:
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

    def _finish_busy_success(
        self,
        on_success: Optional[Callable[[Any], None]],
        result: Any,
    ) -> None:
        self._progress.stop()
        self._progress.pack_forget()
        try:
            self._label.configure(
                text="✓ Complete",
                style=self._label_style_success,
            )
        except tk.TclError:
            self._label.configure(text="✓ Complete")

        self._busy = False
        try:
            self.root.configure(cursor="")
        except tk.TclError:
            pass
        self._apply_widget_states(disabled=False)
        self.root.update_idletasks()

        # Schedule clear as soon as the worker finishes — before on_success. Tab 3 runs
        # modal dialogs and slow UI in on_success; deferring this until after on_success
        # returned made the checkmark look "stuck" compared to Select Data (fast on_success).
        def clear_success() -> None:
            self._success_after_id = None
            try:
                self._label.pack_forget()
                self._label.configure(text="", style=self._label_style_normal)
            except tk.TclError:
                pass
            self.root.update_idletasks()

        self._success_after_id = self.root.after(_SUCCESS_FLASH_MS, clear_success)

        if on_success is not None:
            on_success(result)

    def _finish_busy(self) -> None:
        if self._success_after_id is not None:
            try:
                self.root.after_cancel(self._success_after_id)
            except (tk.TclError, ValueError):
                pass
            self._success_after_id = None

        self._progress.stop()
        self._progress.pack_forget()
        self._label.pack_forget()
        try:
            self._label.configure(text="", style=self._label_style_normal)
        except tk.TclError:
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
                if isinstance(w, tk.Entry):
                    wid = id(w)
                    if disabled:
                        if wid not in self._entry_state_restore:
                            self._entry_state_restore[wid] = str(w.cget("state"))
                        w.configure(state=tk.DISABLED)
                    else:
                        prev = self._entry_state_restore.pop(wid, tk.NORMAL)
                        w.configure(state=prev)
                    continue

                if hasattr(w, "state") and callable(w.state):
                    # ttk.* uses state(['disabled']) / state(['!disabled'])
                    w.state(["disabled"] if disabled else ["!disabled"])
                else:
                    w.configure(
                        state=tk.DISABLED if disabled else tk.NORMAL
                    )
            except (tk.TclError, AttributeError):
                continue
