"""
Provides a PopUpZoom widget for Tkinter, enabling interactive image zooming in a popup window.

## API
- Class: `PopUpZoom(widget: Label, **kwargs)`

### Constructor kwargs:
- zoom_factor (float): Initial zoom level. Default: 1.75
- min_zoom_factor (float): Minimum zoom level. Default: 1.25
- max_zoom_factor (float): Maximum zoom level. Default: 10.0
- max_image_size (int): Max dimension for internal image. Default: 4096
- corner_radius (int): Popup corner radius in pixels. Default: 8
- popup_size (int): Popup window size in pixels. Default: 400
- min_popup_size (int): Minimum popup size. Default: 100
- max_popup_size (int): Maximum popup size. Default: 600
- zoom_enabled (bool): Whether zoom is enabled. Default: False
- full_image_mode (bool): Show full image instead of zoomed region. Default: False

### Public Methods:
- configure(**kwargs) / config(**kwargs): Update configuration at runtime.
- set_image(image: Image.Image) -> None: Set the image to be used for zooming.
- show_popup(event: Event) -> None: Show the popup window and update based on mouse position.
- hide_popup(event: Event) -> None: Hide the popup window.
- unbind() -> None: Remove all event bindings and cleanup.

### Public Properties (BooleanVar):
- zoom_enabled: Controls whether zoom is enabled.
- full_image_mode: When true, disables wheel zooming and shows the full image scaled to popup.

## Notes
- The widget expects a Tkinter Label with an image set.
- The popup is automatically positioned near the mouse cursor and constrained to the screen.
- Use Shift+MouseWheel to resize the popup window.
- Use MouseWheel to adjust zoom level (disabled in full_image_mode).

## Example
```python
import tkinter as tk
from PIL import Image
from nenotk.widgets.popup_zoom import PopUpZoom

root = tk.Tk()
label = tk.Label(root)
label.pack()

zoom = PopUpZoom(label, zoom_factor=2.0, popup_size=300)
img = Image.open("example.png")
zoom.set_image(img)
zoom.configure(zoom_enabled=True)

root.mainloop()
```
"""
#region Imports


# tkinter
from tkinter import Event, Label, Toplevel, BooleanVar, Canvas

# Third-Party
from PIL import Image, ImageTk, ImageDraw, ImageChops

# Typing
from typing import Any, Dict, List, Optional


#endregion
#region Exports


__all__ = ["PopUpZoom"]


#endregion
#region PopUpZoom


