"""
Tkinter widgets for displaying rich or plain text with Markdown-like formatting.

Supported values:
- Headings: `#`, `##`, `###` at line start
- Inline styles: `*italic*, **bold**, ***bold italic***, __underline__`, and combinations.
- Justification blocks: `[justify:left]`...`[/justify]`, `[justify:center]`, `[justify:right]`

Public API:
- TextPanel: embeddable widget `(ttk.Frame)`
- TextWindow: standalone widget `(tk.Toplevel)`

See `nenotk/widgets/tkmarktext/README.md` for more details.
"""
#region Imports

# Standard
import os
from PIL import Image, ImageTk

# tkinter
import tkinter as tk
from tkinter import scrolledtext, ttk

# NenoTk
from nenotk.utils import window_helper

# Typing
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


#endregion
#region Shared Logic


__all__ = ["TextPanel", "TextWindow"]


class _Mixin:
    """Helpers to render text into a Tk Text/ScrolledText widget."""
    def _setup_text_widgets(self, footer: Optional[Union[str, Callable[[Any], Any]]] = None, include_scrollbar: bool = True) -> None:
        """Create textbox (optionally with scrollbar) and footer."""
        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(expand=True, fill="both")
        if include_scrollbar:
            self.textbox = scrolledtext.ScrolledText(self.content_frame, wrap="word", height=1, padx=6, pady=2, insertbackground="white")
        else:
            self.textbox = tk.Text(self.content_frame, wrap="word", height=1, padx=6, pady=2, insertbackground="white")
        self.textbox.pack(expand=True, fill='both')
        self.textbox.config(state='disabled')
        self.textbox.bind("<FocusOut>", lambda e: self.textbox.tag_remove("sel", "1.0", "end"), add="+")
        self._configure_text_tags()
        self.set_font(color="#0B0B16")
        self.current_text = None
        self.current_rich_text = True
        self.footer = footer
        self.footer_widget = None
        if self.footer:
            self._create_footer()
        self.context_menu = tk.Menu(self.textbox, tearoff=0)
        self.context_menu.add_command(label="Copy", accelerator="Ctrl+C", command=self._copy_selection)
        self.textbox.bind("<Button-3>", self._show_context_menu, add="+")


    def _configure_text_tags(self):
        """Configure text tags for headings, styles, and justification."""
        for tag, font_spec in self._tag_font_specs().items():
            self._apply_tag_config(tag, font_spec=font_spec)
        self.textbox.tag_config("justify_left", justify='left')
        self.textbox.tag_config("justify_center", justify='center')
        self.textbox.tag_config("justify_right", justify='right')


    # new helper methods to reduce duplication
    def _tag_font_specs(self) -> Dict[str, Tuple[Union[str, int], ...]]:
        """Return default font tuples for all tags."""
        return {
            "#heading":     ("", 16, "bold"),
            "##heading":    ("", 14, "bold"),
            "###heading":   ("", 12, "bold"),
            "content":      ("", 10),
            "bold":         ("", 10, "bold"),
            "italic":       ("", 10, "italic"),
            "bolditalic":   ("", 10, "bold", "italic"),
            "underline":    ("", 10),
            "boldunderline": ("", 10, "bold"),
            "italicunderline": ("", 10, "italic"),
            "bolditalicunderline": ("", 10, "bold", "italic"),
        }


    def _underline_tags(self) -> Tuple[str, ...]:
        """Return tags that should have underline=True."""
        return ("underline", "boldunderline", "italicunderline", "bolditalicunderline")


    def _apply_tag_config(self, tag: str, font_spec: Optional[Tuple[Any, ...]] = None, family: Optional[str] = None, color: Optional[str] = None) -> None:
        """Centralize configuring a tag's font, underline and colors.

        - font_spec: set explicit font tuple
        - family: override family while preserving size/style
        - color: set foreground and selection colors
        """
        if font_spec is not None:
            self.textbox.tag_config(tag, font=font_spec)
        # If family requested, keep size/style by modifying the existing font
        if family:
            current_font = self.textbox.tag_cget(tag, "font")
            font_parts = list(self.textbox.tk.splitlist(current_font)) if current_font else ["", 10]
            font_parts[0] = family
            self.textbox.tag_config(tag, font=tuple(font_parts))
        # Set color/selection colors if requested
        if color:
            self.textbox.tag_config(tag, foreground=color, selectbackground="#0078d7", selectforeground="white")
        # Ensure underline is set for the defined underline tags
        if tag in self._underline_tags():
            self.textbox.tag_config(tag, underline=True)


    def _show_context_menu(self, event: tk.Event) -> str:
        """Show context menu at mouse position, enabling Copy if selection exists."""
        try:
            has_selection = bool(self.textbox.tag_ranges("sel"))
            if has_selection:
                self.context_menu.entryconfigure(0, state="normal")
            else:
                self.context_menu.entryconfigure(0, state="disabled")
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            try:
                self.context_menu.grab_release()
            except Exception:
                pass
        return "break"


    def _create_footer(self) -> None:
        """Create footer widget from string or callable."""
        if self.footer_widget or not self.footer:
            return
        elif callable(self.footer):
            self.footer_widget = self.footer(self)
            if self.footer_widget is not None:
                self.footer_widget.pack(side="bottom", fill="x")
        else:
            self.footer_widget = ttk.Label(self, text=str(self.footer), font=("", 10))
            self.footer_widget.pack(side="bottom", fill="x")


