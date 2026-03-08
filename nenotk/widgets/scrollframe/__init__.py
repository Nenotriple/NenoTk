"""
# Purpose
Provides a scrollable frame widget for Tkinter GUIs, supporting vertical, horizontal, or both scrollbars.

## API
- Class: `ScrollFrame(master, layout="vertical", label=None, maxwidth=None, ...) -> ttk.Frame`
    - `master`: parent widget
    - `layout`: 'vertical', 'horizontal', or 'both' (controls which scrollbars are shown)
    - `label`: optional string; if provided, wraps content in a ttk.LabelFrame
    - `maxwidth`: optional integer cap for vertical layout width sync
    - `.frame`: attribute; the inner frame for user content
    - `.set_maxwidth(maxwidth)`: update the vertical width cap at runtime
    - `Returns`: ScrollFrame instance

## Notes
- Mousewheel scrolling is dynamically enabled only when content exceeds the visible area.
- The `.frame` attribute is the container for user widgets.
- Emits <<ScrollStateChanged>> event when scrollable state changes.

## Example
```
import tkinter as tk
from nenotk.widgets.scrollframe import ScrollFrame
root = tk.Tk()
sf = ScrollFrame(root, layout="vertical")
sf.pack(fill="both", expand=True)
tk.Button(sf.frame, text="A Button").pack()
root.mainloop()
```
"""

#region Imports


# tkinter
import tkinter as tk
from tkinter import ttk


#endregion
#region _BaseScrollFrame


class _BaseScrollFrame:
    """Base scroll logic: Canvas + embedded Frame, scrollbars, and mousewheel handling.

        Parameters
        ----------
        layout : str
            One of 'vertical', 'horizontal', or 'both' indicating which scrollbars
            to create/bind. This name matches the internal attribute
            ``self.layout`` and the validator method.
    """
    def __init__(self, master: tk.Widget, layout: str = "vertical", maxwidth: int | None = None, *args: object, **kwargs: object) -> None:
        self.layout = self._validate_layout(layout)
        self._maxwidth = self._validate_maxwidth(maxwidth)
        self._width_sync_job: str | None = None
        self._wheel_bindtag = f"ScrollFrameMouseWheel{hex(id(self))}"
        self._wheel_cooldown_ms = 250
        self._wheel_scroll_job: str | None = None
        self._wheel_scroll_active = False
        self._setup_scroll_canvas(master)
        self._bind_mousewheel_events()


    def _validate_layout(self, layout: str) -> str:
        """Ensure layout is 'vertical', 'horizontal', or 'both'."""
        if layout not in ("vertical", "horizontal", "both"):
            raise ValueError("layout must be 'vertical', 'horizontal', or 'both'")
        return layout


    @staticmethod
    def _validate_maxwidth(maxwidth: int | None) -> int | None:
        """Normalize an optional width cap for vertical layouts."""
        if maxwidth is None:
            return None
        try:
            value = int(maxwidth)
        except (TypeError, ValueError) as exc:
            raise ValueError("maxwidth must be a positive integer or None") from exc
        if value <= 0:
            raise ValueError("maxwidth must be a positive integer or None")
        return value


    def _setup_scroll_canvas(self, master: tk.Widget) -> None:
        """Create Canvas and a Frame window for content, bind config events."""
        self.canvas = tk.Canvas(master, highlightthickness=0)
        self._setup_scrollbars(master)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.content_frame = ttk.Frame(self.canvas)
        self.content_window = self.canvas.create_window((0, 0), window=self.content_frame, anchor="nw")
        self.frame = self.content_frame
        self.content_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)


    def _setup_scrollbars(self, master: tk.Widget) -> None:
        """Create vertical and/or horizontal ttk.Scrollbar widgets as requested."""
        if self.layout in ("vertical", "both"):
            self.vsb = ttk.Scrollbar(master, orient="vertical", command=self.canvas.yview)
            self.canvas.configure(yscrollcommand=self.vsb.set)
            self.vsb.pack(side="right", fill="y")
        if self.layout in ("horizontal", "both"):
            self.hsb = ttk.Scrollbar(master, orient="horizontal", command=self.canvas.xview)
            self.canvas.configure(xscrollcommand=self.hsb.set)
            self.hsb.pack(side="bottom", fill="x")


    def _bind_mousewheel_events(self) -> None:
        """Register mousewheel handlers and track descendants for wheel interception."""
        self.canvas.bind_class(self._wheel_bindtag, "<MouseWheel>", self._on_mousewheel, add="+")
        self.canvas.bind_class(self._wheel_bindtag, "<Shift-MouseWheel>", self._on_mousewheel, add="+")
        self._refresh_mousewheel_bindtags()
        self.canvas.bind("<Enter>", self._on_enter, add="+")
        self.canvas.bind("<Leave>", self._on_leave, add="+")
        self.content_frame.bind("<Enter>", self._on_enter, add="+")
        self.content_frame.bind("<Leave>", self._on_leave, add="+")