class PopUpZoom:
    """Interactive image zoom popup for Tkinter Label widgets."""

    #region Class Defaults

    # Class-level defaults (used when kwargs not provided)
    ZOOM_FACTOR: float = 1.75
    MIN_ZOOM_FACTOR: float = 1.25
    MAX_ZOOM_FACTOR: float = 10.0
    MAX_IMAGE_SIZE: int = 4096
    CORNER_RADIUS: int = 8
    POPUP_SIZE: int = 400
    MIN_POPUP_SIZE: int = 100
    MAX_POPUP_SIZE: int = 600
    ZOOM_ENABLED: bool = False
    FULL_IMAGE_MODE: bool = False

    # List of valid configurable parameters
    PARAMS: List[str] = [
        "zoom_factor", "min_zoom_factor", "max_zoom_factor",
        "max_image_size", "corner_radius", "popup_size",
        "min_popup_size", "max_popup_size", "zoom_enabled", "full_image_mode"
    ]

    #endregion
    #region Init

    def __init__(self, widget: 'Label', **kwargs: Any) -> None:
        """Initialize PopUpZoom with configurable parameters.

        Args:
            widget: The Tkinter Label widget to attach zoom behavior to.
            **kwargs: Configuration options (see class PARAMS for valid keys).
        """
        self.widget: Optional[Label] = widget
        self.original_image: Optional[Image.Image] = None

        # Create BooleanVars for interactive state
        self.zoom_enabled = BooleanVar(value=self.ZOOM_ENABLED)
        self.full_image_mode = BooleanVar(value=self.FULL_IMAGE_MODE)

        # Apply kwargs (sets instance attributes from defaults or provided values)
        self._apply_kwargs(kwargs, initialize=True)

        # Set up the zoom window and bind events
        self._create_popup_window()
        self._bind_events()


    def _create_popup_window(self) -> None:
        """Create the popup window and canvas for displaying zoomed images."""
        self.popup = Toplevel(self.widget)
        self.popup.withdraw()
        self.popup.overrideredirect(True)
        self.popup.wm_attributes("-transparentcolor", self.popup["bg"])
        self.zoom_canvas = Canvas(
            self.popup,
            width=self.popup_size,
            height=self.popup_size,
            highlightthickness=0,
            bg=self.popup["bg"]
        )
        self.zoom_canvas.pack()


    def _bind_events(self) -> None:
        """Bind mouse events to the widget for zoom functionality."""
        if not self.widget:
            return
        self._motion_id = self.widget.bind("<Motion>", self.show_popup, add="+")
        self._leave_id = self.widget.bind("<Leave>", self.hide_popup, add="+")
        self._click_id = self.widget.bind("<Button-1>", self.hide_popup, add="+")
        self._wheel_id = self.widget.bind("<MouseWheel>", self._zoom, add="+")
        self._shift_wheel_id = self.widget.bind("<Shift-MouseWheel>", self._resize_popup, add="+")


    #endregion
    #region Public API


    def set_image(self, image: Image.Image) -> None:
        """Set the image to be used for zooming.

        Args:
            image: The PIL Image object to display and zoom.
        """
        if self.original_image is image:
            return
        self.original_image = image
        self._resize_original_image()


    def show_popup(self, event: Event) -> None:
        """Show the popup window and update its image based on mouse position."""
        if event is None or not self.zoom_enabled.get() or not self.original_image:
            return
        self._show_and_update(event)


    def hide_popup(self, event: Optional[Event] = None) -> None:
        """Hide the popup window."""
        if hasattr(self, "popup") and self.popup:
            self.popup.withdraw()


    def configure(self, **kwargs: Any) -> None:
        """Update configuration options at runtime.

        Args:
            **kwargs: Configuration options (see class PARAMS for valid keys).

        Raises:
            TypeError: If an invalid parameter name is provided.
        """
        if not kwargs:
            return
        self._apply_kwargs(kwargs, initialize=False)
        # Update popup canvas size if popup_size changed
        if hasattr(self, "zoom_canvas") and self.zoom_canvas:
            self.zoom_canvas.config(width=self.popup_size, height=self.popup_size)


    def config(self, **kwargs: Any) -> None:
        """Alias for configure()."""
        self.configure(**kwargs)


    def unbind(self) -> None:
        """Remove all event bindings from the widget and cleanup."""
        if self.widget:
            try:
                if hasattr(self, "_motion_id"):
                    self.widget.unbind("<Motion>", self._motion_id)
                if hasattr(self, "_leave_id"):
                    self.widget.unbind("<Leave>", self._leave_id)
                if hasattr(self, "_click_id"):
                    self.widget.unbind("<Button-1>", self._click_id)
                if hasattr(self, "_wheel_id"):
                    self.widget.unbind("<MouseWheel>", self._wheel_id)
                if hasattr(self, "_shift_wheel_id"):
                    self.widget.unbind("<Shift-MouseWheel>", self._shift_wheel_id)
            except Exception:
                pass
        self.hide_popup(None)
        if hasattr(self, "popup") and self.popup:
            try:
                self.popup.destroy()
            except Exception:
                pass


    #endregion
    #region Config Helpers


    def _apply_kwargs(self, kwargs: Dict[str, Any], initialize: bool) -> None:
        """Validate and apply kwargs to instance attributes.

        Args:
            kwargs: Dictionary of parameter names and values.
            initialize: If True, set all parameters from defaults; if False, only update provided.

        Raises:
            TypeError: If an invalid parameter name is provided.
        """
        # Validate keys
        invalid = [k for k in kwargs if k not in self.PARAMS]
        if invalid:
            raise TypeError(f"Invalid parameter(s): {', '.join(invalid)}. "
                            f"Valid parameters are: {', '.join(self.PARAMS)}")

        if initialize:
            # Set all parameters from class defaults, overriding with kwargs
            for param in self.PARAMS:
                default_value = getattr(self, param.upper())
                value = kwargs.get(param, default_value)
                self._set_param(param, value)
        else:
            # Only update provided parameters
            for param, value in kwargs.items():
                self._set_param(param, value)


    def _set_param(self, param: str, value: Any) -> None:
        """Set a single parameter, handling BooleanVar specially."""
        if param == "zoom_enabled":
            if isinstance(value, bool):
                self.zoom_enabled.set(value)
            elif hasattr(value, "get"):
                self.zoom_enabled.set(value.get())
        elif param == "full_image_mode":
            if isinstance(value, bool):
                self.full_image_mode.set(value)
            elif hasattr(value, "get"):
                self.full_image_mode.set(value.get())
        else:
            setattr(self, param, value)


    #endregion
    #region Zoom Logic


    def _show_and_update(self, event: Event) -> None:
        """Update popup position and image based on mouse event."""
        x, y = event.x, event.y
        new_x, new_y = self._compute_popup_position(event)
        self.popup.geometry(f"+{new_x}+{new_y}")
        if self.full_image_mode.get():
            self._update_full_image()
            return
        display_w, display_h, pad_x, pad_y, scale_x, scale_y = self._get_display_metrics()
        if display_w == 0 or display_h == 0 or scale_x == 0 or scale_y == 0:
            return
        img_x = self._clamp((x - pad_x) / scale_x, 0, self.original_image.width)
        img_y = self._clamp((y - pad_y) / scale_y, 0, self.original_image.height)
        self._update_popup_image(img_x, img_y)


    def _zoom(self, event: Event) -> None:
        """Adjust the zoom factor based on the mouse wheel event."""
        if event is None or self.full_image_mode.get():
            return
        delta_direction = 1 if event.delta > 0 else -1 if event.delta < 0 else 0
        if delta_direction == 0:
            return
        step = self.min_zoom_factor * delta_direction
        self.zoom_factor = self._clamp(self.zoom_factor + step, self.min_zoom_factor, self.max_zoom_factor)
        self.show_popup(event)


    def _resize_popup(self, event: Event) -> None:
        """Adjust the popup size based on Shift+MouseWheel event."""
        if event is None:
            return
        delta_direction = 1 if event.delta > 0 else -1 if event.delta < 0 else 0
        if delta_direction == 0:
            return
        self.popup_size = self._clamp(self.popup_size + 20 * delta_direction, self.min_popup_size, self.max_popup_size)
        self.zoom_canvas.config(width=self.popup_size, height=self.popup_size)
        self.show_popup(event)


    def _update_popup_image(self, img_x: float, img_y: float) -> None:
        """Update the popup image based on calculated coordinates."""
        left, top, right, bottom = self._calculate_coordinates(img_x, img_y)
        if left < right and top < bottom:
            self._create_zoomed_image(left, top, right, bottom)
            self.popup.deiconify()
        else:
            self.popup.withdraw()


    def _update_full_image(self) -> None:
        """Show the entire image scaled to the popup while preserving aspect ratio."""
        width, height = self.original_image.size
        self._create_zoomed_image(0, 0, width, height, force_full_image=True)
        self.popup.deiconify()


    def _create_zoomed_image(self, left: int, top: int, right: int, bottom: int, force_full_image: bool = False) -> None:
        """Create and display the zoomed image in the zoom window."""
        cropped_image, new_width, new_height = self._crop_and_resize_image(left, top, right, bottom)
        high_zoom = self.zoom_factor >= 4 and not force_full_image
        resize_method = Image.Resampling.NEAREST if high_zoom else Image.Resampling.LANCZOS
        zoomed_image = cropped_image.resize((new_width, new_height), resize_method).convert("RGBA")
        transparent_background = Image.new("RGBA", (new_width, new_height), (0, 0, 0, 0))
        self._apply_corner_radius(new_width, new_height, zoomed_image, transparent_background)
        self._delete_zoom_image()
        self._display_zoomed_image(new_width, new_height, transparent_background)


    def _display_zoomed_image(self, new_width: int, new_height: int, transparent_background: Image.Image) -> None:
        """Display the processed zoom image on the canvas."""
        self.zoom_photo_image = ImageTk.PhotoImage(transparent_background)
        self.zoom_canvas.delete("all")
        x = (self.popup_size - new_width) // 2
        y = (self.popup_size - new_height) // 2
        self.zoom_canvas.create_image(x, y, anchor="nw", image=self.zoom_photo_image)


    #endregion
    #region Image Processing


    def _crop_and_resize_image(self, left: int, top: int, right: int, bottom: int) -> tuple[Image.Image, int, int]:
        """Crop and calculate resize dimensions for the zoomed area."""
        cropped_image = self.original_image.crop((left, top, right, bottom))
        aspect_ratio = cropped_image.width / cropped_image.height
        if aspect_ratio > 1:
            new_width = self.popup_size
            new_height = int(self.popup_size / aspect_ratio)
        else:
            new_height = self.popup_size
            new_width = int(self.popup_size * aspect_ratio)
        return cropped_image, new_width, new_height


    def _apply_corner_radius(self, new_width: int, new_height: int, zoomed_image: Image.Image, transparent_background: Image.Image) -> None:
        """Apply rounded corners to the zoomed image."""
        if self.corner_radius >= 1:
            mask = Image.new('L', (new_width, new_height), 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle((0, 0, new_width, new_height), radius=self.corner_radius, fill=255)
            alpha_channel = zoomed_image.getchannel("A")
            combined_mask = ImageChops.multiply(alpha_channel, mask)
            transparent_background.paste(zoomed_image, (0, 0), combined_mask)
        else:
            transparent_background.paste(zoomed_image, (0, 0), zoomed_image)


    def _resize_original_image(self) -> None:
        """Resize the original image if it's too large."""
        max_size = self.max_image_size
        img_copy = self.original_image.copy()
        img_copy.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        self.original_image = img_copy.convert("RGBA")


    #endregion
    #region Coordinate Helpers


    def _calculate_coordinates(self, img_x: float, img_y: float) -> tuple[int, int, int, int]:
        """Calculate the coordinates for the zoomed image."""
        width, height = self.original_image.width, self.original_image.height
        span = int(round(self.popup_size / self.zoom_factor))
        span = max(1, min(span, width, height))
        half_span = span / 2

        if width <= span:
            left, right = 0, width
        else:
            min_center_x = half_span
            max_center_x = width - (span - half_span)
            center_x = self._clamp(img_x, min_center_x, max_center_x)
            left = int(round(center_x - half_span))
            right = left + span
            if right > width:
                right = width
                left = right - span
            if left < 0:
                left = 0
                right = span

        if height <= span:
            top, bottom = 0, height
        else:
            min_center_y = half_span
            max_center_y = height - (span - half_span)
            center_y = self._clamp(img_y, min_center_y, max_center_y)
            top = int(round(center_y - half_span))
            bottom = top + span
            if bottom > height:
                bottom = height
                top = bottom - span
            if top < 0:
                top = 0
                bottom = span

        return int(left), int(top), int(right), int(bottom)


    def _compute_popup_position(self, event: Event) -> tuple[int, int]:
        """Return popup coordinates constrained to the visible screen area."""
        screen_width = self.widget.winfo_screenwidth()
        screen_height = self.widget.winfo_screenheight()
        default_x = event.x_root + self.popup_size // 10
        if default_x + self.popup_size > screen_width:
            default_x = event.x_root - self.popup_size - 20
        x_limit = max(0, screen_width - self.popup_size)
        y_limit = max(0, screen_height - self.popup_size)
        new_x = self._clamp(default_x, 0, x_limit)
        default_y = event.y_root - self.popup_size // 2
        new_y = self._clamp(default_y, 0, y_limit)
        return new_x, new_y


    #endregion
    #region Utility


    def _delete_zoom_image(self) -> None:
        """Delete the cached zoom image to free memory."""
        if hasattr(self, "zoom_photo_image"):
            try:
                del self.zoom_photo_image
            except Exception:
                pass


    def _clamp(self, value: float, min_value: float, max_value: float) -> float:
        """Clamp a value between the provided bounds."""
        if max_value < min_value:
            return min_value
        return max(min_value, min(value, max_value))


    def _get_display_metrics(self) -> tuple[float, float, float, float, float, float]:
        """Get display metrics for coordinate mapping."""
        null = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
        if not self.widget or not self.original_image:
            return null
        widget_w, widget_h = self.widget.winfo_width(), self.widget.winfo_height()
        if widget_w <= 0 or widget_h <= 0:
            return null
        img_w, img_h = self.original_image.size
        if img_w == 0 or img_h == 0:
            return null
        image_obj = getattr(self.widget, "image", None)
        width_fn = getattr(image_obj, "width", None) if image_obj is not None else None
        height_fn = getattr(image_obj, "height", None) if image_obj is not None else None
        if callable(width_fn) and callable(height_fn):
            display_w = float(width_fn())
            display_h = float(height_fn())
        else:
            scale = min(widget_w / img_w, widget_h / img_h, 1.0)
            display_w = img_w * scale
            display_h = img_h * scale
        pad_x = (widget_w - display_w) / 2
        pad_y = (widget_h - display_h) / 2
        scale_x = display_w / img_w if img_w else 0.0
        scale_y = display_h / img_h if img_h else 0.0
        return display_w, display_h, pad_x, pad_y, scale_x, scale_y


#endregion
#region Demo


if __name__ == "__main__":
    import tkinter as tk

    def demo() -> None:
        """Run a demonstration of the PopUpZoom widget."""
        root = tk.Tk()
        # Create a gradient test image
        width, height = 800, 600
        img = Image.new("RGB", (width, height))
        for y in range(height):
            for x in range(width):
                r = int(255 * x / width)
                g = int(255 * y / height)
                b = int(255 * (1 - x / width))
                img.putpixel((x, y), (r, g, b))
        # Resize for display
        display_img = img.copy()
        display_img.thumbnail((500, 400), Image.Resampling.LANCZOS)
        tk_img = ImageTk.PhotoImage(display_img)
        # Create label and attach PopUpZoom
        label = tk.Label(root, image=tk_img)
        label.image = tk_img
        label.pack(pady=20)
        zoom = PopUpZoom(label, zoom_factor=2.0, popup_size=300, corner_radius=12, zoom_enabled=True)
        zoom.set_image(img)
        # Control buttons
        frame = tk.Frame(root)
        frame.pack(pady=10)

        def toggle_zoom() -> None:
            current = zoom.zoom_enabled.get()
            zoom.configure(zoom_enabled=not current)
            btn_zoom.config(text=f"Zoom: {'ON' if not current else 'OFF'}")

        def toggle_full() -> None:
            current = zoom.full_image_mode.get()
            zoom.configure(full_image_mode=not current)
            btn_full.config(text=f"Full Image: {'ON' if not current else 'OFF'}")

        btn_zoom = tk.Button(frame, text="Zoom: ON", command=toggle_zoom, width=15)
        btn_zoom.pack(side="left", padx=5)
        btn_full = tk.Button(frame, text="Full Image: OFF", command=toggle_full, width=15)
        btn_full.pack(side="left", padx=5)
        info_label = tk.Label(root, text="Hover over image to zoom. Use MouseWheel to adjust zoom, Shift+MouseWheel to resize popup.")
        info_label.pack(pady=5)
        root.mainloop()

    demo()


#endregion
