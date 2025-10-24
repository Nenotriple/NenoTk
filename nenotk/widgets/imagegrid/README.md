# ImageGrid

Scrollable thumbnail browser for Tkinter with on-demand image loading.

## Features

- Accepts a directory path or iterable of image files; supports PNG, JPEG, WebP, TIFF, BMP variants.
- Built-in slider toggles five thumbnail sizes with immediate redraw.
- Incremental loading with `Load More` / `Load All` controls for large image sets.
- Grid recalculates column count on parent resize and keeps the active selection centered.
- Per-size Pillow cache avoids reprocessing thumbnails when sizes change.
- Selection highlight with optional `on_select(index, path)` callback.

## Quick Start

```python
import tkinter as tk
import nenotk as ntk

root = tk.Tk()
grid = ntk.ImageGrid(root)
grid.pack(fill="both", expand=True)

def on_select(index, path):
    print("Selected:", path)

grid.on_select = on_select
grid.initialize(image_files="path/to/images")

root.mainloop()
```

## API

- Class: `ImageGrid(master, image_files=None)`
  - `initialize(image_files=None)` - scan the provided folder or iterable and build the grid.
  - `reload_grid()` - rebuild thumbnails for the current `image_size`.
  - `load_images(all_images=False)` / `load_all_images()` - control incremental loading batches.
  - Attributes
    - `on_select`: optional callback receiving `(index, path)` when selection changes.
    - `image_size`: current size bucket `1-5`; set via slider or code before `reload_grid()`.
    - `images_per_load`: thumbnails fetched per batch (default 250).
    - `supported_types`: tuple of recognized file extensions.
- Thumbnails render as `ttk.Button` widgets; the active item uses the `Highlighted.TButton` style.

## Notes

- Requires Pillow for image processing.
- When `initialize` receives a folder path, files are gathered alphabetically.
- The grid uses `ScrollFrame` internally and recenters the selected item after resize or selection shifts.
