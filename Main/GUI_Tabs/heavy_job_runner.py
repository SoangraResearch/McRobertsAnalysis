"""Run long tasks on a worker thread while keeping Tk responsive.

GUI updates, dialogs, and Matplotlib must run on the main thread; use schedule_main()
from a worker to post short callbacks to the Tk event loop.

**Single busy UI:** Build the shared status strip once with :func:`create_busy_status_strip`
from the main window. Long-running work should use the returned :class:`HeavyJobRunner`
(:meth:`~HeavyJobRunner.run`, :meth:`~HeavyJobRunner.schedule_status_message`, etc.).
Do not add separate bottom-of-window ``ttk.Progressbar`` widgets for the same purpose.
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

# Returned from *worker* to clear the busy UI without treating the job as an error.
HEAVY_JOB_CANCELLED = object()


def create_busy_status_strip(
    root: tk.Misc,
    *,
    pack_side: str = tk.BOTTOM,
    fill: str = tk.X,
) -> HeavyJobRunner:
    """Create the shared status frame (packed on *root*) and its :class:`HeavyJobRunner`.

    Call once during main-window setup, before packing the notebook/content that
    should fill the rest of the window. Returns the runner used by Tab 1, Tab 3,
    Tab 4 (``GUI_Main``), and any other heavy job entry points.
    """
    status_frame = ttk.Frame(root)
    status_frame.pack(side=pack_side, fill=fill)
    return HeavyJobRunner(root, status_frame)


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
        self._busy_base_message: str = ""
        self._determinate_job: bool = False
        self._progress_animation_active: bool = False
        self._disable_widgets: List[tk.Widget] = []
        self._entry_state_restore: Dict[int, str] = {}
        self._success_after_id: Optional[str] = None
        self._freeze_progress_on_success: bool = False

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

    def schedule_progress(self, percent: int) -> None:
        """Thread-safe: set determinate progress 0–100.

        Only moves the bar; the label is controlled by set_busy_base_message().
        No-op unless a determinate job is active (see run(..., determinate=True)).
        """
        pct = max(0, min(100, int(percent)))

        def apply() -> None:
            if not self._busy or not self._determinate_job:
                return
            try:
                self._progress.configure(value=pct)
            except tk.TclError:
                pass

        if threading.current_thread() is threading.main_thread():
            apply()
            try:
                self.root.update()
            except tk.TclError:
                pass
        else:
            self.schedule_main(apply)

    def set_busy_base_message(self, message: str) -> None:
        """Thread-safe: change the status label text (e.g. after worker phase)."""

        def apply() -> None:
            if not self._busy or not self._determinate_job:
                return
            self._busy_base_message = message
            try:
                self._label.configure(text=message, style=self._label_style_normal)
            except tk.TclError:
                self._label.configure(text=message)

        if threading.current_thread() is threading.main_thread():
            apply()
            try:
                self.root.update()
            except tk.TclError:
                pass
        else:
            self.schedule_main(apply)

    def release_success(
        self,
        message: str = "✓ Complete",
        *,
        flash_ms: int | None = None,
    ) -> None:
        """End a determinate job that used deferred_finalize (main thread or via schedule_main).

        Call after on_success finishes any extra main-thread work (e.g. building plots).
        *flash_ms* overrides _SUCCESS_FLASH_MS for this one message.
        """
        if not self._busy:
            return

        def apply() -> None:
            if not self._busy:
                return
            self._present_success_ui(message, flash_ms=flash_ms)

        self.schedule_main(apply)

    def _present_success_ui(
        self,
        message: str,
        *,
        flash_ms: int | None = None,
    ) -> None:
        if self._success_after_id is not None:
            try:
                self.root.after_cancel(self._success_after_id)
            except (tk.TclError, ValueError):
                pass
            self._success_after_id = None

        if self._progress_animation_active:
            self._progress.stop()
        self._progress_animation_active = False
        self._determinate_job = False
        self._progress.pack_forget()
        try:
            self._label.configure(text=message, style=self._label_style_success)
        except tk.TclError:
            self._label.configure(text=message)

        self._busy = False
        try:
            self.root.configure(cursor="")
        except tk.TclError:
            pass
        self._apply_widget_states(disabled=False)
        self.root.update_idletasks()

        def clear_success() -> None:
            self._success_after_id = None
            try:
                self._label.pack_forget()
                self._label.configure(text="", style=self._label_style_normal)
            except tk.TclError:
                pass
            self.root.update_idletasks()

        self._success_after_id = self.root.after(
            flash_ms if flash_ms is not None else _SUCCESS_FLASH_MS,
            clear_success,
        )

    @property
    def is_busy(self) -> bool:
        return self._busy

    def clear_busy(self) -> None:
        """Clear busy UI without a success flash (e.g. deferred *on_success* raised)."""

        def apply() -> None:
            self._finish_busy()

        self.schedule_main(apply)

    def run(
        self,
        message: str,
        worker: Callable[[], Any],
        on_success: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        *,
        determinate: bool = False,
        deferred_finalize: bool = False,
        freeze_progress_on_success: bool = False,
    ) -> bool:
        """Start *worker* in a daemon thread. Returns False if already busy.

        If *determinate* is True, use a 0–100 progress bar; the worker may call
        schedule_progress(percent) from a background thread.

        If *deferred_finalize* is True, the busy UI stays up after the worker
        returns; *on_success* must end by calling release_success() on the main
        thread (e.g. after plotting). Implies *determinate* if not set.

        If *freeze_progress_on_success* is True, on success the progress bar stops
        at 100% and the label keeps the final message (worker may return
        ``(payload, "status text")`` to set the label; otherwise *payload* is the
        worker return value). No auto-clear timer — useful for inspecting timing.
        """
        if deferred_finalize:
            determinate = True

        if self._busy:
            messagebox.showwarning(
                "Busy",
                "Another operation is already running. Please wait for it to finish.",
            )
            return False

        self._freeze_progress_on_success = bool(freeze_progress_on_success)
        self._show_busy(message, determinate=determinate)

        def wrap() -> None:
            try:
                result = worker()
                if result is HEAVY_JOB_CANCELLED:

                    def finish_cancel() -> None:
                        self._finish_busy()

                    self.schedule_main(finish_cancel)
                    return

                def finish_ok() -> None:
                    if deferred_finalize:
                        self._finish_worker_deferred(on_success, result)
                    else:
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

    def _finish_worker_deferred(
        self,
        on_success: Optional[Callable[[Any], None]],
        result: Any,
    ) -> None:
        """Worker finished; keep busy UI for main-thread follow-up (e.g. plot build)."""

        def run_followup() -> None:
            try:
                if on_success is not None:
                    on_success(result)
            except Exception:
                traceback.print_exc()
                err_msg = str(sys.exc_info()[1])
                self._finish_busy()
                messagebox.showerror("Error", err_msg)

        self.schedule_main(run_followup)

    # --- internals ---

    def _show_busy(self, message: str, *, determinate: bool = False) -> None:
        if self._success_after_id is not None:
            try:
                self.root.after_cancel(self._success_after_id)
            except (tk.TclError, ValueError):
                pass
            self._success_after_id = None

        self._busy = True
        self._busy_base_message = message
        self._determinate_job = determinate
        self._progress_animation_active = False
        try:
            self._label.configure(
                text=message, style=self._label_style_normal, wraplength=0
            )
        except tk.TclError:
            self._label.configure(text=message)
        self._label.pack(fill=tk.X, padx=6, pady=(4, 0))
        self._progress.pack(fill=tk.X, padx=6, pady=(0, 4))
        try:
            self._progress.stop()
        except tk.TclError:
            pass
        if determinate:
            self._progress.configure(mode="determinate", maximum=100, value=0)
        else:
            self._progress.configure(mode="indeterminate")
            self._progress.start(12)
            self._progress_animation_active = True
        try:
            self.root.configure(cursor="watch")
        except tk.TclError:
            pass
        self._apply_widget_states(disabled=True)
        self.root.update_idletasks()

    def _present_frozen_ui(self, message: str) -> None:
        """Stop animation, full bar, keep label + bar visible (no auto-hide)."""
        if self._success_after_id is not None:
            try:
                self.root.after_cancel(self._success_after_id)
            except (tk.TclError, ValueError):
                pass
            self._success_after_id = None

        if self._progress_animation_active:
            self._progress.stop()
        self._progress_animation_active = False
        self._determinate_job = False
        try:
            self._progress.configure(mode="determinate", maximum=100, value=100)
        except tk.TclError:
            pass
        try:
            self._label.configure(
                text=message,
                style=self._label_style_normal,
                wraplength=920,
            )
        except tk.TclError:
            self._label.configure(text=message)
        self._busy = False
        try:
            self.root.configure(cursor="")
        except tk.TclError:
            pass
        self._apply_widget_states(disabled=False)
        self.root.update_idletasks()

    def _finish_busy_success(
        self,
        on_success: Optional[Callable[[Any], None]],
        result: Any,
    ) -> None:
        if self._freeze_progress_on_success:
            payload = result
            freeze_msg: Optional[str] = None
            if (
                isinstance(result, tuple)
                and len(result) == 2
                and isinstance(result[1], str)
            ):
                payload, freeze_msg = result
            self._present_frozen_ui(freeze_msg if freeze_msg else "✓ Complete")
            self._freeze_progress_on_success = False
            if on_success is not None:
                on_success(payload)
            return

        self._present_success_ui("✓ Complete")

        if on_success is not None:
            on_success(result)

    def _finish_busy(self) -> None:
        if self._success_after_id is not None:
            try:
                self.root.after_cancel(self._success_after_id)
            except (tk.TclError, ValueError):
                pass
            self._success_after_id = None

        if self._progress_animation_active:
            self._progress.stop()
        self._progress_animation_active = False
        self._determinate_job = False
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
