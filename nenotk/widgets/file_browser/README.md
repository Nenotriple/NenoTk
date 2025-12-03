# FileBrowser

A Treeview-based file browser widget for navigating local directories with a responsive, feature-rich UI.

## Features

- Lazy-loading directory expansion for snappy performance with large trees.
- Customizable columns: show `"type"`, `"size"`, and/or `"modified"` alongside names.
- Display name mapping via `name_map` to show friendly labels instead of filenames.
- Full file operations: Cut, Copy, Paste, Rename, Delete, New Folder, New File.
- Right-click context menu with common file operations.
- Inline rename with Windows filename validation.
- Save and restore expansion state across refreshes.
- Double-click or Enter to open files with the OS default handler.
- Optional `on_open` and `on_change` callbacks for integration.

## Quick Start

```python
import tkinter as tk
import nenotk as ntk

root = tk.Tk()
browser = ntk.FileBrowser(root, path=".")
browser.pack(fill="both", expand=True)

def handle_open(path):
    print(f"Opened: {path}")

browser.on_open = handle_open

root.mainloop()
```

## API

- **Class:** `FileBrowser(master, path=None, on_open=None, on_change=None, show_cols=None, name_map=None, **kwargs)`
  - `path`: starting directory; defaults to the user's home directory.
  - `on_open`: callback invoked with a `pathlib.Path` when a file is activated.
  - `on_change`: callback invoked when files are created, deleted, renamed, or pasted.
  - `show_cols`: list of column names to display (case-insensitive). Options: `"type"`, `"size"`, `"modified"`. Defaults to all columns.
  - `name_map`: dictionary mapping `pathlib.Path` or string paths to display names.
  - Inherits `ttk.Frame` options via `**kwargs`.
- **Attributes**
  - `.selected_paths`: list of `pathlib.Path` objects for the current selection.
  - `.on_open`: callback for file activation (can be set after creation).
  - `.on_change`: callback for file operations (can be set after creation).
- **Methods**
  - `.change_directory(path)`: set a new root directory and rebuild the tree.
  - `.refresh()`: reload the current root directory contents.
  - `.update_name_map(name_map, refresh=True)`: update filename mappings.
  - `.get_expansion_state()`: return a set of expanded node paths.
  - `.set_expansion_state(state)`: restore previously saved expansion state.

## Context Menu

Right-click on any file or folder to access:

| Action                   | Description                                      |
| ------------------------ | ------------------------------------------------ |
| Open                     | Open file/folder with the OS default handler     |
| Reveal in File Explorer  | Show the item in Windows Explorer                |
| New Folder               | Create a new folder in the selected directory    |
| New File                 | Create a new text file in the selected directory |
| Cut                      | Cut selected items to clipboard                  |
| Copy                     | Copy selected items to clipboard                 |
| Paste                    | Paste clipboard items to the target directory    |
| Copy Filepath            | Copy the full path to clipboard                  |
| Copy Filename            | Copy the filename (or mapped name) to clipboard  |
| Rename                   | Inline rename with validation                    |
| Refresh                  | Reload the directory tree                        |
| Delete                   | Delete with confirmation prompt                  |

## Name Mapping Example

Display friendly names instead of actual filenames:

```python
import pathlib
import tkinter as tk
import nenotk as ntk

root = tk.Tk()

current_dir = pathlib.Path(".").resolve()
name_mapping = {
    current_dir: "🏠 Project Root",
    current_dir / "setup.py": "📦 Module Setup",
    current_dir / "README.md": "📖 Documentation",
}

browser = ntk.FileBrowser(root, path=".", name_map=name_mapping)
browser.pack(fill="both", expand=True)

root.mainloop()
```

## Notes

- The "Name" column is always displayed and cannot be disabled.
- Name validation enforces Windows filesystem rules (invalid characters, reserved names like CON, PRN, etc.).
- Cut items appear dimmed in the tree until pasted or the operation is cancelled.
- Directories load lazily when expanded, keeping large trees responsive.
- Requires Pillow (`PIL`) for folder/file icons.
