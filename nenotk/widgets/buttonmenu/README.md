# ButtonMenu

A `ttk.Button` subclass with an attached `tk.Menu` that opens on click. Easily add commands, checkbuttons, and separators to the built-in menu.

## Features

- Menu appears relative to the button on `"up"`, `"down"` *(default)*, `"left"`, or `"right"`.
- Access the menu via `.menu` to add items programmatically.
- Simple `.hide_menu()` helper to close an open menu.

## Quick Start

```python
import tkinter as tk
import nenotk as ntk

root = tk.Tk()
btn = ntk.ButtonMenu(root, text="Options", side="right")
btn.pack()

btn.menu.add_command(label="Open", command=lambda: print("Open"))
btn.menu.add_separator()
btn.menu.add_checkbutton(label="Toggle", command=lambda: print("Toggled"))

root.mainloop()
```

## API

- Class: `ButtonMenu(parent, side="down", **kwargs)`
  - `side`: one of `"up"`, `"down"`, `"left"`, `"right"`
  - Inherits all `ttk.Button` options via `**kwargs`
- Attributes
  - `.menu`: the attached `tk.Menu`
- Methods
  - `.hide_menu()`: remove the menu if shown