#endregion
#region API / Config


    def configure(self, cnf: Optional[Union[Dict[str, Any], Any]] = None, **kwargs: Any) -> Any:
        """Extend configure to handle custom options."""
        custom_keys = ("text", "rich_text", "footer", "include_scrollbar")
        kwargs = dict(kwargs)
        cnf_payload = dict(cnf) if isinstance(cnf, dict) else cnf
        custom_options = {}
        if isinstance(cnf_payload, dict):
            for key in custom_keys:
                if key in cnf_payload:
                    custom_options[key] = cnf_payload.pop(key)
        for key in custom_keys:
            if key in kwargs:
                custom_options[key] = kwargs.pop(key)
        if isinstance(cnf, dict):
            result = super().configure(cnf_payload, **kwargs)
        elif cnf is None:
            result = super().configure(**kwargs)
        else:
            result = super().configure(cnf, **kwargs)
        if custom_options:
            widget_ready = hasattr(self, "textbox")
            if widget_ready:
                if ("footer" in custom_options) or ("include_scrollbar" in custom_options):
                    self.content_frame.destroy()
                    footer_arg = custom_options.get("footer", None)
                    include_arg = custom_options.get("include_scrollbar", True)
                    self._setup_text_widgets(footer=footer_arg, include_scrollbar=include_arg)
                if ("text" in custom_options) or ("rich_text" in custom_options):
                    text = custom_options.get("text", getattr(self, "current_text", None))
                    rich_text = custom_options.get("rich_text", getattr(self, "current_rich_text", True))
                    self._update_text(text, rich_text)
        return result


    def config(self, cnf: Optional[Union[Dict[str, Any], Any]] = None, **kwargs: Any) -> Any:
        """Alias for configure."""
        return self.configure(cnf, **kwargs)


    def set_text(self, text: Optional[Union[str, Dict[Any, Any], List[Any], Tuple[Any, ...]]] = None, rich_text: bool = True) -> None:
        """Update displayed text."""
        self._update_text(text, rich_text)


    def set_font(self, family: Optional[str] = None, color: Optional[str] = None) -> None:
        """Set font family and color for all text tags."""
        for tag in self._tag_font_specs().keys():
            self._apply_tag_config(tag, family=family, color=color)