#endregion
#region Events


    def _on_frame_configure(self, _event: tk.Event) -> None:
        """Update canvas scrollregion and scrollable state."""
        # Always update scrollregion to the full bounding box of the content
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._schedule_width_sync()
        self._refresh_mousewheel_bindtags()
        # update cached scrollable state after content changes
        self._update_scrollable_state()


    def _on_canvas_configure(self, event: tk.Event) -> None:
        """Adjust embedded window size for single-axis layouts and update state."""
        # Only set width/height if the corresponding scrollbar is NOT present
        # This allows the content to expand beyond the visible area and be scrollable
        if self.layout == "vertical":
            self.canvas.itemconfig(self.content_window, width=event.width)
        elif self.layout == "horizontal":
            self.canvas.itemconfig(self.content_window, height=event.height)
        # For "both", do not force width or height, let content grow freely
        # update cached scrollable state after canvas size changes
        self._update_scrollable_state()



    def _on_enter(self, _event: tk.Event) -> None:
        """Recompute scrollable state and refresh descendant wheel bindtags."""
        # Recompute scrollable state to make an informed decision.
        try:
            self._update_scrollable_state()
            self._refresh_mousewheel_bindtags()
        except Exception:
            # safe fallback: assume not scrollable
            pass


    def _on_leave(self, _event: tk.Event) -> None:
        """Keep state fresh when the pointer leaves the ScrollFrame."""
        try:
            self._update_scrollable_state()
        except Exception:
            pass


    def _on_mousewheel(self, event: tk.Event) -> str | None:
        """Map mousewheel to xview/yview; returns 'break' when handled."""
        if not self._event_targets_self(event.widget):
            return
        units = self._get_scroll_units(event)
        # Keep original shift-detection for compatibility; Shift-MouseWheel may also set state.
        is_shift = bool(getattr(event, "state", 0) & 0x1)
        axis = "horizontal" if is_shift else "vertical"
        if self._should_allow_widget_mousewheel(event.widget, axis):
            return
        # If the event originates from a child widget that itself supports
        # scrolling on the requested axis and is currently scrollable, do
        # not intercept the event so the child receives it.
        if is_shift:
            if self.layout in ("horizontal", "both") and self._scrollable_state.get("horizontal", False):
                if self._is_child_widget_scrollable(event.widget, "horizontal"):
                    return
                self._mark_scroll_activity()
                self.canvas.xview_scroll(units, "units")
                return "break"
        else:
            if self.layout in ("vertical", "both") and self._scrollable_state.get("vertical", False):
                if self._is_child_widget_scrollable(event.widget, "vertical"):
                    return
                self._mark_scroll_activity()
                self.canvas.yview_scroll(units, "units")
                return "break"


    def _event_targets_self(self, widget: tk.Widget) -> bool:
        """Return True if widget is the canvas or a descendant."""
        while widget:
            if widget == self.canvas:
                return True
            widget = getattr(widget, "master", None)
        return False


    def _refresh_mousewheel_bindtags(self) -> None:
        """Ensure descendants route wheel events through this ScrollFrame first."""
        for widget in self._iter_mousewheel_widgets():
            self._ensure_mousewheel_bindtag(widget)


    def _iter_mousewheel_widgets(self) -> list[tk.Widget]:
        """Yield this ScrollFrame's wheel-intercepted widgets, excluding nested ScrollFrames."""
        widgets = [self.canvas, self.content_frame]
        pending = list(self.content_frame.winfo_children())
        while pending:
            widget = pending.pop()
            if widget is self:
                continue
            if isinstance(widget, _BaseScrollFrame):
                continue
            widgets.append(widget)
            pending.extend(widget.winfo_children())
        return widgets


    def _ensure_mousewheel_bindtag(self, widget: tk.Widget) -> None:
        """Insert the instance bindtag ahead of widget class bindings."""
        try:
            bindtags = list(widget.bindtags())
        except Exception:
            return
        if self._wheel_bindtag in bindtags:
            return
        insert_at = len(bindtags)
        for index, tag in enumerate(bindtags):
            if isinstance(tag, str) and tag == widget.winfo_class():
                insert_at = index
                break
        bindtags.insert(insert_at, self._wheel_bindtag)
        try:
            widget.bindtags(tuple(bindtags))
        except Exception:
            pass


    def _should_allow_widget_mousewheel(self, widget: tk.Widget, axis: str) -> bool:
        """Allow hovered widgets to use the wheel when the ScrollFrame is idle."""
        if self._is_child_widget_scrollable(widget, axis):
            return True
        if self._wheel_scroll_active:
            return False
        return self._is_child_widget_wheel_sensitive(widget)


    def _is_child_widget_wheel_sensitive(self, widget: tk.Widget) -> bool:
        """Return True when a child widget is expected to consume wheel input itself."""
        w = widget
        while w and w is not self.content_frame and w is not self.canvas:
            if self._widget_has_mousewheel_binding(w):
                return True
            w = getattr(w, "master", None)
        return False


    def _widget_has_mousewheel_binding(self, widget: tk.Widget) -> bool:
        """Detect widgets with class or instance mousewheel bindings."""
        try:
            widget_class = widget.winfo_class()
        except Exception:
            return False
        if any(name in widget_class for name in ("Spinbox", "Combobox")):
            return True
        sequences = ("<MouseWheel>", "<Shift-MouseWheel>")
        try:
            if any(widget.bind(sequence) for sequence in sequences):
                return True
        except Exception:
            return False
        try:
            return any(widget.bind_class(widget_class, sequence) for sequence in sequences)
        except Exception:
            return False


    def _mark_scroll_activity(self) -> None:
        """Keep accidental wheel edits blocked until scrolling pauses briefly."""
        self._wheel_scroll_active = True
        if self._wheel_scroll_job is not None:
            try:
                self.canvas.after_cancel(self._wheel_scroll_job)
            except Exception:
                pass
        self._wheel_scroll_job = self.canvas.after(self._wheel_cooldown_ms, self._clear_scroll_activity)


    def _clear_scroll_activity(self) -> None:
        """Re-enable child widget wheel bindings after the cooldown expires."""
        self._wheel_scroll_job = None
        self._wheel_scroll_active = False


    def _is_child_widget_scrollable(self, widget: tk.Widget, axis: str) -> bool:
        """Return True if a widget (or one of its ancestors up to the content
        frame) has a scroll view (`yview`/`xview`) that is currently scrollable.

        This prevents the ScrollFrame from stealing wheel events when an inner
        widget (e.g., `Text`, `Treeview`, inner `Canvas`) can handle them.
        """
        w = widget
        # Walk up the widget hierarchy until we reach the content frame or canvas.
        while w and w is not self.content_frame and w is not self.canvas:
            view = getattr(w, "yview" if axis == "vertical" else "xview", None)
            if callable(view):
                try:
                    first, last = view()
                    # If the child view does not show the whole range, it's scrollable.
                    if not (abs(first - 0.0) < 1e-9 and abs(last - 1.0) < 1e-9):
                        return True
                except Exception:
                    # If we can't reliably query the widget, be conservative and
                    # assume it can handle the event so we don't steal it.
                    return True
            w = getattr(w, "master", None)
        return False


