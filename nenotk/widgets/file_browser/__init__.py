"""
# Purpose
Provides a Treeview-based file browser widget for navigating local directories with a responsive UI.

## API
- Class: `FileBrowser(master, path=None, on_open=None, show_cols=None, **kwargs) -> ttk.Frame`
    - `path`: starting directory; defaults to the user's home directory.
    - `on_open`: optional callback invoked with a `pathlib.Path` when a file is activated.
    - `show_cols`: list of column names to display (case-insensitive). Options: "type", "size", "modified". Defaults to all columns.
    - `.change_directory(path)`: point the browser to a new root directory.
    - `.refresh()`: reload contents of the current root directory.
    - `.selected_paths`: list of `pathlib.Path` objects representing the current selection.

## Notes
- Directories load lazily when expanded, keeping large trees snappy.
- Double-clicking (or pressing Enter on) a file triggers the `on_open` callback.
- The widget configures internal geometry management for plug-and-play use inside layouts.
- The "Name" column is always displayed and cannot be disabled.

## Example
- See the demo code at the bottom of this file.
"""


#region Imports


from __future__ import annotations

# Standard
import os
import shutil
import subprocess
import sys
import time
import pathlib

# tkinter
import tkinter as tk
from tkinter import ttk, messagebox

# typing
from typing import Callable, Iterable, List, Optional


#endregion
#region FileBrowser


class FileBrowser(ttk.Frame):
    """Treeview-backed browser for navigating the filesystem."""
    def __init__(self,
                 master: tk.Widget,
                 path: Optional[os.PathLike[str] | str] = None,
                 on_open: Optional[Callable[[pathlib.Path], None]] = None,
                 show_cols: Optional[List[str]] = None,
                 **kwargs) -> None:
        """Initialize the file browser widget."""
        super().__init__(master, **kwargs)
        self.on_open = on_open
        self._node_paths: dict[str, pathlib.Path] = {}
        self._placeholder_tag = "__placeholder__"
        self._build_ui(show_cols)
        self.change_directory(path or pathlib.Path.home())


#endregion
#region Public API


    def change_directory(self, path: os.PathLike[str] | str) -> None:
        """Set a new root directory and rebuild the tree."""
        root_path = pathlib.Path(path).expanduser().resolve()
        if not root_path.exists():
            raise FileNotFoundError(f"Directory does not exist: {root_path}")
        if not root_path.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {root_path}")
        self._root_path = root_path
        self.refresh()


    def refresh(self) -> None:
        """Reload the tree for the current root directory."""
        self._node_paths.clear()
        self.tree.delete(*self.tree.get_children())
        root_node = self._insert_node("", self._root_path, open=True)
        self._expand_node(root_node)


    @property
    def selected_paths(self) -> List[pathlib.Path]:
        """Return the selected items as pathlib.Path objects."""
        paths: List[pathlib.Path] = []
        for item in self.tree.selection():
            path = self._node_paths.get(item)
            if path is not None:
                paths.append(path)
        return paths


#endregion
#region UI Setup


    def _build_ui(self, show_cols) -> None:
        """Create child widgets and configure layout."""
        self.set_visible_columns(show_cols)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        all_columns = ("type", "size", "modified")
        self.tree = ttk.Treeview(self, columns=all_columns, displaycolumns=self._visible_cols, show="tree headings", selectmode="extended")
        self.tree.heading("#0", text="Name", anchor="w")
        self.tree.heading("type", text="Type", anchor="w")
        self.tree.heading("size", text="Size", anchor="w")
        self.tree.heading("modified", text="Modified", anchor="w")

        self.tree.column("#0", width=240, minwidth=160, stretch=True)
        self.tree.column("type", width=120, minwidth=80, stretch=False)
        self.tree.column("size", width=100, minwidth=80, stretch=False)
        self.tree.column("modified", width=160, minwidth=140, stretch=False)

        self.tree.grid(row=0, column=0, sticky="nsew")

        vscroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        hscroll = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vscroll.set, xscrollcommand=hscroll.set)

        vscroll.grid(row=0, column=1, sticky="ns")
        hscroll.grid(row=1, column=0, sticky="ew")

        self.tree.bind("<<TreeviewOpen>>", self._on_node_open, add="+")
        self.tree.bind("<Double-1>", self._on_item_activated, add="+")
        self.tree.bind("<Return>", self._on_item_activated, add="+")
        self.tree.bind("<Button-3>", self._on_right_click, add="+")

        # Context menu
        self._menu = tk.Menu(self, tearoff=0)
        self._menu.add_command(label="Open", command=self._menu_open)
        self._menu.add_command(label="Reveal in File Explorer", command=self._menu_reveal)
        self._menu.add_separator()
        self._menu.add_command(label="Refresh", command=self.refresh)
        self._menu.add_separator()
        self._menu.add_command(label="Delete", command=self._menu_delete)

        self._menu_item_id = None  # Track which item menu is for


    def set_visible_columns(self, show_cols):
        all_cols = ["type", "size", "modified"]
        if show_cols is None:
            self._visible_cols = all_cols.copy()
        else:
            normalized = [col.lower() for col in show_cols]
            self._visible_cols = [col for col in all_cols if col in normalized]


