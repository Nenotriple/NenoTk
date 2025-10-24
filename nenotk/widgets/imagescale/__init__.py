"""
# Purpose
Provides a Tkinter `ImageScale` widget (label subclass) that resizes images with optional aspect preservation and delayed high-quality redraws.

## API
- Class: `ImageScale(master=None, image_path="", width=None, height=None, keep_aspect=True, draw_method="lanczos", scale_mode="fill", hq_delay_ms=200, **kwargs) -> tk.Label`
    - `set_image(image_path_or_pil)`: load from filesystem path or `PIL.Image.Image` instance.
    - `set_image_from_pil(pil_image)`: convenience wrapper for in-memory images.
    - `refresh_displayed_image()`: force re-render using current widget dimensions.
    - `set_keep_aspect(enabled)`: toggle aspect ratio preservation.
    - `set_scale_mode(mode)`: switch between "fill" and "center" behaviour.
    - `clear()`: remove the current image and reset state.
    - `get_displayed_pil_image()`: return last rendered `PIL.Image` (or `None`).

## Notes
- Supports PIL draw methods: nearest, bilinear, bicubic, lanczos (default).
- Uses fast nearest-neighbour preview during resize, followed by a delayed high-quality render (`hq_delay_ms`).
- Integrates with `tkinter` `<Configure>` events to react to container resizes automatically.

## Example
```
import tkinter as tk
import nenotk as ntk

root = tk.Tk()
widget = ntk.ImageScale(root, image_path="photo.jpg", scale_mode="center")
widget.pack(fill="both", expand=True)
root.mainloop()
```
"""
#region Imports


# UI
import tkinter as tk

# Third-party
from PIL import Image, ImageTk


#endregion
#region Constants


DRAW_METHODS = {
    'nearest': Image.Resampling.NEAREST,
    'bilinear': Image.Resampling.BILINEAR,
    'bicubic': Image.Resampling.BICUBIC,
    'lanczos': Image.Resampling.LANCZOS
}


#endregion
#region ImageScale


