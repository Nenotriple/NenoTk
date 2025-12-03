# ImageZoomWidget and SplitImage

Interactive image viewer widgets for Tkinter with zoom, pan, GIF playback, and side-by-side comparison.

## Features

- Mouse wheel zoom with cursor-centric focus; click-drag to pan.
- Fit-to-canvas, programmatic pan/zoom, and snapshot of the visible region.
- High-quality full render with fast previews for smooth interaction.
- GIF animation playback (disables pan/zoom events while playing).
- `SplitImage`: two synchronized panes for side-by-side comparison.
- Optional callbacks for render, zoom, pan, and error events.

## Quick Start

```python
import tkinter as tk
import nenotk as ntk

root = tk.Tk()
viewer = ntk.ImageZoomWidget(root)
viewer.pack(fill="both", expand=True)
viewer.load_image("example.png")

root.mainloop()
```

## API (Essentials)

- **Class:** `ImageZoomWidget(master, on_render_done=None, on_zoom_change=None, on_pan_change=None, on_error=None, **kwargs)`
  - Methods:
    - `load_image(path, keep_view=False)`
    - `set_image(pil_image, keep_view=False)`
    - `force_fit_to_canvas()`
    - `set_pan_and_zoom(scale, pan_x, pan_y)`
    - `get_pan_and_zoom() -> (scale, pan_x, pan_y)`
    - `get_zoom_percent() -> float`
    - `set_zoom_percent(percent: float)`
    - `unload_image()`
    - `get_image(original=True) -> Optional[PIL.Image]`
    - `get_visible_image() -> Optional[PIL.Image]`
    - `destroy()`
  - Callbacks:
    - `on_render_done`: Called after each render completes
    - `on_zoom_change`: Called with (scale, percent) when zoom level changes
    - `on_pan_change`: Called with (pan_x, pan_y) when pan position changes
    - `on_error`: Called with (error_type, message) for errors

- **Class:** `SplitImage(master=None)`
  - Methods:
    - `load_image(side: str, path: str)`  where `side` is `"left"` or `"right"`
    - `fit_both()`
    - `unload_both()`

## Notes

- Requires Pillow (`PIL`). For GIFs, frames are resized to fit the canvas each tick.
- GIF playback disables pan/zoom events while playing.
- Returns `None` if no image is loaded or visible region is empty.
- Optional callbacks allow integration with external UI logic.
- Demo code is included in the widget module for interactive testing.
