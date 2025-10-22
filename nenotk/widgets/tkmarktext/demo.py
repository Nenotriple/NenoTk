"""Minimal-yet-complete demonstration of tkmarktext.

The examples below cover:
- TextPanel in rich/simple modes, with and without custom footers.
- TextWindow variations, including geometry tweaks and fallback formatting.
- Runtime content updates, footer changes, and rich formatting markers.
- Custom callable footers that return custom widgets.
- Markdown-style # headings for rich text formatting.
"""


import tkinter as tk
from tkinter import ttk

# Import tkmarktext components
from tkmarktext import TextPanel, TextWindow


RICH_TEXT = """# tkmarktext Overview
**tkmarktext** makes it easy to write and display formatted text in Tkinter using Text widgets.

**Highlights:**
- **TextWindow** is a pop-up window
- **TextPanel** is an embeddable frame

## Formatting Guide

Start a line with #, ##, or ### for headings:
-
# Heading 1
-
## Heading 2
-
### Heading 3
-
**Heading 4**
(Just bold text)

Text can be made italic, bold, bold italic, and underlined, by wrapping with markers:
- *italic*, *(single asterisk)*
- **bold**, *(double asterisks)*
- ***bold italic***, *(triple asterisks)*
- __underline__, *(double underscore)*
- *__italic underline__*, *(double underscore + single asterisk)*
- **__bold underline__**, *(double underscore + double asterisks)*
- ***__bold italic underline__***, *(double underscore + triple asterisks)*
"""


JUSTIFY_TEXT = """[justify:left]# Left-justify (default)
This text is **left-aligned** with *formatted* content.
Multiple lines stay left-aligned.[/justify]

[justify:center]
# Center-justify
This entire block is **centered**.
Even with *italic* and **bold** formatting.
[/justify]

[justify:right]
# Right-justify
Everything here appears on the **right side**.
Great for *signatures* or credits.
[/justify]

normal text (default left-justified)

[justify:left]Some text to the left,[/justify] [justify:center]some text in the center,[/justify] [justify:right]some text to the right.[/justify]
"""


LIST_TEXT = [
    "Simple mode accepts iterables.",
    "Each item is written on its own line.",
    "Great for lightweight instructions.",
]


STRING_TEXT = """Pass a plain string to render it as-is.

This example uses a custom footer to showcase branding or version info.
"""


DYNAMIC_CONTENT = [
    "# Dynamic Rich\nThis block shows **bold**, *italic*, and multiple lines.\n\n## Subsection\nMarkdown-style headings work great!",
    ["Dynamic list entry", "Fallback from rich mode to simple", "Still readable"],
    "Plain string update — useful for quick notices.",
]


