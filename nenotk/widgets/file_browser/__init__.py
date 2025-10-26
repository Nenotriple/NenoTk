"""
# Purpose
Provides a Treeview-based file browser widget for navigating local directories with a responsive UI.

## API
- Class: `FileBrowser(master, path=None, on_open=None, show_cols=None, name_map=None, **kwargs) -> ttk.Frame`
    - `path`: starting directory; defaults to the user's home directory.
    - `on_open`: optional callback invoked with a `pathlib.Path` when a file is activated.
    - `show_cols`: list of column names to display (case-insensitive). Options: "type", "size", "modified". Defaults to all columns.
    - `name_map`: optional dictionary mapping `pathlib.Path` or string paths to display names. Keys can be absolute or relative paths.
    - `.change_directory(path)`: point the browser to a new root directory.
    - `.refresh()`: reload contents of the current root directory.
    - `.selected_paths`: list of `pathlib.Path` objects representing the current selection.
    - `.update_name_map(name_map)`: update the filename mapping and refresh the tree.
    - `.get_expansion_state()`: return a set of expanded node paths for later restoration.
    - `.set_expansion_state(state)`: restore previously saved expansion state.

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
import re
import time
import shutil
import pathlib
import subprocess

# tkinter
import tkinter as tk
from tkinter import ttk, messagebox

# typing
from typing import Callable, Iterable, List, Optional

from PIL import Image, ImageTk  # Add PIL import for image support


#endregion
#region FileBrowser


class FileBrowser(ttk.Frame):
    """Treeview-backed browser for navigating the filesystem."""
    def __init__(self,
                 master: tk.Widget,
                 path: Optional[os.PathLike[str] | str] = None,
                 on_open: Optional[Callable[[pathlib.Path], None]] = None,
                 on_change: Optional[Callable[[], None]] = None,
                 show_cols: Optional[List[str]] = None,
                 name_map: Optional[dict[os.PathLike[str] | str, str]] = None,
                 **kwargs) -> None:
        """Initialize the file browser widget."""
        super().__init__(master, **kwargs)
        self.on_open = on_open
        self.on_change = on_change
        self._node_paths: dict[str, pathlib.Path] = {}
        self._placeholder_tag = "__placeholder__"
        self._name_map: dict[pathlib.Path, str] = {}
        self._icon_images = self._load_icons()

        # Clipboard state
        self._clipboard_paths: List[pathlib.Path] = []
        self._clipboard_mode: Optional[str] = None  # 'cut' or 'copy'
        self._cut_items: set[str] = set()  # Track visually dimmed items

        self.set_name_map(name_map)
        self._build_ui(show_cols)
        self.change_directory(path or pathlib.Path.home())


    def _load_icons(self):
        """Load icon images from the script directory."""
        icon_dir = pathlib.Path(__file__).parent
        icons = {}
        def load_icon(filename):
            path = icon_dir / filename
            if path.exists():
                img = Image.open(path).resize((18, 18), Image.LANCZOS)
                return ImageTk.PhotoImage(img)
            return None
        icons['dir'] = load_icon('tree_dir_icon.png')
        icons['doc'] = load_icon('tree_doc_icon.png')
        return icons


    def _get_icon_for_path(self, path: pathlib.Path):
        """Return the appropriate icon for the given path."""
        if path.is_dir():
            return self._icon_images.get('dir')
        return self._icon_images.get('doc')


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
        # Save expansion state before clearing
        expansion_state = self.get_expansion_state()
        self._node_paths.clear()
        self.tree.delete(*self.tree.get_children())
        root_node = self._insert_node("", self._root_path, open=True)
        self._expand_node(root_node)
        # Restore expansion state
        self.set_expansion_state(expansion_state)
        self._trigger_change_callback()


    @property
    def selected_paths(self) -> List[pathlib.Path]:
        """Return the selected items as pathlib.Path objects."""
        paths: List[pathlib.Path] = []
        for item in self.tree.selection():
            path = self._node_paths.get(item)
            if path is not None:
                paths.append(path)
        return paths


    def update_name_map(self, name_map: Optional[dict[os.PathLike[str] | str, str]], refresh: bool = True) -> None:
        """Update the filename mapping and optionally refresh the tree."""
        self.set_name_map(name_map)
        if refresh:
            self.refresh()
        else:
            self._update_visible_labels()


    def set_name_map(self, name_map: Optional[dict[os.PathLike[str] | str, str]]) -> None:
        """Update the filename mapping without refreshing the tree."""
        self.set_name_map(name_map)
        self._update_visible_labels()


    def _update_visible_labels(self) -> None:
        """Update the text labels and icons of all existing tree items based on current name map."""
        for item_id, path in self._node_paths.items():
            new_label = self._node_label_with_map(path)
            icon = self._get_icon_for_path(path)
            self.tree.item(item_id, text=new_label, image=icon)


    def get_expansion_state(self) -> set[pathlib.Path]:
        """Return a set of paths for all currently expanded nodes."""
        expanded_paths = set()

        def collect_expanded(item_id: str) -> None:
            if self.tree.item(item_id, "open"):
                path = self._node_paths.get(item_id)
                if path is not None:
                    expanded_paths.add(path)
            # Recurse into children
            for child_id in self.tree.get_children(item_id):
                collect_expanded(child_id)

        # Start from root items
        for item_id in self.tree.get_children():
            collect_expanded(item_id)

        return expanded_paths


    def set_expansion_state(self, state: set[pathlib.Path]) -> None:
        """Restore expansion state from a previously saved set of paths."""
        if not state:
            return

        def expand_matching(item_id: str) -> None:
            path = self._node_paths.get(item_id)
            if path in state:
                # Open this node and ensure its children are loaded
                self.tree.item(item_id, open=True)
                self._expand_node(item_id)
                # Recurse into children to restore their state
                for child_id in self.tree.get_children(item_id):
                    expand_matching(child_id)

        # Start from root items
        for item_id in self.tree.get_children():
            expand_matching(item_id)


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

        # Configure tag for cut items
        self.tree.tag_configure("cut", foreground="gray")

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
        self._menu.add_command(label="Cut", command=self._menu_cut)
        self._menu.add_command(label="Copy", command=self._menu_copy)
        self._menu.add_command(label="Paste", command=self._menu_paste)
        self._menu.add_separator()
        self._menu.add_command(label="Copy Filepath", command=self._menu_copy_filepath)
        self._menu.add_command(label="Copy Filename", command=self._menu_copy_filename)
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
        self._menu.entryconfig("Cut", state=state)
        self._menu.entryconfig("Copy", state=state)
        self._menu.entryconfig("Copy Filepath", state=state)
        self._menu.entryconfig("Copy Filename", state=state)
        self._menu.entryconfig("Delete", state=state)
        # Paste is enabled if clipboard has items and a valid destination exists
        paste_state = "normal" if self._clipboard_paths else "disabled"
        self._menu.entryconfig("Paste", state=paste_state)


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
            self._trigger_change_callback()
        except Exception as e:
            messagebox.showerror("Delete Failed", f"Could not delete:\n{e}", parent=self)


    def _menu_copy_filepath(self) -> None:
        """Copy the full filepath of the selected item to the clipboard."""
        path = self._get_menu_selected_path()
        if path is None:
            return
        try:
            filepath_str = str(path.resolve())
            self.clipboard_clear()
            self.clipboard_append(filepath_str)
            self.update()  # Ensure clipboard is updated
        except Exception:
            pass


    def _menu_copy_filename(self) -> None:
        """Copy the filename (or mapped name if available) to the clipboard."""
        path = self._get_menu_selected_path()
        if path is None:
            return
        try:
            # Use mapped name if available, otherwise use the actual filename
            mapped = self._get_mapped_name(path)
            filename = mapped if mapped is not None else path.name
            self.clipboard_clear()
            self.clipboard_append(filename)
            self.update()  # Ensure clipboard is updated
        except Exception:
            pass


    def _menu_cut(self) -> None:
        """Cut selected items to clipboard."""
        paths = self.selected_paths
        if not paths:
            return
        # Clear previous cut visual state
        self._clear_cut_visual()
        self._clipboard_paths = paths
        self._clipboard_mode = 'cut'
        # Apply visual feedback to cut items
        for item_id, path in self._node_paths.items():
            if path in self._clipboard_paths:
                current_tags = list(self.tree.item(item_id, "tags"))
                if "cut" not in current_tags:
                    current_tags.append("cut")
                    self.tree.item(item_id, tags=current_tags)
                    self._cut_items.add(item_id)


    def _menu_copy(self) -> None:
        """Copy selected items to clipboard."""
        paths = self.selected_paths
        if not paths:
            return
        # Clear previous cut visual state
        self._clear_cut_visual()
        self._clipboard_paths = paths
        self._clipboard_mode = 'copy'


    def _menu_paste(self) -> None:
        """Paste clipboard items to the selected directory."""
        if not self._clipboard_paths or not self._clipboard_mode:
            return
        # Determine destination directory
        selected = self.selected_paths
        if selected:
            dest = selected[0]
            if not dest.is_dir():
                dest = dest.parent
        else:
            dest = self._root_path
        if not dest.exists() or not dest.is_dir():
            messagebox.showerror("Paste Failed", "Invalid destination directory.", parent=self)
            return
        errors = []
        success_count = 0
        # Track source -> destination mappings for name_map updates
        paste_mappings = {}
        for source_path in self._clipboard_paths:
            if not source_path.exists():
                errors.append(f"Source no longer exists: {source_path.name}")
                continue
            dest_path = dest / source_path.name
            # Handle name conflicts
            if dest_path.exists():
                base_name = source_path.stem
                suffix = source_path.suffix
                counter = 1
                while dest_path.exists():
                    new_name = f"{base_name} ({counter}){suffix}"
                    dest_path = dest / new_name
                    counter += 1
            try:
                if self._clipboard_mode == 'cut':
                    shutil.move(str(source_path), str(dest_path))
                else:  # copy
                    if source_path.is_dir():
                        shutil.copytree(str(source_path), str(dest_path))
                    else:
                        shutil.copy2(str(source_path), str(dest_path))
                success_count += 1
                paste_mappings[source_path] = dest_path
            except Exception as e:
                errors.append(f"{source_path.name}: {str(e)}")
        # Update name_map for pasted items
        for source_path, dest_path in paste_mappings.items():
            # If source had a mapped name, apply it to the destination
            mapped_name = self._get_mapped_name(source_path)
            if mapped_name is not None:
                try:
                    resolved_dest = dest_path.resolve()
                    self._name_map[resolved_dest] = mapped_name
                except (OSError, RuntimeError):
                    self._name_map[dest_path] = mapped_name
        # Clear clipboard after cut operation
        if self._clipboard_mode == 'cut':
            self._clear_cut_visual()
            self._clipboard_paths.clear()
            self._clipboard_mode = None
        # Refresh the view
        self.refresh()
        # Trigger change callback
        if success_count > 0:
            self._trigger_change_callback()
        # Show results
        if errors:
            error_msg = f"Pasted {success_count} item(s).\n\nErrors:\n" + "\n".join(errors[:5])
            if len(errors) > 5:
                error_msg += f"\n... and {len(errors) - 5} more errors"
            messagebox.showwarning("Paste Completed with Errors", error_msg, parent=self)
        elif success_count > 0:
            messagebox.showinfo("Paste Successful", f"Pasted {success_count} item(s).", parent=self)


    def _clear_cut_visual(self) -> None:
        """Remove cut visual feedback from all items."""
        for item_id in self._cut_items:
            try:
                current_tags = list(self.tree.item(item_id, "tags"))
                if "cut" in current_tags:
                    current_tags.remove("cut")
                    self.tree.item(item_id, tags=current_tags)
            except tk.TclError:
                # Item no longer exists
                pass
        self._cut_items.clear()


    def _trigger_change_callback(self) -> None:
        """Invoke the on_change callback if set."""
        if callable(self.on_change):
            self.on_change()


#endregion
#region Tree Management


    def _insert_node(self, parent: str, path: pathlib.Path, *, open: bool = False) -> str:
        """Insert an item for the given path and optionally seed lazy loading."""
        text = self._node_label_with_map(path)
        values = self._describe_path(path)
        icon = self._get_icon_for_path(path)
        item_id = self.tree.insert(parent, "end", text=text, values=values, open=open, image=icon)
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
        """Yield directory contents sorted with directories first and names in natural order or name_map."""
        try:
            entries = list(path.iterdir())
        except (PermissionError, OSError):
            return []
        def sort_key(p):
            # Use mapped name if available, else fallback to natural sort key
            mapped = self._get_mapped_name(p)
            if mapped is not None:
                # Use natural sort key on mapped name for consistency
                return (not p.is_dir(), FileBrowser._natural_sort_key(mapped.lower()))
            return (not p.is_dir(), FileBrowser._natural_sort_key(p.name))
        entries.sort(key=sort_key)
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


    def _get_mapped_name(self, path: pathlib.Path) -> Optional[str]:
        """Return the mapped name for a path if it exists in the name map."""
        # Try exact match first
        if path in self._name_map:
            return self._name_map[path]
        # Try resolved path
        try:
            resolved = path.resolve()
            if resolved in self._name_map:
                return self._name_map[resolved]
        except (OSError, RuntimeError):
            pass
        return None


    def _node_label_with_map(self, path: pathlib.Path) -> str:
        """Return the display label for a path, checking name map first."""
        mapped = self._get_mapped_name(path)
        if mapped is not None:
            return mapped
        return self._node_label(path)


    def set_name_map(self, name_map: Optional[dict[os.PathLike[str] | str, str]]) -> None:
        """Normalize and store the name mapping dictionary."""
        self._name_map.clear()
        if name_map:
            for key, value in name_map.items():
                try:
                    normalized_key = pathlib.Path(key).expanduser().resolve()
                    self._name_map[normalized_key] = value
                except (OSError, RuntimeError):
                    # If resolution fails, store as-is
                    self._name_map[pathlib.Path(key)] = value


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


    @staticmethod
    def _natural_sort_key(name: str):
        """Return a tuple key that sorts numeric parts numerically and text parts case-insensitively."""
        parts = re.findall(r'\d+|\D+', name.lower())
        key = []
        for part in parts:
            if part.isdigit():
                key.append(int(part))
            else:
                key.append(part)
        return tuple(key)


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

    # Demo with filename mapping
    current_dir = pathlib.Path(".").resolve()
    name_mapping = {
        current_dir / "__init__.py": "📄 Widget Init File",
        current_dir: "🏠 Current Directory",
    }

    browser2 = FileBrowser(root, path=".", show_cols=["size"], name_map=name_mapping)
    browser2.pack(fill="both", expand=True)

    root.mainloop()