#endregion
#region Event Handlers


    def _on_node_open(self, event: tk.Event) -> None:
        """Lazy-load children when a directory node is expanded."""
        item_id = self.tree.focus()
        if not item_id:
            return
        self._expand_node(item_id)


    def _on_item_activated(self, _event: tk.Event) -> None:
        """Handle file activation via double-click or Return key press."""
        selection = self.tree.selection()
        if not selection:
            return
        item_id = selection[0]
        path = self._node_paths.get(item_id)
        if path is None:
            return
        if path.is_dir():
            # Toggle directories manually to keep focus in sync.
            is_open = self.tree.item(item_id, "open")
            self.tree.item(item_id, open=not is_open)
            if not is_open:
                self._expand_node(item_id)
            return
        callback = self.on_open
        if callable(callback):
            try:
                callback(path)
            except Exception:
                # Suppress callback exceptions to protect the UI loop.
                pass


    def _set_menu_item_states(self, enabled: bool) -> None:
        """Enable or disable item-specific context menu commands."""
        state = "normal" if enabled else "disabled"
        self._menu.entryconfig("Open", state=state)
        self._menu.entryconfig("Reveal in File Explorer", state=state)
        self._menu.entryconfig("Delete", state=state)


    def _open_with_os(self, path: pathlib.Path) -> None:
        """Open or reveal the given path using the OS file explorer."""
        try:
            os.startfile(str(path))
        except Exception:
            pass


    def _on_right_click(self, event: tk.Event) -> None:
        """Show context menu for item under pointer."""
        iid = self.tree.identify_row(event.y)
        if iid:
            self.tree.selection_set(iid)
            self._menu_item_id = iid
            self._set_menu_item_states(True)
        else:
            self._menu_item_id = None
            self._set_menu_item_states(False)
        self._menu.tk_popup(event.x_root, event.y_root)


#endregion
#region Menu Handlers


    def _get_menu_selected_path(self) -> Optional[pathlib.Path]:
        """Return the path for the currently menu-selected item, or None."""
        item_id = self._menu_item_id
        return self._node_paths.get(item_id)


    def _menu_open(self) -> None:
        """Open the selected file/directory in the system default program."""
        path = self._get_menu_selected_path()
        if path is None:
            return
        self._open_with_os(path)


    def _menu_reveal(self) -> None:
        """Reveal the selected file/directory in the OS file explorer."""
        path = self._get_menu_selected_path()
        if path is None:
            return
        try:
            subprocess.run(['explorer', '/select,', str(path.resolve())])
        except Exception:
            pass


    def _menu_delete(self) -> None:
        """Delete the selected file/directory with confirmation."""
        path = self._get_menu_selected_path()
        if path is None:
            return
        confirm = messagebox.askyesno("Delete", f"Delete '{path.name}'?\nThis cannot be undone.", parent=self)
        if not confirm:
            return
        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            self.refresh()
        except Exception as e:
            messagebox.showerror("Delete Failed", f"Could not delete:\n{e}", parent=self)


#endregion
#region Tree Management


    def _insert_node(self, parent: str, path: pathlib.Path, *, open: bool = False) -> str:
        """Insert an item for the given path and optionally seed lazy loading."""
        text = self._node_label(path)
        values = self._describe_path(path)
        item_id = self.tree.insert(parent, "end", text=text, values=values, open=open)
        self._node_paths[item_id] = path

        if path.is_dir():
            # Insert a placeholder child so the Treeview displays an expand icon.
            self.tree.insert(item_id, "end", text="", values=("", "", ""), tags=(self._placeholder_tag,))
        return item_id


    def _expand_node(self, item_id: str) -> None:
        """Populate directory children when a node is opened."""
        children = self.tree.get_children(item_id)
        if len(children) == 1 and self._placeholder_tag in self.tree.item(children[0], "tags"):
            self.tree.delete(children[0])
            path = self._node_paths.get(item_id)
            if path is None:
                return
            for child_path in self._iter_directory(path):
                self._insert_node(item_id, child_path)


    def _iter_directory(self, path: pathlib.Path) -> Iterable[pathlib.Path]:
        """Yield directory contents sorted with directories first."""
        try:
            entries = list(path.iterdir())
        except (PermissionError, OSError):
            return []
        entries.sort(key=lambda p: (not p.is_dir(), p.name.lower()))
        return entries


#endregion
#region Helpers


    @staticmethod
    def _node_label(path: pathlib.Path) -> str:
        """Return the display label for a path."""
        if path == path.home():
            return path.name or str(path)
        name = path.name
        if not name:
            drive = getattr(path, "drive", "") or str(path)
            return drive.rstrip("\\/")
        return name


    @staticmethod
    def _describe_path(path: pathlib.Path) -> tuple[str, str, str]:
        """Return (type, size, modified) tuple for Treeview columns."""
        if path.is_dir():
            type_text = "Directory"
            size_text = ""
        else:
            type_text = path.suffix.lower() or "File"
            size_text = FileBrowser._format_size(path)
        modified_text = FileBrowser._format_mtime(path)
        return type_text, size_text, modified_text


    @staticmethod
    def _format_size(path: pathlib.Path) -> str:
        """Return a human-readable representation of file size."""
        try:
            size = path.stat().st_size
        except (OSError, PermissionError):
            return ""
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024:
                return f"{size:.0f} {unit}"
            size /= 1024
        return f"{size:.0f} PB"


    @staticmethod
    def _format_mtime(path: pathlib.Path) -> str:
        """Return a formatted modification timestamp."""
        try:
            mtime = path.stat().st_mtime
        except (OSError, PermissionError):
            return ""
        return time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime))


#endregion
#region Demo


if __name__ == "__main__":
    import tkinter as tk
    from tkinter import messagebox
    from nenotk.widgets.file_browser import FileBrowser

    root = tk.Tk()
    root.title("FileBrowser Demo")
    root.geometry("800x600")

    # Demo with all columns (default)
    browser = FileBrowser(root, path=".")
    browser.pack(fill="both", expand=True)

    def handle_open(path):
        print("Opened:", path)

    browser.on_open = handle_open

    # Demo with only Name and Size columns
    browser2 = FileBrowser(root, path=".", show_cols=["size"])
    browser2.pack(fill="both", expand=True)

    root.mainloop()