class DemoApp:
    """Tiny UI wrapper that wires every tkmarktext feature together."""
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("tkmarktext Demo")
        self._center_window(1280, 720)

        self.windows: dict[str, TextWindow] = {}
        self.dynamic_index = 0
        self.dynamic_format = "rich"
        self.dynamic_footer_updates = 0

        self._build_static_panels()
        self._build_dynamic_section()
        self._build_window_section()


    def _center_window(self, width, height):
        """Center the window on the screen."""
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")


    def _build_static_panels(self) -> None:
        container = ttk.LabelFrame(self.root, text="TextPanel basics")
        container.pack(fill="both", expand=True, padx=10, pady=10)
        container.columnconfigure((0, 1, 2), weight=1)
        container.rowconfigure(0, weight=1)
        # Rich text
        TextPanel(container, text=RICH_TEXT, rich_text=True, footer="Demo footer").grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        # Justification demo
        justification = TextPanel(container, text=JUSTIFY_TEXT, rich_text=True, footer="Justification Demo")
        justification.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        # No footer
        TextPanel(container, text=LIST_TEXT, rich_text=False, include_scrollbar=False).grid(row=0, column=2, sticky="nsew", padx=5, pady=5)



    def _build_dynamic_section(self) -> None:
        frame = ttk.LabelFrame(self.root, text="Dynamic TextPanel controls")
        frame.pack(fill="both", padx=10, pady=(0, 10))
        frame.rowconfigure(0, weight=1)
        # Use callable footer to create custom widget
        self.dynamic_panel = TextPanel(frame, text=DYNAMIC_CONTENT[0], rich_text=True, footer=self._create_custom_footer, include_scrollbar=False)
        self.dynamic_panel.pack(fill="both", expand=True, padx=10, pady=10)
        self.dynamic_panel.textbox.config(height=6)
        buttons = ttk.Frame(frame)
        buttons.pack(pady=5, anchor="s")
        ttk.Button(buttons, text="Next content", command=self._next_dynamic_content).pack(side="left", padx=5)
        ttk.Button(buttons, text="Toggle rich/simple", command=self._toggle_dynamic_format).pack(side="left", padx=5)
        ttk.Button(buttons, text="Update footer", command=self._update_dynamic_footer).pack(side="left", padx=5)
        ttk.Button(buttons, text="Show None", command=self._clear_dynamic_content).pack(side="left", padx=5)


    def _create_custom_footer(self, parent):
        """Example callable footer that returns a custom frame with multiple widgets."""
        footer_frame = ttk.Frame(parent)
        self.custom_footer_label = ttk.Label(footer_frame, text="Custom footer with button", font=("", 9, "italic"))
        self.custom_footer_label.pack(side="left", padx=5)
        ttk.Button(footer_frame, text="Click me!", command=lambda: print("Footer button clicked!")).pack(side="right", padx=5)
        return footer_frame


    def _build_window_section(self) -> None:
        frame = ttk.LabelFrame(self.root, text="TextWindow samples")
        frame.pack(fill="x", padx=10, pady=(0, 10))
        frame.columnconfigure((0, 1, 2, 3), weight=1)
        demos = [
            ("Rich text", lambda: self._open_window("rich", "Rich format", RICH_TEXT, True)),
            ("Simple list", lambda: self._open_window("list", "Simple list", LIST_TEXT, False)),
            ("Simple text", lambda: self._open_window("simple", "Simple text", STRING_TEXT, False)),
            ("No content", lambda: self._open_window("none", "No content", None, True)),
            ("Large geometry", lambda: self._open_window("large", "Large window", RICH_TEXT, True, "800x600")),
            ("Small geometry", lambda: self._open_window("small", "Small window", RICH_TEXT, True, "320x240")),
            ("Rich fallback", lambda: self._open_window("fallback", "Rich mode + list", LIST_TEXT, True)),
            # --- Add footer demo buttons below ---
            ("Footer (string)", lambda: self._open_window_with_footer("footer_str", "Footer String", RICH_TEXT, True, footer="String footer!")),
            ("Footer (callable)", lambda: self._open_window_with_footer("footer_cb", "Footer Callable", RICH_TEXT, True, footer=self._window_custom_footer)),
        ]
        for idx, (label, command) in enumerate(demos):
            row, col = divmod(idx, 4)
            ttk.Button(frame, text=label, command=command, width=18).grid(row=row, column=col, padx=5, pady=5, sticky="ew")


    def _open_window_with_footer(self, key: str, title: str, text, rich_text: bool, geometry: str | None = None, footer=None) -> None:
        window = self.windows.setdefault(key, TextWindow(self.root))
        window.open_window(title=title, text=text, rich_text=rich_text, geometry=geometry)
        # Set footer after open to ensure it's updated
        window.configure(footer=footer)


    def _window_custom_footer(self, parent):
        frame = ttk.Frame(parent)
        ttk.Label(frame, text="Custom Footer Widget", font=("", 9, "italic")).pack(side="left", padx=5)
        ttk.Button(frame, text="Footer Btn", command=lambda: print("TextWindow footer button clicked!")).pack(side="right", padx=5)
        return frame


    def _next_dynamic_content(self) -> None:
        self.dynamic_index = (self.dynamic_index + 1) % len(DYNAMIC_CONTENT)
        self.dynamic_panel.set_text(DYNAMIC_CONTENT[self.dynamic_index], self.dynamic_format)


    def _toggle_dynamic_format(self) -> None:
        self.dynamic_format = not self.dynamic_format
        self.dynamic_panel.set_text(DYNAMIC_CONTENT[self.dynamic_index], self.dynamic_format)


    def _update_dynamic_footer(self) -> None:
        self.dynamic_footer_updates += 1
        # Update the custom footer label text directly
        self.custom_footer_label.config(text=f"Footer update #{self.dynamic_footer_updates}")


    def _clear_dynamic_content(self) -> None:
        self.dynamic_panel.set_text(None, self.dynamic_format)


    def _open_window(self, key: str, title: str, text, rich_text: bool, geometry: str | None = None) -> None:
        window = self.windows.setdefault(key, TextWindow(self.root))
        window.open_window(title=title, text=text, rich_text=rich_text, geometry=geometry)


    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    DemoApp().run()


if __name__ == "__main__":
    main()
