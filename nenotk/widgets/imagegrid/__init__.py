"""
# Purpose
Scrollable thumbnail browser widget for Tkinter with incremental loading, caching, and selection callbacks.

## API
- Class: `ImageGrid(master, image_files=None) -> ttk.Frame`
    - `initialize(image_files=None)`: scan the provided directory or iterable and populate thumbnails.
    - `reload_grid()`: rebuild thumbnails for the current `image_size` bucket.
    - `load_images(all_images=False)`: load the next batch or every remaining image.
    - `on_select`: callback attribute receiving `(index, path)` when the selection changes.

## Notes
- Supports PNG, JPEG, WebP, TIFF, BMP variants via Pillow image processing.
- Slider adjusts thumbnail size presets (1-5) and reuses a per-size Pillow cache.
- Columns recalculate on parent resize and keep the active thumbnail centered using `ScrollFrame`.

## Example
```
import tkinter as tk
import nenotk as ntk

root = tk.Tk()
grid = ntk.ImageGrid(root)
grid.pack(fill="both", expand=True)
grid.initialize(image_files="path/to/images")
root.mainloop()
```
"""
#region Imports


# Standard
import os

# tkinter
from tkinter import ttk, Frame

# Third-Party
from PIL import Image, ImageTk, ImageDraw

# Local
from nenotk.widgets.scrollframe import ScrollFrame

__all__ = ["ImageGrid"]


#endregion
#region ImageGrid


class ImageGrid(ttk.Frame):
    def __init__(self, master: 'Frame', image_files=None):
        super().__init__(master)
        self.supported_types = (".png", ".webp", ".jpg", ".jpeg", ".jpg_large", ".jfif", ".tif", ".tiff", ".bmp")
        self.cache = {1: {}, 2: {}, 3: {}, 4: {}, 5: {}}
        self._raw_images_input = image_files
        self._parent_resize_after_id = None
        self.last_parent_sz = (None, None)
        self._pending_parent_sz = None
        self._last_column_count = None
        self.initial_selected = None
        self.prev_selected = None
        self.initialized = False
        self.parent_bind = None
        self.on_select = None
        self.thumbnails = {}
        self.selected = None
        self.current_idx = 0
        self.visible = True
        self.images = []


    def initialize(self, image_files=None):
        '''Initialize the ImageGrid widget. Must be called before use.'''
        if self.initialized:
            return
        if image_files is not None:
            self._raw_images_input = image_files
        self._process_images()
        self.working_folder = self._extract_working_folder()
        # Grid configuration
        self.max_width = 80
        self.max_height = 80
        self.images_per_load = 250
        self.padding = 6
        self.rows = 0
        self.columns = 0
        self.loaded = 0
        self.total_images = len(self.images)
        # Smaller grids default to larger thumbnails
        self.image_size = 5 if self.total_images < 10 else 3
        self.image_flag = self.create_image_flag()
        self.create_interface()
        # Delay image loading to allow interface initialization
        self.after(250, self.load_images)
        self.initialized = True
        # Bind to top-level window for resize events
        try:
            toplevel = self.winfo_toplevel()
            if toplevel and self.parent_bind is not toplevel:
                toplevel.bind("<Configure>", self.on_parent_configure, add="+")
                self.parent_bind = toplevel
                self.last_parent_sz = (toplevel.winfo_width(), toplevel.winfo_height())
        except Exception:
            pass


#endregion
#region Interface Creation


    def create_interface(self):
        self.configure_grid_structure()
        self.create_scrollframe()
        self.create_control_row()


    def configure_grid_structure(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)


    def create_scrollframe(self):
        self.scroll_frame = ScrollFrame(self, layout="vertical")
        self.scroll_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 10), pady=(10, 4))
        # The canvas_frame is now the .frame attribute of ScrollFrame
        self.canvas_frame = ttk.Frame(self.scroll_frame.frame, padding=(self.padding, self.padding))
        self.canvas_frame.pack(fill="both", expand=True)


    def create_control_row(self):
        # Main
        frame = ttk.LabelFrame(self, text="Grid Controls", padding=(10, 6))
        frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(3, weight=1)
        # Size
        self.label_size = ttk.Label(frame, text="Size:")
        self.label_size.grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.scale_image_size = ttk.Scale(frame, from_=1, to=5, orient="horizontal")
        self.scale_image_size.set(self.image_size)
        self.scale_image_size.grid(row=0, column=1, sticky="ew")
        self.scale_image_size.bind("<ButtonRelease-1>", self.on_image_size_changed)
        # Info
        self.label_size_value = ttk.Label(frame, text=str(self.image_size), width=3)
        self.label_size_value.grid(row=0, column=2, padx=(8, 12))
        self.label_image_info = ttk.Label(frame, width=16, anchor="e")
        self.label_image_info.grid(row=0, column=3, sticky="e")
        self.scale_image_size.config(command=self.round_scale_input)
        # Load all
        self.button_load_all = ttk.Button(frame, text="Load All", command=self.load_all_images)
        self.button_load_all.grid(row=0, column=4, padx=(12, 6))
        # Refresh
        self.button_refresh = ttk.Button(frame, text="Refresh", command=self.reload_grid)
        self.button_refresh.grid(row=0, column=5)


