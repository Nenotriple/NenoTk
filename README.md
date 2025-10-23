# NenoTk

NenoTk provides a suite of drop-in replacement and enhancement widgets for Python's tkinter GUI framework.

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## 📋 Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Available Widgets](#available-widgets)
- [Project Structure](#project-structure)

## Overview

- **Ease of use:** Simple, intuitive APIs that extend familiar tkinter patterns
- **Interactive demos:** Every widget includes working example code

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
from nenotk.widgets.tooltip import ToolTip as Tip

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
menu_items = ["1", "2", "3"]
ntk.ButtonMenu(root, text="Choose", menu_items=menu_items).pack()

root.mainloop()
```

## Available Widgets

- **ButtonMenu:**
  - A button that displays a dropdown menu when clicked.
  - *(Inherits from `ttk.Button`)*
- **CustomSimpleDialog:**
  - A collection of customizable dialog boxes.
  - *(Inherits from `tk.Toplevel`)*
- **FindReplaceEntry:**
  - An Entry widget cluster with built-in find and replace functionality.
  - *(Inherits from `ttk.Frame`)*
- **ImageZoomWidget:**
  - A widget for displaying and zooming images.
  - *(Inherits from `ttk.Frame`)*
- **PopUpZoom:**
  - A popup window that allows zooming into content.
  - *(Inherits from `tk.Toplevel`)*
- **ScrollFrame:**
  - A frame that adds scrollbars automatically when content overflows.
  - *(Inherits from `ttk.Frame` or `ttk.LabelFrame`)*
- **SpellCheckText:**
  - A Text widget with integrated spell-checking capabilities.
  - *(Inherits from `tk.Text`)*
- **ToolTip:**
  - A widget that displays helpful tooltips when hovering over other widgets.
  - *(Composes using `tk.Toplevel`)*

## Available Utilities

- **entry_helper:** Enhance Entry widget functionality.
- **window_helper:** For managing window behavior and properties.

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
