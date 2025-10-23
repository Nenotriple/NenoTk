# NenoTk

NenoTk provides a suite of drop-in replacement and enhancement widgets for Python's tkinter GUI framework.

Designed to be simple to implement, blend in with existing ttk styles, extend functionality, and improve user experience.

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## 📋 Table of Contents

- [Installation](#installation)
- [Available Modules](#available-modules)
- [Project Structure](#project-structure)

## Installation

Tested on Python 3.10

### Install from Source

```bash
# Clone repo
git clone https://github.com/Nenotriple/NenoTk.git
cd NenoTk

# Install dependencies
pip install -r requirements.txt

# Install NenoTk to your environment
pip install -e .
```

### Quick Start

```python
import tkinter as tk
import nenotk as ntk
from nenotk/widgets/tooltip import ToolTip as Tip

root = tk.Tk()

# ToolTip
button = tk.Button(root, text="Go!")
button.pack()
Tip.bind(button, "ToolTip text")

# ScrollFrame
scrollframe = ntk.ScrollFrame(root, layout="vertical")
scrollframe.pack()
for i in range(20):
    tk.Label(scrollframe.frame, text=f"Item {i+1}").pack()

# ButtonMenu
bmenu = ntk.ButtonMenu(root, text="Choose",).pack()
bmenu.menu.add_command(label="Option 1", ...)
bmenu.menu.add_separator()
bmenu.menu.add_checkbutton(label="Toggle", ...)

root.mainloop()
```

*See individual [widgets](nenotk/widgets)/[utils](nenotk/utils) docs and demos for more info and examples.*

## Available Modules

### Available Widgets

- [ButtonMenu](nenotk/widgets/buttonmenu/__init__.py)
  - A button that displays a dropdown menu when clicked.
  - *(Inherits from `ttk.Button`)*
- [CustomSimpleDialog](nenotk/widgets/custom_simpledialog/__init__.py)
  - A collection of customizable dialog boxes.
  - *(Inherits from `tk.Toplevel`)*
- [FindReplaceEntry](nenotk/widgets/find_replace_entry/__init__.py)
  - An Entry widget cluster with built-in find and replace functionality.
  - *(Inherits from `ttk.Frame`)*
- [ImageZoomWidget](nenotk/widgets/image_zoom/__init__.py)
  - A widget for displaying and zooming images.
  - *(Inherits from `ttk.Frame`)*
- [PopUpZoom](nenotk/widgets/popup_zoom/__init__.py)
  - A popup window that allows zooming into content.
  - *(Inherits from `tk.Toplevel`)*
- [ScrollFrame](nenotk/widgets/scrollframe/__init__.py)
  - A frame that adds scrollbars automatically when content overflows.
  - *(Inherits from `ttk.Frame` or `ttk.LabelFrame`)*
- [SpellCheckText](nenotk/widgets/spelltext/__init__.py)
  - A Text widget with integrated spell-checking capabilities.
  - *(Inherits from `tk.Text`)*
- [ToolTip](nenotk/widgets/tooltip/__init__.py)
  - A widget that displays helpful tooltips when hovering over other widgets.
  - *(Composes using `tk.Toplevel`)*

### Available Utilities

- [entry_helper](nenotk/utils/entry_helper.py)
  - Enhance Entry widget functionality.
- [window_helper](nenotk/utils/window_helper.py)
  - For managing window behavior and properties.

## Project Structure

```filetree
.
└── NenoTk/                           # Project root
    ├── nenotk/                       # Root package
    │   ├── __init__.py               # Root package exports
    │   │
    │   ├── widgets/                  # Widget package
    │   │   ├── __init__.py           # Widget package exports
    │   │   │
    │   │   ├── buttonmenu/           # ButtonMenu
    │   │   ├── custom_simpledialog/  # Dialog collection
    │   │   ├── findreplace/          # FindReplaceEntry
    │   │   ├── imagezoomwidget/      # ImageZoomWidget
    │   │   ├── popupzoom/            # PopUpZoom
    │   │   ├── scrollframe/          # ScrollFrame
    │   │   ├── spelltext/            # SpellCheckText
    │   │   └── tooltip/              # ToolTip
    │   │
    │   └── utils/                    # Utility package
    │       ├── __init__.py           # Utility package exports
    │       │
    │       ├── entry_helper.py       # Entry helper collection
    │       └── window_helper.py      # Window helper collection
    │
    ├── requirements.txt              # Project dependencies
    ├── setup.py                      # Package installation
    └── README.md                     # This file
```