#endregion
#region Grid Logic


    def reload_grid(self, *args, skip_cache_update=False):
        self.clear_frame(self.canvas_frame)
        self.set_size_settings()
        self.update_image_info_label()
        if skip_cache_update:
            self.create_image_grid()
        else:
            self.update_cache_and_grid()
        self.highlight_thumbnail(self.current_idx)
        self.label_size_value.config(text=str(self.image_size))
        self._last_column_count = self.columns


    def update_cache_and_grid(self):
        self.update_cache()
        self.create_image_grid()


    def update_cache(self):
        image_size_key = self.image_size
        for img_path in self.images:
            if not img_path.lower().endswith(self.supported_types):
                continue
            if img_path not in self.cache[image_size_key]:
                self.create_new_image(img_path)


    def update_image_info_label(self):
        self.label_image_info.config(text=f"{self.loaded} / {self.total_images}")
        self.button_load_all.config(state="disabled" if self.loaded == self.total_images else "normal")


    def clear_frame(self, frame):
        for widget in frame.winfo_children():
            widget.destroy()


    def set_size_settings(self):
        size_settings = {
            1: (45, 45, 13),
            2: (80, 80, 8),
            3: (170, 170, 4),
            4: (240, 240, 3),
            5: (320, 320, 2)
        }
        self.max_width, self.max_height, self.cols = size_settings.get(self.image_size, (80, 80, 8))
        if not hasattr(self, '_last_image_size') or self._last_image_size != self.image_size:
            self.image_flag = self.create_image_flag()
            self._last_image_size = self.image_size
        self.cols = self.calculate_columns()


    def calculate_columns(self):
        frame_width = self.scroll_frame.winfo_width()
        if frame_width <= 1:
            frame_width = self.scroll_frame.winfo_reqwidth()
        available_width = frame_width - (2 * self.padding) - 30  # Account for scrollbar
        thumbnail_width_with_padding = self.max_width + (2 * self.padding)
        columns = max(1, available_width // thumbnail_width_with_padding)
        columns = int(columns)
        return columns


    def create_image_grid(self):
        self.imageset = self.load_image_set()
        self.populate_image_grid()
        self.add_load_more_button()


    def populate_image_grid(self):
        self.thumbnails.clear()
        self.prev_selected = None
        self.initial_selected = None
        for column in range(self.cols):
            self.canvas_frame.columnconfigure(column, weight=1)
        for index, (image, filepath, image_index) in enumerate(self.imageset):
            row, col = divmod(index, self.cols)
            button_style = "Highlighted.TButton" if image_index == self.current_idx else "TButton"
            thumbnail = ttk.Button(self.canvas_frame, image=image, takefocus=False, style=button_style)
            thumbnail.configure(command=lambda idx=image_index: self.on_mouse_click(idx))
            thumbnail.image = image
            thumbnail.grid(row=row, column=col, sticky="nsew")
            self.thumbnails[image_index] = thumbnail
            if image_index == self.current_idx:
                self.initial_selected = thumbnail


    def add_load_more_button(self):
        if self.loaded < self.total_images:
            total_items = len(self.thumbnails)
            final_row = (total_items - 1) // self.columns if total_items else 0
            self.load_more_button = ttk.Button(self.canvas_frame, text="Load More", command=self.load_images)
            self.load_more_button.grid(row=final_row + 1, column=0, columnspan=self.columns, pady=(self.padding * 2), padx=self.padding, sticky="ew")


#endregion
#region Image Loading


    def load_images(self, all_images=False):
        self.loaded = self.total_images if all_images else min(self.loaded + self.images_per_load, self.total_images)
        self.update_image_info_label()
        self.reload_grid()


    def load_all_images(self):
        self.load_images(all_images=True)


    def load_image_set(self):
        images = []
        image_size_key = self.image_size
        for image_index, img_path in enumerate(self.images):
            if not img_path.lower().endswith(self.supported_types):
                continue
            if len(images) >= self.loaded:
                break
            if img_path not in self.cache[image_size_key]:
                new_img = self.create_new_image(img_path)
            else:
                new_img = self.cache[image_size_key][img_path]
            images.append((ImageTk.PhotoImage(new_img), img_path, image_index))
        return images


    def create_new_image(self, img_path):
        new_img = Image.new("RGBA", (self.max_width, self.max_height))
        with Image.open(img_path) as img:
            img.thumbnail((self.max_width, self.max_height))
            position = ((self.max_width - img.width) // 2, (self.max_height - img.height) // 2)
            new_img.paste(img, position)
        self.cache[self.image_size][img_path] = new_img
        return new_img


    def create_image_flag(self):
        """Create a red circular badge indicator for thumbnails."""
        size = self.image_size
        diameter = {1: 14, 2: 20, 3: 28, 4: 36, 5: 44}.get(size, 20)
        margin = max(2, diameter // 5)
        scale = 4
        hr_width, hr_height = self.max_width * scale, self.max_height * scale
        img_flag_hr = Image.new("RGBA", (hr_width, hr_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img_flag_hr)
        hr_diameter = diameter * scale
        hr_margin = margin * scale
        center_x = hr_width - hr_diameter // 2 - hr_margin
        center_y = hr_height - hr_diameter // 2 - hr_margin
        radius = hr_diameter // 2
        circle_bbox = [
            (center_x - radius, center_y - radius),
            (center_x + radius, center_y + radius),
        ]
        draw.ellipse(circle_bbox, fill=(250, 80, 83, 230))
        ring_thickness = max(scale, (diameter // 10) * scale)
        inner_bbox = [
            (circle_bbox[0][0] + ring_thickness, circle_bbox[0][1] + ring_thickness),
            (circle_bbox[1][0] - ring_thickness, circle_bbox[1][1] - ring_thickness),
        ]
        draw.ellipse(inner_bbox, fill=(250, 80, 83, 160))
        bar_height = max(2, diameter // 6) * scale
        bar_width = int(hr_diameter / 1.6)
        bar_bbox = [
            (center_x - bar_width // 2, center_y - bar_height // 2),
            (center_x + bar_width // 2, center_y + bar_height // 2),
        ]
        draw.rounded_rectangle(bar_bbox, radius=bar_height // 2, fill="white")
        img_flag = img_flag_hr.resize((self.max_width, self.max_height), Image.LANCZOS)
        return img_flag


#endregion
#region Image Scanning


    def _process_images(self):
        """Process images input: either a list of paths or a directory path."""
        if self._raw_images_input is None:
            self.images = []
            return
        if isinstance(self._raw_images_input, str):
            if os.path.isdir(self._raw_images_input):
                self.working_folder = self._raw_images_input
                self.images = self._scan_directory(self._raw_images_input)
            else:
                self.images = []
        elif isinstance(self._raw_images_input, (list, tuple)):
            self.images = list(self._raw_images_input)
        else:
            self.images = []


    def _scan_directory(self, directory_path):
        """Scan directory for supported image files."""
        image_files = []
        try:
            for filename in sorted(os.listdir(directory_path)):
                if filename.lower().endswith(self.supported_types):
                    image_files.append(os.path.join(directory_path, filename))
        except Exception:
            pass
        return image_files


    def _extract_working_folder(self):
        """Extract working folder from images."""
        if isinstance(self._raw_images_input, str) and os.path.isdir(self._raw_images_input):
            return self._raw_images_input
        elif self.images:
            return os.path.dirname(self.images[0])
        return ""


#endregion
#region Event Handlers


    def on_mouse_click(self, index):
        """Handle thumbnail selection and emit selection changed event."""
        if index < 0 or index >= len(self.images):
            return
        old_index = self.current_idx
        self.current_idx = index

        self.highlight_thumbnail(index)

        if self.on_select and old_index != index:
            try:
                img_path = self.images[index] if index < len(self.images) else None
                self.on_select(index, img_path)
            except Exception:
                pass


    def on_image_size_changed(self, event=None):
        """Update image_size from slider and reload grid."""
        int_val = int(round(float(self.scale_image_size.get())))
        self.image_size = int_val
        self.label_size_value.config(text=str(int_val))
        self.reload_grid()


    def round_scale_input(self, val):
        int_val = int(round(float(val)))
        if self.scale_image_size.get() != int_val:
            self.scale_image_size.set(int_val)
        self.label_size_value.config(text=int_val)


    def on_parent_configure(self, event=None):
        try:
            if self.parent_bind is not None and getattr(event, "widget", None) is not self.parent_bind:
                return
        except Exception:
            pass
        if not self.visible:
            return
        try:
            new_size = (event.width, event.height)
        except Exception:
            return
        self._pending_parent_sz = new_size
        if self._parent_resize_after_id:
            try:
                self.after_cancel(self._parent_resize_after_id)
            except Exception:
                pass
        self._parent_resize_after_id = self.after(300, self._handle_parent_resize)


    def _handle_parent_resize(self):
        if not self.visible:
            return
        self._parent_resize_after_id = None
        new_size = self._pending_parent_sz or (None, None)
        if new_size == self.last_parent_sz:
            return
        self.last_parent_sz = new_size
        if getattr(self, "initialized", False):
            try:
                new_column_count = self.calculate_columns()
                if new_column_count != self._last_column_count:
                    self._last_column_count = new_column_count
                    self.reload_grid(skip_cache_update=True)
            except Exception:
                try:
                    self.after_idle(lambda: self.reload_grid(skip_cache_update=True))
                except Exception:
                    pass


#endregion
#region Thumbnail Selection


    def get_thumbnail_button(self, identifier):
        """Get thumbnail button by index or filename."""
        if isinstance(identifier, int):
            return self.thumbnails.get(identifier)
        elif isinstance(identifier, str):
            # Search by filename or full path
            for index, img_path in enumerate(self.images):
                if img_path == identifier or os.path.basename(img_path) == identifier:
                    return self.thumbnails.get(index)
        return None


    def highlight_thumbnail(self, index):
        if self.prev_selected:
            self._reset_thumbnail(self.prev_selected)
        button = self.thumbnails.get(index)
        if not button:
            return
        img_path = None
        for _, path, idx in self.imageset:
            if idx == index:
                img_path = path
                break
        if not img_path:
            return
        self.prev_selected = button
        with Image.open(img_path) as img:
            img.thumbnail((self.max_width, self.max_height))
            highlighted_thumbnail = self.apply_highlight(img)
            bordered_thumb = ImageTk.PhotoImage(highlighted_thumbnail)
            button.configure(image=bordered_thumb, style="Highlighted.TButton")
            button.image = bordered_thumb
        self.ensure_thumbnail_visible(button)


    def _reset_thumbnail(self, button):
        if not button:
            return
        for index, btn in self.thumbnails.items():
            if btn == button:
                for img_tk, _, idx in self.imageset:
                    if idx == index:
                        button.configure(image=img_tk, style="TButton")
                        button.image = img_tk
                        return
                break


    def apply_highlight(self, img):
        mask_color = (0, 93, 215, 96)
        base = img.copy().convert("RGBA")
        overlay = Image.new("RGBA", base.size, mask_color)
        return Image.alpha_composite(base, overlay)


    def reset_initial_thumbnail(self):
        if self.initial_selected:
            self.initial_selected.configure(style="TButton")
            self.initial_selected = None


    def ensure_thumbnail_visible(self, button):
        """Scroll to center the selected thumbnail in view."""
        if not button:
            return
        button_index = list(self.thumbnails.values()).index(button)
        row, _ = divmod(button_index, self.cols)
        cell_height = self.max_height + 2 * self.padding
        button_y = row * cell_height
        # Access the canvas from ScrollFrame
        canvas = self.scroll_frame.canvas
        canvas_height = canvas.winfo_height()
        # Get scrollable region
        scrollregion = canvas.cget("scrollregion").split()
        if len(scrollregion) == 4:
            total_height = float(scrollregion[3])
        else:
            return
        # Calculate centered position
        center_pos = (button_y + cell_height / 2) - (canvas_height / 2)
        center_pos = max(0, min(center_pos, total_height - canvas_height))
        target_scroll = center_pos / total_height if total_height > 0 else 0
        canvas.yview_moveto(target_scroll)


#endregion
#region Test Code


if __name__ == "__main__":
    import tkinter as tk
    from tkinter import filedialog

    def select_directory():
        dir_path = filedialog.askdirectory(title="Select Image Directory")
        if dir_path:
            image_grid.initialize(image_files=dir_path)

    root = tk.Tk()
    root.title("ImageGrid Test")
    root.geometry("800x600")

    menubar = tk.Menu(root)
    filemenu = tk.Menu(menubar, tearoff=0)
    filemenu.add_command(label="Open Folder...", command=select_directory)
    filemenu.add_command(label="Exit", command=root.quit)
    menubar.add_cascade(label="File", menu=filemenu)
    root.config(menu=menubar)

    image_grid = ImageGrid(root)
    image_grid.pack(fill="both", expand=True)

    root.mainloop()


#endregion
