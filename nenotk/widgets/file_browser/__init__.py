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
- Double-clicking (or pressing Enter) on a file triggers the `on_open` callback.
- The widget configures internal geometry management for plug-and-play use inside layouts.
- The "Name" column is always displayed and cannot be disabled.
- Right-click context menu includes: Open, Reveal in File Explorer, New Folder, New File, Cut, Copy, Paste, Copy Filepath, Copy Filename, Rename, Refresh, Delete.
- Name validation enforces Windows filesystem rules (invalid characters, reserved names, etc.).

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

from PIL import Image, ImageTk


#endregion
#region FileBrowser


class FileBrowser(ttk.Frame):
    """Treeview-backed browser for navigating the filesystem."""

    # Filename validation constants (Windows-specific)
    INVALID_FILENAME_CHARS = '<>:"/\\|?*'
    RESERVED_FILENAMES = frozenset({
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    })

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

        self._set_name_map(name_map)
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
        self._set_name_map(name_map)
        if refresh:
            self.refresh()
        else:
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
        self._menu.add_command(label="New Folder", command=self._menu_new_folder)
        self._menu.add_command(label="New File", command=self._menu_new_file)
        self._menu.add_separator()
        self._menu.add_command(label="Cut", command=self._menu_cut)
        self._menu.add_command(label="Copy", command=self._menu_copy)
        self._menu.add_command(label="Paste", command=self._menu_paste)
        self._menu.add_separator()
        self._menu.add_command(label="Copy Filepath", command=self._menu_copy_filepath)
        self._menu.add_command(label="Copy Filename", command=self._menu_copy_filename)
        self._menu.add_separator()
        self._menu.add_command(label="Rename", command=self._menu_rename)
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
        # Open file/folder with the OS default handler
        self._open_with_os(path)


    def _set_menu_item_states(self, enabled: bool) -> None:
        """Enable or disable item-specific context menu commands."""
        state = "normal" if enabled else "disabled"
        self._menu.entryconfig("Open", state=state)
        self._menu.entryconfig("Reveal in File Explorer", state=state)
        self._menu.entryconfig("Cut", state=state)
        self._menu.entryconfig("Copy", state=state)
        self._menu.entryconfig("Copy Filepath", state=state)
        self._menu.entryconfig("Copy Filename", state=state)
        self._menu.entryconfig("Rename", state=state)
        self._menu.entryconfig("Delete", state=state)
        # Paste is enabled if clipboard has items and a valid destination exists
        paste_state = "normal" if self._clipboard_paths else "disabled"
        self._menu.entryconfig("Paste", state=paste_state)
        # New Folder/File are always enabled (create in root or selected directory)
        self._menu.entryconfig("New Folder", state="normal")
        self._menu.entryconfig("New File", state="normal")


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


    def _validate_name(self, name: str, parent_dir: pathlib.Path, operation: str = "Operation") -> Optional[str]:
        """Validate a filename/folder name. Returns error message or None if valid."""
        name = name.strip()
        # Check if name is empty
        if not name:
            return "Name cannot be empty."
        # Check for invalid characters (Windows-specific)
        if any(char in name for char in self.INVALID_FILENAME_CHARS):
            return f"Name contains invalid characters: {self.INVALID_FILENAME_CHARS}"
        # Check for reserved names (Windows)
        name_without_ext = pathlib.Path(name).stem.upper()
        if name_without_ext in self.RESERVED_FILENAMES:
            return f"'{name}' is a reserved system name."
        # Check if name ends with space or period (Windows restriction)
        if name.endswith(' ') or name.endswith('.'):
            return "Name cannot end with a space or period."
        # Check for duplicate names
        new_path = parent_dir / name
        if new_path.exists():
            return f"An item named '{name}' already exists."
        return None


    def _get_target_directory(self) -> pathlib.Path:
        """Get the target directory for new item creation based on selection."""
        selected = self.selected_paths
        if selected:
            target = selected[0]
            if target.is_dir():
                return target
            return target.parent
        return self._root_path


    def _generate_unique_name(self, directory: pathlib.Path, base_name: str, extension: str = "") -> str:
        """Generate a unique filename in the given directory."""
        new_name = f"{base_name}{extension}"
        counter = 1
        while (directory / new_name).exists():
            new_name = f"{base_name} ({counter}){extension}"
            counter += 1
        return new_name


    def _create_new_item(self, is_folder: bool) -> None:
        """Create a new file or folder and start inline rename."""
        target_dir = self._get_target_directory()
        if is_folder:
            base_name, extension = "New Folder", ""
            item_type = "Folder"
        else:
            base_name, extension = "New File", ".txt"
            item_type = "File"
        new_name = self._generate_unique_name(target_dir, base_name, extension)
        new_path = target_dir / new_name
        try:
            if is_folder:
                new_path.mkdir(parents=False, exist_ok=False)
            else:
                new_path.touch(exist_ok=False)
        except Exception as e:
            messagebox.showerror(f"Create {item_type} Failed", f"Could not create {item_type.lower()}:\n{e}", parent=self)
            return
        self._refresh_and_rename_new_item(new_path, target_dir)


    def _menu_new_folder(self) -> None:
        """Create a new folder and start inline rename."""
        self._create_new_item(is_folder=True)


    def _menu_new_file(self) -> None:
        """Create a new text file and start inline rename."""
        self._create_new_item(is_folder=False)


    def _refresh_and_rename_new_item(self, new_path: pathlib.Path, parent_dir: pathlib.Path) -> None:
        """Refresh the tree and start inline rename for a newly created item."""
        # Save expansion state, ensure parent is expanded
        expansion_state = self.get_expansion_state()
        expansion_state.add(parent_dir)
        # Refresh
        self.refresh()
        self.set_expansion_state(expansion_state)
        # Find the new item
        new_item_id = None
        for item_id, path in self._node_paths.items():
            if path == new_path:
                new_item_id = item_id
                break
        if new_item_id:
            # Select and scroll to the new item
            self.tree.selection_set(new_item_id)
            self.tree.see(new_item_id)
            self.tree.focus(new_item_id)
            # Schedule inline rename after UI updates
            self.after(50, lambda: self._start_rename(new_item_id))
        self._trigger_change_callback()


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


    def _set_clipboard(self, mode: str) -> None:
        """Set clipboard paths and mode, applying visual feedback for cut operations."""
        paths = self.selected_paths
        if not paths:
            return
        self._clear_cut_visual()
        self._clipboard_paths = paths
        self._clipboard_mode = mode
        if mode == 'cut':
            # Apply visual feedback to cut items
            clipboard_set = set(self._clipboard_paths)
            for item_id, path in self._node_paths.items():
                if path in clipboard_set:
                    current_tags = list(self.tree.item(item_id, "tags"))
                    if "cut" not in current_tags:
                        current_tags.append("cut")
                        self.tree.item(item_id, tags=current_tags)
                        self._cut_items.add(item_id)


    def _menu_cut(self) -> None:
        """Cut selected items to clipboard."""
        self._set_clipboard('cut')


    def _menu_copy(self) -> None:
        """Copy selected items to clipboard."""
        self._set_clipboard('copy')


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
            self._update_name_map_entry(source_path, dest_path)
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


    def _menu_rename(self) -> None:
        """Start inline rename for the selected item."""
        item_id = self._menu_item_id
        if item_id:
            self._start_rename(item_id)


    def _start_rename(self, item_id: str) -> None:
        """Start inline rename with a ttk.Entry overlay over the tree item."""
        path = self._node_paths.get(item_id)
        if path is None:
            return
        # Get the bounding box of the tree item text
        self.tree.update_idletasks()
        bbox = self.tree.bbox(item_id, column="#0")
        if not bbox:
            # Item not visible, scroll to it and retry
            self.tree.see(item_id)
            self.tree.update_idletasks()
            bbox = self.tree.bbox(item_id, column="#0")
            if not bbox:
                return
        x, y, width, height = bbox
        # Create the entry widget
        rename_entry = ttk.Entry(self.tree)
        current_name = path.name
        rename_entry.insert(0, current_name)
        # Position the entry over the item
        # Add some padding to x to account for icon
        icon_offset = 24  # Approximate icon width + padding
        rename_entry.place(x=x + icon_offset, y=y, width=max(width - icon_offset, 150), height=height)
        rename_entry.focus_set()
        # Select the filename stem (not extension) for files
        if path.is_file() and path.suffix:
            stem_end = len(path.stem)
            rename_entry.selection_range(0, stem_end)
            rename_entry.icursor(stem_end)
        else:
            rename_entry.selection_range(0, tk.END)
        # Track whether rename was completed to avoid double processing
        rename_completed = [False]

        def validate_and_rename(new_name: str) -> bool:
            """Validate the new name and perform the rename."""
            new_name = new_name.strip()
            # No change needed if name is the same
            if new_name == current_name:
                return True
            # Validate the name
            error = self._validate_name(new_name, path.parent, "Rename")
            if error:
                messagebox.showerror("Rename Failed", error, parent=self)
                return False
            # Perform the rename
            new_path = path.parent / new_name
            try:
                path.rename(new_path)
                # Update name_map if the old path had a mapping
                self._update_name_map_entry(path, new_path)
                self.refresh()
                self._trigger_change_callback()
                return True
            except Exception as e:
                messagebox.showerror("Rename Failed", f"Could not rename:\n{e}", parent=self)
                return False

        def complete_rename(event=None) -> None:
            """Complete the rename operation."""
            if rename_completed[0]:
                return
            rename_completed[0] = True
            new_name = rename_entry.get()
            rename_entry.destroy()
            validate_and_rename(new_name)

        def cancel_rename(event=None) -> None:
            """Cancel the rename operation."""
            if rename_completed[0]:
                return
            rename_completed[0] = True
            rename_entry.destroy()

        # Bind events
        rename_entry.bind("<Return>", complete_rename)
        rename_entry.bind("<FocusOut>", complete_rename)
        rename_entry.bind("<Escape>", cancel_rename)


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
        resolved = self._resolve_path_safe(path)
        return self._name_map.get(resolved)


    def _node_label_with_map(self, path: pathlib.Path) -> str:
        """Return the display label for a path, checking name map first."""
        mapped = self._get_mapped_name(path)
        if mapped is not None:
            return mapped
        return self._node_label(path)


    def _set_name_map(self, name_map: Optional[dict[os.PathLike[str] | str, str]]) -> None:
        """Normalize and store the name mapping dictionary."""
        self._name_map.clear()
        if name_map:
            for key, value in name_map.items():
                resolved = self._resolve_path_safe(pathlib.Path(key).expanduser())
                self._name_map[resolved] = value


    def _resolve_path_safe(self, path: pathlib.Path) -> pathlib.Path:
        """Resolve a path safely, returning original path if resolution fails."""
        try:
            return path.resolve()
        except (OSError, RuntimeError):
            return path


    def _update_name_map_entry(self, old_path: pathlib.Path, new_path: pathlib.Path) -> None:
        """Transfer a name_map entry from old_path to new_path if it exists."""
        mapped_name = self._get_mapped_name(old_path)
        if mapped_name is None:
            return
        # Remove old mappings
        self._name_map.pop(old_path, None)
        self._name_map.pop(self._resolve_path_safe(old_path), None)
        # Add mapping for new path
        self._name_map[self._resolve_path_safe(new_path)] = mapped_name


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
        """Return a tuple key that sorts numeric parts numerically and text parts case-insensitively, with type tags to avoid TypeError."""
        parts = re.findall(r'\d+|\D+', name.lower())
        key = []
        for part in parts:
            if part.isdigit():
                key.append((0, int(part)))
            else:
                key.append((1, part))
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
    # -------------------------------
    browser = FileBrowser(root, path=".")
    browser.pack(fill="both", expand=True)

    def handle_open(path):
        print("Opened:", path)

    browser.on_open = handle_open


    # Demo with filename mapping
    # --------------------------
    current_dir = pathlib.Path(".").resolve()
    name_mapping = {
        current_dir: "🏠 Root",
        current_dir / "setup.py": "Module Setup",
    }

    browser2 = FileBrowser(root, path=".", show_cols=["size"], name_map=name_mapping)
    browser2.pack(fill="both", expand=True)

    root.mainloop()