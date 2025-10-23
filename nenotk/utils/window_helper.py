#region Imports
import tkinter as tk
from typing import Literal



__all__ = [
    "center_window",
    ]


def center_window(window: tk.Misc, to: Literal['screen', 'parent'] = 'screen') -> None:
    """Centers a Tkinter window.
    Args:
        window: The Tkinter window to center.
        to: 'screen' to center on the monitor, 'parent' to center on the parent window/root.
    """
    window.update_idletasks()
    w = window.winfo_reqwidth() or window.winfo_width()
    h = window.winfo_reqheight() or window.winfo_height()
    if to == 'parent' and getattr(window, "master", None) is not None:
        parent = window.master
        try:
            if parent.winfo_ismapped():
                px, py = parent.winfo_rootx(), parent.winfo_rooty()
                pw, ph = parent.winfo_width(), parent.winfo_height()
                x = px + max(0, (pw - w) // 2)
                y = py + max(0, (ph - h) // 2)
            else:
                sw, sh = window.winfo_screenwidth(), window.winfo_screenheight()
                x = max(0, (sw - w) // 2)
                y = max(0, (sh - h) // 3)
        except Exception:
            sw, sh = window.winfo_screenwidth(), window.winfo_screenheight()
            x = max(0, (sw - w) // 2)
            y = max(0, (sh - h) // 3)
    else:
        sw, sh = window.winfo_screenwidth(), window.winfo_screenheight()
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 3)
    window.geometry(f"+{x}+{y}")
