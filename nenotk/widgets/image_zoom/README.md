# ImageZoomWidget and SplitImage

Interactive image viewer widgets for Tkinter with zoom, pan, and GIF playback support.

## Features

- Mouse wheel zoom with cursor-centric focus; click-drag to pan.
- Fit-to-canvas, programmatic pan/zoom, and snapshot of the visible region.
- High-quality full render with fast previews for smooth interaction.
- GIF animation playback (temporarily disables pan/zoom events while playing).
- `SplitImage`: two synchronized panes for side-by-side comparison.

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

- Class: `ImageZoomWidget(master, on_render_done=None, **kwargs)`
  - `load_image(path, keep_view=False)` / `set_image(pil_image, keep_view=False)`
  - `force_fit_to_canvas()`
  - `set_pan_and_zoom(scale, pan_x, pan_y)` / `get_pan_and_zoom() -> (scale, pan_x, pan_y)`
  - `unload_image()`
  - `get_image(original=True) -> Optional[PIL.Image]`
  - `get_visible_image() -> Optional[PIL.Image]`
- Class: `SplitImage(master=None)`
  - `load_image(side: str, path: str)`  where `side` is e.g., `"left"` or `"right"`
  - `fit_both()` / `unload_both()`

## Notes

- Requires Pillow (`PIL`). For GIFs, frames are resized to fit the canvas each tick.
- The viewer emits an optional `on_render_done` callback after preview/full renders.