#endregion
#region Helpers


    @staticmethod
    def _get_scroll_units(event: tk.Event) -> int:
        """Turn event.delta into integer scroll units."""
        delta = getattr(event, "delta", 0)
        if delta:
            if abs(delta) >= 120:
                magnitude = abs(delta) // 120
            else:
                magnitude = 1
            return -int(delta / abs(delta)) * magnitude
        return 0


    def _schedule_width_sync(self) -> None:
        """Keep vertical layouts wide enough for their content without x-scrolling."""
        if self.layout != "vertical" or self._width_sync_job is not None:
            return
        self._width_sync_job = self.canvas.after_idle(self._sync_vertical_width)


    def _sync_vertical_width(self) -> None:
        """Update the canvas requested width to the content's requested width."""
        self._width_sync_job = None
        if self.layout != "vertical":
            return
        try:
            required_width = self.content_frame.winfo_reqwidth()
            current_request = int(float(self.canvas.cget("width")))
        except Exception:
            return
        if self._maxwidth is not None:
            required_width = min(required_width, self._maxwidth)
        if required_width > 1 and current_request != required_width:
            self.canvas.configure(width=required_width)


    def set_maxwidth(self, maxwidth: int | None) -> None:
        """Set or clear the width cap used by vertical width synchronization."""
        self._maxwidth = self._validate_maxwidth(maxwidth)
        if self.layout == "vertical":
            self._schedule_width_sync()


    def _update_scrollable_state(self) -> None:
        """Recompute cached scrollable state and emit <<ScrollStateChanged>> if changed."""
        prev = getattr(self, "_scrollable_state", None)
        v = self._is_axis_scrollable("vertical")
        h = self._is_axis_scrollable("horizontal")
        self._scrollable_state = {"vertical": v, "horizontal": h}
        if prev is None or prev != self._scrollable_state:
            try:
                self.canvas.event_generate("<<ScrollStateChanged>>", when="tail")
            except Exception:
                pass


    def _is_axis_scrollable(self, axis: str) -> bool:
        """Return True if the content is larger than the canvas view on the axis."""
        try:
            if axis == "vertical":
                first, last = self.canvas.yview()
            elif axis == "horizontal":
                first, last = self.canvas.xview()
            else:
                raise ValueError("axis must be 'vertical' or 'horizontal'")
        except Exception:
            return False
        # If the whole content is visible, view() returns (0.0, 1.0)
        return not (abs(first - 0.0) < 1e-9 and abs(last - 1.0) < 1e-9)


