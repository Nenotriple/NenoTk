# ScrollFrame

A drop-in scrollable container for Tkinter that behaves like a `ttk.Frame` but exposes an inner content frame you place your widgets into.

## Features

- Vertical, horizontal, or both scrollbars via `layout="vertical"|"horizontal"|"both"`.
- Inner container exposed as `.frame` for your UI content.
- Auto mousewheel binding only when scrolling is possible on that axis.
- Optional `label="..."` wraps content in a `ttk.LabelFrame` instead of a plain `ttk.Frame`.
- Emits `<<ScrollStateChanged>>` when scrollability changes.

## Quick Start

```python
import tkinter as tk
from tkinter import ttk
import nenotk as ntk

root = tk.Tk()
sf = ntk.ScrollFrame(root, layout="vertical")
sf.pack(fill="both", expand=True)

# Add content to the inner frame
for i in range(30):
    ttk.Button(sf.frame, text=f"Item {i+1}").pack(fill="x", padx=8, pady=2)

root.mainloop()
```

## API

- Class: `ScrollFrame(master, layout="vertical", label=None, **kwargs)`
  - `layout`: `"vertical"`, `"horizontal"`, or `"both"`
  - `label`: optional string; wraps content in a `ttk.LabelFrame`
  - Inherits `ttk.Frame` options via `**kwargs`
- Attributes
  - `.frame`: the inner `ttk.Frame` to pack/grid/place your widgets
- Events
  - `<<ScrollStateChanged>>` fired when scrollability toggles on/off per axis

## Notes

- For `layout="vertical"`, the inner window width follows the canvas width. For `layout="horizontal"`, the height follows the canvas height. For `"both"`, the content can freely grow in both directions.
- Mouse wheel events are bound/unbound dynamically based on the content size and the selected layout.