#endregion
#region Content


    def _update_text(self, text: Optional[Union[str, Dict[Any, Any], List[Any], Tuple[Any, ...]]] = None, rich_text: bool = True) -> None:
        """Render text into the textbox."""
        self.textbox.config(state='normal')
        self.textbox.delete("1.0", "end")
        stripped_text = self._strip_leading_whitespace(text)
        if stripped_text is None:
            self.textbox.insert("end", "No text available")
            self.textbox.config(state='disabled')
            self.current_text = None
            self.current_rich_text = rich_text
            return
        if rich_text:
            if not isinstance(stripped_text, str):
                self.textbox.insert("end", "Error: Rich text mode requires a string input.")
            else:
                self._insert_rich_text(stripped_text)
        else:
            self._insert_simple_text(stripped_text)
        self.textbox.config(state='disabled')
        self.current_text = text
        self.current_rich_text = rich_text


    def _strip_leading_whitespace(self, text: Optional[Union[str, Dict[Any, Any], List[Any], Tuple[Any, ...]]]) -> Optional[Union[str, Dict[Any, Any], List[Any], Tuple[Any, ...]]]:
        """Strip leading whitespace from strings, dict values, and list items."""
        if text is None:
            return None
        if isinstance(text, str):
            return text.lstrip()
        elif isinstance(text, dict):
            return {k.lstrip() if isinstance(k, str) else k: v.lstrip() if isinstance(v, str) else v for k, v in text.items()}
        elif isinstance(text, (list, tuple)):
            return type(text)(item.lstrip() if isinstance(item, str) else item for item in text)
        return text


    def _insert_simple_text(self, text: Union[str, Dict[Any, Any], List[Any], Tuple[Any, ...]]) -> None:
        """Insert text without formatting."""
        try:
            out = ""
            if isinstance(text, dict):
                for heading, content in text.items():
                    out += f"{heading}\n{content}\n\n"
            elif isinstance(text, list):
                for item in text:
                    out += f"{str(item)}\n"
            else:
                out = str(text)
            self.textbox.insert("end", out)
        except Exception as e:
            self.textbox.insert("end", f"Error: {str(e)}")


    def _get_tags_with_justify(self, base_tags: Union[str, Tuple[str, ...]], justify_type: Optional[str]) -> Tuple[str, ...]:
        """Return tag tuple with optional justification tag."""
        if justify_type:
            if isinstance(base_tags, tuple):
                return base_tags + (justify_type,)
            else:
                return (base_tags, justify_type)
        return base_tags if isinstance(base_tags, tuple) else (base_tags,)


    def _insert_rich_text(self, text: str) -> None:
        """Insert text using Markdown-like rules and justification tags."""
        try:
            blocks = self._parse_justify_blocks(text)
            for justify_type, block_text in blocks:
                lines = block_text.splitlines()
                blank_line_pending = False
                for line in lines:
                    stripped = line.strip()
                    if stripped.startswith("### "):
                        heading_text = stripped[4:]
                        tags = self._get_tags_with_justify("###heading", justify_type)
                        self.textbox.insert("end", heading_text + "\n", tags)
                        blank_line_pending = False
                    elif stripped.startswith("## "):
                        heading_text = stripped[3:]
                        tags = self._get_tags_with_justify("##heading", justify_type)
                        self.textbox.insert("end", heading_text + "\n", tags)
                        blank_line_pending = False
                    elif stripped.startswith("# "):
                        heading_text = stripped[2:]
                        tags = self._get_tags_with_justify("#heading", justify_type)
                        self.textbox.insert("end", heading_text + "\n", tags)
                        blank_line_pending = False
                    elif stripped:
                        formatted_parts = self._parse_style(line)
                        for tag_name, txt in formatted_parts:
                            tags = self._get_tags_with_justify(tag_name, justify_type)
                            self.textbox.insert("end", txt, tags)
                        self.textbox.insert("end", "\n")
                        blank_line_pending = False
                    else:
                        if not blank_line_pending:
                            self.textbox.insert("end", "\n")
                            blank_line_pending = True
        except Exception as e:
            self.textbox.insert("end", f"Error: {str(e)}")


    def _copy_selection(self) -> None:
        """Copy selected text to clipboard."""
        try:
            if not self.textbox.tag_ranges("sel"):
                return
            selected = self.textbox.get("sel.first", "sel.last")
            self.textbox.clipboard_clear()
            self.textbox.clipboard_append(selected)
        except tk.TclError:
            pass