#endregion
#region ScrollFrame


class ScrollFrame(ttk.Frame, _BaseScrollFrame):
    """Drop-in ttk.Frame container with an inner scrollable .frame.

    Use layout='vertical'|'horizontal'|'both'. Pass label to wrap
    content in a ttk.LabelFrame.
    """
    def __init__(self, master: tk.Widget, layout: str = "vertical", label: str | None = None, maxwidth: int | None = None, *args: object, **kwargs: object) -> None:
        """Initialize the ScrollFrame container."""
        # Initialize the outer frame (this instance) which remains the widget to pack/grid.
        ttk.Frame.__init__(self, master, *args, **kwargs)
        if label is not None:
            self._inner_container = ttk.LabelFrame(self, text=label)
            self._inner_container.pack(fill="both", expand=True)
            base_parent = self._inner_container
        else:
            self._inner_container = None
            base_parent = self
        # Initialize the scrollable machinery using the chosen container as the master.
        _BaseScrollFrame.__init__(self, base_parent, layout, maxwidth, *args, **kwargs)


#endregion
#region Demo


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Scrollable Frame Demo")
    root.geometry("540x420")
    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True)
    # Vertical scrollbar
    tab1 = ttk.Frame(notebook)
    notebook.add(tab1, text="Vertical")
    scrollable_v = ScrollFrame(tab1, layout="vertical")
    scrollable_v.pack(fill="both", expand=True)
    for i in range(20):
        ttk.Button(scrollable_v.frame, text=f"Button {i+1}").pack(side="top", fill="x", padx=10, pady=2)
    # Horizontal scrollbar
    tab2 = ttk.Frame(notebook)
    notebook.add(tab2, text="Horizontal")
    scrollable_h = ScrollFrame(tab2, layout="horizontal")
    scrollable_h.pack(fill="both", expand=True)
    for i in range(10):
        ttk.Button(scrollable_h.frame, text=f"Wide Button {i+1}" * 5).pack(side="left", padx=10, pady=2)
    # Both scrollbars
    tab3 = ttk.Frame(notebook)
    notebook.add(tab3, text="Both")
    scrollable_both = ScrollFrame(tab3, layout="both")
    scrollable_both.pack(fill="both", expand=True)
    for i in range(15):
        for j in range(5):
            ttk.Button(scrollable_both.frame, text=f"Button ({i+1},{j+1})").grid(row=i, column=j, padx=10, pady=10, sticky="ew")
    # LabelFrame example
    tab4 = ttk.Frame(notebook)
    notebook.add(tab4, text="LabelFrame")
    scrollable_label = ScrollFrame(tab4, layout="vertical", label="Labeled Scrollable Frame")
    scrollable_label.pack(fill="both", expand=True)
    for i in range(10):
        ttk.Label(scrollable_label.frame, text=f"Label {i+1}").pack(anchor="w", padx=10, pady=2)
    # Wheel-sensitive child widgets
    tab5 = ttk.Frame(notebook)
    notebook.add(tab5, text="Wheel Input")
    scrollable_inputs = ScrollFrame(tab5, layout="vertical", label="Wheel Input Demo")
    scrollable_inputs.pack(fill="both", expand=True)
    ttk.Label(scrollable_inputs.frame, text=("Scroll the frame, then hover the controls below. While the frame is scrolling, spinbox/combobox wheels are blocked; they work again once scrolling stops."), wraplength=480, justify="left").pack(anchor="w", padx=10, pady=(10, 8))
    speed_var = tk.IntVar(value=5)
    mode_var = tk.StringVar(value="2")
    controls = ttk.Frame(scrollable_inputs.frame)
    controls.pack(fill="x", padx=10, pady=(0, 10))
    ttk.Label(controls, text="Speed:").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
    ttk.Spinbox(controls, from_=0, to=10, textvariable=speed_var, width=8).grid(row=0, column=1, sticky="w", pady=4)
    ttk.Label(controls, text="Mode:").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
    ttk.Combobox(controls, textvariable=mode_var, values=["1", "2", "3"], state="readonly", width=16).grid(row=1, column=1, sticky="w", pady=4)
    ttk.Separator(scrollable_inputs.frame, orient="horizontal").pack(fill="x", padx=10, pady=8)
    ttk.Label(scrollable_inputs.frame, text="Hovered scrollable children still keep their own wheel behavior:").pack(anchor="w", padx=10, pady=(0, 6))
    sample_text = tk.Text(scrollable_inputs.frame, width=56, height=8, wrap="word")
    sample_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
    sample_text.insert("1.0","\n".join(f"Text line {i + 1}: this widget should continue to scroll while hovered." for i in range(20) ))
    root.mainloop()


#endregion
