# PopUpZoom

Hover-zoom for images displayed in a `tk.Label`. Shows a movable popup near the cursor with a zoomed view of the area under the mouse.

## Features

- Smooth popup zoom window that follows the mouse over the source widget.
- Mouse wheel to zoom in/out; Shift+MouseWheel to resize the popup.
- Constrains the popup to the screen bounds.
- Simple on/off via `zoom_enabled: BooleanVar`.

## Quick Start

```python
import tkinter as tk
from tkinter import Label
from PIL import Image, ImageTk
import nenotk as ntk

root = tk.Tk()
img = Image.open("example.png")
photo = ImageTk.PhotoImage(img)

lbl = Label(root, image=photo)
lbl.pack()

zoom = ntk.PopUpZoom(lbl)
zoom.set_image(img)
zoom.zoom_enabled.set(True)

root.mainloop()
```

## API

- Class: `PopUpZoom(widget: Label)`
  - `set_image(image: PIL.Image)`: set/replace the image used for zooming
  - `show_popup(event)` / `hide_popup(event)`: show/hide popup (normally event-driven)
  - `zoom_enabled: BooleanVar`: enable/disable behavior

## Notes

- Requires Pillow (`PIL`). The source widget should display the same image (e.g., via `ImageTk.PhotoImage`) to make coordinates intuitive.