#endregion
#region Parse / Format


    def _parse_justify_blocks(self, text: str) -> List[Tuple[Optional[str], str]]:
        """Return (justify_tag_or_None, text_segment) tuples for justify blocks."""
        import re
        blocks = []
        pattern = r'\[justify:(left|center|right)\](.*?)\[/justify\]'
        last_end = 0
        for match in re.finditer(pattern, text, re.DOTALL):
            if match.start() > last_end:
                pre_text = text[last_end:match.start()]
                if pre_text:
                    blocks.append((None, pre_text))
            alignment = match.group(1)
            content = match.group(2)
            justify_tag = f"justify_{alignment}"
            if content:
                blocks.append((justify_tag, content))
            last_end = match.end()
        if last_end < len(text):
            post_text = text[last_end:]
            if post_text:
                blocks.append((None, post_text))
        if not blocks:
            blocks.append((None, text))
        blocks = [(jt, seg) for jt, seg in blocks if seg and seg.strip() != ""]
        return blocks


    def _parse_style(self, text: str) -> List[Tuple[Union[str, Tuple[str, ...]], str]]:
        """Parse bold/italic/underline markers and return mapped tag names.

        Supports combined modes (boldunderline, italicunderline, bolditalicunderline)
        and correct nesting like *__italic underline__*.
        """
        # Fast-path when no markers present
        if not any(c in text for c in ("*", "_")):
            return [("content", text)]
        tokens, token_styles = self._style_token_definitions()
        style_markers = self._find_style_markers(text, tokens)
        pairs = self._pair_style_markers(style_markers, text)
        events, skip_positions = self._build_style_events_and_skip_positions(pairs, token_styles)
        style_to_tag_map = self._style_to_tag_map()

        def style_set_to_tag(active: set) -> str:
            return style_to_tag_map.get(frozenset(active), "content")

        out_segments = self._emit_segments_from_events(text, events, skip_positions, style_set_to_tag)
        merged = self._merge_adjacent_segments(out_segments)
        return merged if merged else [("content", text)]


    def _style_token_definitions(self) -> Tuple[List[str], Dict[str, set]]:
        """Return token order and mapping of token -> styles."""
        tokens = ["***", "**", "__", "*"]
        token_styles = {
            "***": {"bold", "italic"},
            "**": {"bold"},
            "__": {"underline"},
            "*": {"italic"},
        }
        return tokens, token_styles


    def _find_style_markers(self, text: str, tokens: List[str]) -> List[Dict[str, Any]]:
        """Scan text and return a list of marker occurrences (pos, token, len, paired)."""
        n = len(text)
        style_markers: List[Dict[str, Any]] = []
        i = 0
        while i < n:
            matched = None
            for token in tokens:
                if text.startswith(token, i):
                    matched = token
                    break
            if matched:
                style_markers.append({"pos": i, "token": matched, "len": len(matched), "paired": False})
                i += len(matched)
            else:
                i += 1
        return style_markers


    def _pair_style_markers(self, style_markers: List[Dict[str, Any]], text: str) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
        """Pair opening/closing style markers, preserving nesting and skipping invalid pairs."""
        stack: List[Dict[str, Any]] = []
        pairs: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
        for occ in style_markers:
            if stack and stack[-1]["token"] == occ["token"]:
                open_occ = stack[-1]
                inner_start = open_occ["pos"] + open_occ["len"]
                inner_end = occ["pos"]
                # require non-empty inner content and no newline in-between
                if inner_end > inner_start and "\n" not in text[inner_start:inner_end]:
                    stack.pop()
                    open_occ["paired"] = True
                    occ["paired"] = True
                    pairs.append((open_occ, occ))
                    continue
            stack.append(occ)
        return pairs


    def _build_style_events_and_skip_positions(self, pairs: List[Tuple[Dict[str, Any], Dict[str, Any]]], token_styles: Dict[str, set]) -> Tuple[Dict[int, List[Tuple[str, str]]], set]:
        """From pairs build events (add/remove) at content boundaries and collect token positions to skip."""
        events: Dict[int, List[Tuple[str, str]]] = {}
        skip_positions: set = set()
        for open_occ, close_occ in pairs:
            start_content = open_occ["pos"] + open_occ["len"]
            end_content = close_occ["pos"]
            # mark token characters to skip in output
            for p in range(open_occ["pos"], open_occ["pos"] + open_occ["len"]):
                skip_positions.add(p)
            for p in range(close_occ["pos"], close_occ["pos"] + close_occ["len"]):
                skip_positions.add(p)
            # record add/remove events
            for style in token_styles[open_occ["token"]]:
                events.setdefault(start_content, []).append(("add", style))
                events.setdefault(end_content, []).append(("remove", style))
        return events, skip_positions


    def _style_to_tag_map(self) -> Dict[frozenset, str]:
        """Return mapping from active style set to tag name."""
        return {
            frozenset(): "content",
            frozenset({"bold"}): "bold",
            frozenset({"italic"}): "italic",
            frozenset({"bold", "italic"}): "bolditalic",
            frozenset({"underline"}): "underline",
            frozenset({"bold", "underline"}): "boldunderline",
            frozenset({"italic", "underline"}): "italicunderline",
            frozenset({"bold", "italic", "underline"}): "bolditalicunderline",
        }


    def _emit_segments_from_events(self, text: str, events: Dict[int, List[Tuple[str, str]]], skip_positions: set, style_set_to_tag: Callable[[set], str]) -> List[Tuple[str, str]]:
        """Scan text applying events and producing (tag, segment) tuples; preserves original event/flush semantics."""
        n = len(text)
        style_counts: Dict[str, int] = {}
        active_set: set = set()
        out_segments: List[Tuple[str, str]] = []
        buf: List[str] = []
        idx = 0
        while idx < n:
            if idx in events:
                # flush current buffer with previous style
                if buf:
                    out_segments.append((style_set_to_tag(active_set), "".join(buf)))
                    buf = []
                # apply all events at this position
                for op, style in events[idx]:
                    if op == "add":
                        style_counts[style] = style_counts.get(style, 0) + 1
                    else:  # remove
                        cnt = style_counts.get(style, 0) - 1
                        if cnt <= 0:
                            style_counts.pop(style, None)
                        else:
                            style_counts[style] = cnt
                active_set = set(style_counts.keys())
            # Append character unless it's part of a paired token
            if idx not in skip_positions:
                buf.append(text[idx])
            idx += 1
        # Handle any trailing events at end (e.g., closing at end) - flush if needed
        if n in events:
            if buf:
                out_segments.append((style_set_to_tag(active_set), "".join(buf)))
                buf = []
            for op, style in events[n]:
                if op == "add":
                    style_counts[style] = style_counts.get(style, 0) + 1
                else:
                    cnt = style_counts.get(style, 0) - 1
                    if cnt <= 0:
                        style_counts.pop(style, None)
                    else:
                        style_counts[style] = cnt
            active_set = set(style_counts.keys())
        if buf:
            out_segments.append((style_set_to_tag(active_set), "".join(buf)))
        return out_segments


    def _merge_adjacent_segments(self, segments: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        """Merge consecutive segments with the same tag."""
        merged: List[Tuple[str, str]] = []
        for tag, seg in segments:
            if not seg:
                continue
            if merged and merged[-1][0] == tag:
                merged[-1] = (tag, merged[-1][1] + seg)
            else:
                merged.append((tag, seg))
        return merged


#endregion
#region TextWindow


class TextWindow(_Mixin, tk.Toplevel):
    """Toplevel window for displaying formatted or plain text."""
    def __init__(
        self,
        master: Optional[Any] = None,
        text: Optional[Union[str, Dict[Any, Any], List[Any], Tuple[Any, ...]]] = None,
        rich_text: bool = True,
        footer: Optional[Union[str, Callable[[Any], Any]]] = "",
        include_scrollbar: bool = True,
        title: Optional[str] = "Text",
        geometry: Optional[str] = "400x700",
        icon: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        """Initialize TextWindow with configurable parameters."""
        super().__init__(master=master, **kwargs)
        self.set_window_icon(icon)
        self.title(title if title is not None else "Text")
        self.minsize(200, 200)
        if geometry is not None:
            self.geometry(geometry)
        self.bind("<Escape>", self.close_window, add="+")
        self.protocol("WM_DELETE_WINDOW", self.close_window)
        self._setup_widgets(footer=footer, include_scrollbar=include_scrollbar)
        if text is not None:
            self.configure(text=text, rich_text=rich_text)
        self.withdraw()


    def set_window_icon(self, icon):
        if icon is not None:
            try:
                # If icon is a string path, try to load as image using Pillow
                if isinstance(icon, str):
                    if os.path.isfile(icon):
                        img = Image.open(icon)
                        tk_img = ImageTk.PhotoImage(img)
                        self.iconphoto(False, tk_img)
                        return
                # If icon is already a Tk image object
                if hasattr(icon, "tk") and hasattr(icon, "width"):
                    self.iconphoto(False, icon)
                else:
                    self.iconbitmap(icon)
            except Exception:
                pass


    def _setup_widgets(self, footer: Optional[Union[str, Callable[[Any], Any]]] = "", include_scrollbar: bool = True) -> None:
        """Set up window widgets."""
        self._setup_text_widgets(footer=footer, include_scrollbar=include_scrollbar)


    def open_window(
        self,
        text: Optional[Union[str, Dict[Any, Any], List[Any], Tuple[Any, ...]]] = None,
        rich_text: bool = True,
        footer: Optional[Union[str, Callable[[Any], Any]]] = None,
        include_scrollbar: Optional[bool] = None,
        title: Optional[str] = None,
        geometry: Optional[str] = None,
        icon: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        """Show window and update title, geometry, and content."""
        self._update_window(title, geometry)
        # Only pass `text`/`rich_text` to configure when an explicit text
        # value is provided. Calling `open_window()` with no `text`
        # should not clear previously-set content (e.g., from constructor).
        cfg = dict(kwargs)
        if footer is not None:
            cfg["footer"] = footer
        if include_scrollbar is not None:
            cfg["include_scrollbar"] = include_scrollbar
        if text is not None:
            cfg["text"] = text
            cfg["rich_text"] = rich_text
        self.configure(**cfg)
        self.set_window_icon(icon)
        self.deiconify()
        window_helper.center_window(self, to='parent')
        self.lift()


    def _update_window(self, title: Optional[str] = None, geometry: Optional[str] = None) -> None:
        """Update window title and geometry."""
        if title is not None:
            self.title(title)
        if geometry is not None:
            self.geometry(geometry)


    def close_window(self, event: Optional[Any] = None) -> None:
        """Hide the window."""
        self.withdraw()


#endregion
#region TextPanel


class TextPanel(_Mixin, ttk.Frame):
    """Embeddable panel for displaying formatted or plain text."""
    def __init__(
            self,
            master: Optional[Any] = None,
            text: Optional[Union[str, Dict[Any, Any], List[Any], Tuple[Any, ...]]] = None,
            rich_text: bool = True,
            footer: Optional[Union[str, Callable[[Any], Any]]] = None,
            include_scrollbar: bool = True,
            **kwargs: Any
        ) -> None:
        """Initialize TextPanel."""
        kwargs = dict(kwargs)
        style = kwargs.pop("style", None)
        background = kwargs.pop("background", kwargs.pop("bg", None))
        init_kwargs = kwargs
        if style is not None:
            init_kwargs["style"] = style
        super().__init__(master=master, **init_kwargs)
        if background is not None:
            style_name = style or f"TextPanel{ id(self) }.TFrame"
            ttk.Style().configure(style_name, background=background)
            self.configure(style=style_name)
        self._setup_text_widgets(footer=footer, include_scrollbar=include_scrollbar)
        if text is not None:
            self.configure(text=text, rich_text=rich_text)
        else:
            self.textbox.config(state='disabled')


#endregion