class ImageScale(tk.Label):
    """
    A Tkinter Label widget that displays a scalable image with optional aspect ratio preservation.

    Args:
        master: Parent widget.
        image_path (str | PIL.Image.Image): Path to the image file or a PIL Image instance.
        width (int, optional): Initial width of the widget.
        height (int, optional): Initial height of the widget.
        keep_aspect (bool): Whether to maintain aspect ratio when scaling.
        draw_method (str): The draw method to use ('nearest', 'bilinear', 'bicubic', or 'lanczos').
        scale_mode (str): "fill" scales the image to fill the widget. "center" shows the image at its original size centered within the widget; if the image is larger than the widget, it gets scaled using "fill".
        hq_delay_ms (int): Delay in milliseconds before applying high-quality resize after resizing stops.
        *args: Additional positional arguments for tk.Label.
        **kwargs: Additional keyword arguments for tk.Label.
    """

    def __init__(self,
                 master: tk.Widget = None,
                 image_path: str = "",
                 width: int = None,
                 height: int = None,
                 keep_aspect: bool = True,
                 draw_method: str = 'lanczos',
                 scale_mode: str = "fill",
                 hq_delay_ms: int = 200,
                 *args,
                 **kwargs
        ):
        super().__init__(master, *args, **kwargs)
        # args
        self.image_path = ""
        self._init_dimensions(width, height)
        self.keep_aspect = keep_aspect
        self.draw_method = self._validate_draw_method(draw_method)
        scale_mode = self._init_scale_mode(scale_mode)
        self.resize_delay_ms = int(hq_delay_ms)
        # vars
        self.displayed_image = None
        self.original_image = None
        self.resize_timer = None
        self._last_pil = None
        # Bind event
        self.bind("<Configure>", self._resize, add="+")
        # Load image
        if image_path:
            self.set_image(image_path)


    def _init_dimensions(self, width: int, height: int):
        """Initialize the given dimensions of the label."""
        if width is not None and height is not None:
            self.config(width=width, height=height)
        elif width is not None:
            self.config(width=width, height=width)
        elif height is not None:
            self.config(width=height, height=height)
        else:
            self.config(width=10, height=10)


    def _init_scale_mode(self, scale_mode: str):
        """Initialize the given scale mode."""
        scale_mode = scale_mode.lower()
        if scale_mode not in ["fill", "center"]:
            raise ValueError("scale_mode must be either 'fill' or 'center'")
        self.scale_mode = scale_mode
        return scale_mode


    # --- Public API ---
    def set_image(self, image_path: str | Image.Image):
        """Update the displayed image.
        Accepts:
          - str: filesystem path
          - PIL.Image.Image: in-memory PIL image
        """
        self.image_path = ""
        if isinstance(image_path, Image.Image):
            self.original_image = image_path.copy()
        elif isinstance(image_path, str):
            self.image_path = image_path
            try:
                with Image.open(image_path) as img:
                    self.original_image = img.copy()
            except Exception as e:
                raise IOError(f"Failed to open image '{image_path}': {e}") from e
        else:
            raise TypeError("image_path must be a file path (str) or PIL.Image.Image")
        if self.winfo_width() > 1 and self.winfo_height() > 1:
            self._final_resize(self.winfo_width(), self.winfo_height())
        else:
            self._final_resize(self.original_image.width, self.original_image.height)


    def set_image_from_pil(self, pil_image: Image.Image):
        """Convenience: set an in-memory PIL.Image.Image as the widget image."""
        if not isinstance(pil_image, Image.Image):
            raise TypeError("pil_image must be a PIL.Image.Image")
        self.set_image(pil_image)


    def refresh_displayed_image(self):
        if self.original_image:
            self._final_resize(self.winfo_width(), self.winfo_height())


    def set_draw_method(self, draw_method: str):
        """Update the draw method and re-render the image.
        Args:
            draw_method (str): 'nearest', 'bilinear', 'bicubic', or 'lanczos'
        """
        self.draw_method = self._validate_draw_method(draw_method)
        self.refresh_displayed_image()


    def set_keep_aspect(self, keep_aspect: bool):
        """Update the keep_aspect setting and re-render the image.
        Args:
            keep_aspect (bool): True to maintain aspect ratio, False otherwise.
        """
        self.keep_aspect = keep_aspect
        self.refresh_displayed_image()


    def set_scale_mode(self, scale_mode: str):
        """Update the scale mode and re-render the image.
        Args:
            scale_mode (str): "fill" or "center"
        Raises:
            ValueError: If scale_mode is not valid.
        """
        scale_mode = scale_mode.lower()
        if scale_mode not in ["fill", "center"]:
            raise ValueError("scale_mode must be either 'fill' or 'center'")
        self.scale_mode = scale_mode
        self.refresh_displayed_image()


    def clear(self):
        """Clear the displayed image and reset internal image references."""
        self.image_path = ""
        self.original_image = None
        self.displayed_image = None
        self.config(image='')


    def get_image_path(self):
        """Get the current image path.
        Returns:
            str: The path of the currently displayed image, or empty string if no image is loaded.
        """
        return self.image_path


    def get_displayed_pil_image(self):
        """Get the currently displayed image as a PIL Image object.
        Returns:
            PIL.Image: The currently displayed image, or None if no image is loaded.
        """
        return self._last_pil


    # --- Resize handling ---
    def _resize(self, event: tk.Event):
        """Handle resize events by updating the image size."""
        if not self.original_image:
            return
        if self.resize_timer is not None:
            self.after_cancel(self.resize_timer)
        self._resize_image(event.width, event.height, high_quality=False)
        self.resize_timer = self.after(self.resize_delay_ms, lambda: self._final_resize(event.width, event.height))


    def _final_resize(self, width: int, height: int):
        """Perform final high-quality resize after resizing stops."""
        self.resize_timer = None
        self._resize_image(width, height, high_quality=True)


    # --- Internal helpers ---
    def _resize_image(self, width: int, height: int, high_quality: bool = False):
        """Resize the image to the specified dimensions.
        Args:
            width (int): Target width
            height (int): Target height
            high_quality (bool): Use the high-quality draw method
        """
        if not self.original_image or width <= 0 or height <= 0:
            return
        current_method = self.draw_method if high_quality else Image.Resampling.NEAREST
        orig_width, orig_height = self.original_image.size
        if self.scale_mode == "center":
            if orig_width <= width and orig_height <= height:
                new_width, new_height = orig_width, orig_height
            elif self.keep_aspect:
                new_width, new_height = self._fit_with_aspect(width, height, orig_width, orig_height)
            else:
                new_width, new_height = width, height
            resized = self.original_image.resize((new_width, new_height), current_method)
            # keep a PIL copy for callers
            self._last_pil = resized.copy()
            self.displayed_image = ImageTk.PhotoImage(resized)
            self.config(image=self.displayed_image, anchor="center")
            return
        # scale_mode == "fill" (fit within bounds while preserving aspect if requested)
        if self.keep_aspect:
            new_width, new_height = self._fit_with_aspect(width, height, orig_width, orig_height)
        else:
            new_width, new_height = width, height
        resized = self.original_image.resize((new_width, new_height), current_method)
        # keep a PIL copy for callers
        self._last_pil = resized.copy()
        self.displayed_image = ImageTk.PhotoImage(resized)
        self.config(image=self.displayed_image)


    def _validate_draw_method(self, method: str):
        """Validate and return the PIL draw method constant.
        Args:
            method (str): The draw method name
        Returns:
            int: PIL draw method constant
        Raises:
            ValueError: If the draw method is not supported
        """
        method = method.lower()
        if method not in DRAW_METHODS:
            raise ValueError(f"Unsupported draw method: {method}. Choose from {', '.join(DRAW_METHODS.keys())}")
        return DRAW_METHODS[method]


    def _fit_with_aspect(self, target_width: int, target_height: int, orig_width: int, orig_height: int):
        """Return (w, h) that fit within target while preserving aspect ratio."""
        ratio = min(target_width / orig_width, target_height / orig_height)
        new_width = max(1, int(orig_width * ratio))
        new_height = max(1, int(orig_height * ratio))
        return new_width, new_height


#endregion
#region Demo


if __name__ == "__main__":
    from tkinter import filedialog
    root = tk.Tk()

    path = filedialog.askopenfilename(title="Select image", filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp;")])

    image = ImageScale(root, image_path=path, scale_mode="center")
    image.pack(fill=tk.BOTH, expand=True)

    root.mainloop()

