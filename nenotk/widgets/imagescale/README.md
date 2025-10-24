# ImageScale

Tkinter `Label` widget for dynamic image scaling with optional aspect preservation and high-quality redraws.

## Features

- Load from a file path or `PIL.Image.Image` in memory.
- Supports `fill` and `center` modes to control how images fit the widget.
- Toggle aspect ratio preservation and choose from PIL resampling methods (`nearest`, `bilinear`, `bicubic`, `lanczos`).
- Fast preview updates while resizing, followed by delayed high-quality rendering.
- Exposes helpers to fetch the displayed PIL image or refresh manually.

## Quick Start

```python
import tkinter as tk
import nenotk as ntk

root = tk.Tk()
scale = ntk.ImageScale(root, image_path="photo.jpg", scale_mode="center")
scale.pack(fill="both", expand=True)
root.mainloop()
```

## API

- Class: `ImageScale(master=None, image_path="", width=None, height=None, keep_aspect=True, draw_method="lanczos", scale_mode="fill", hq_delay_ms=200, **kwargs)`
  - `set_image(image_path_or_pil)`
  - `set_image_from_pil(pil_image)`
  - `refresh_displayed_image()`
  - `set_keep_aspect(enabled)` / `is_keep_aspect()`
  - `set_scale_mode(mode)`
  - `set_draw_method(method)`
  - `clear()`
  - `get_image_path()`
  - `get_displayed_pil_image()`

## Notes

- Relies on Pillow (`PIL`) for image loading and resampling.
- Uses `<Configure>` events for resize handling; ensure the widget is gridded/packed with stretch for best results.
- The delayed high-quality redraw is controlled via `hq_delay_ms` (default 200 ms).
