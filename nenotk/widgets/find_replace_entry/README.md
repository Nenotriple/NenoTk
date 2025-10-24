# FindReplaceEntry

An embeddable Find/Replace panel for a `tk.Text`, with case sensitivity, whole-word, and regex support, plus next/previous navigation.

## Features

- Works with an associated `tk.Text` for searching and replacing.
- Options: Case sensitive, match whole word, and regular expressions.
- Keyboard-friendly: Enter/Shift+Enter for next/previous; Esc to hide.
- Highlights all matches and the current match distinctly.

## Quick Start

The following example creates a simple text editor with a find/replace bar that can be shown/hidden with Ctrl+F/Esc:

>*The parent frame must use `.grid()` layout for show/hide to function.*

```python
import tkinter as tk
from tkinter import ttk
import nenotk as ntk

root = tk.Tk()
frame = ttk.Frame(root)
frame.pack(fill="both", expand=True)

text = tk.Text(frame, wrap="word")
text.grid(row=1, column=0, sticky="nsew")
frame.rowconfigure(1, weight=1)
frame.columnconfigure(0, weight=1)

findbar = ntk.FindReplaceEntry(frame, text)
findbar.grid(row=0, column=0, sticky="ew")
findbar.grid_remove()  # start hidden

text.bind("<Control-f>", lambda e: findbar.show_widget())
text.bind("<Escape>",   lambda e: findbar.hide_widget())

root.mainloop()
```

## API

- Class: `FindReplaceEntry(parent, text_widget, **kwargs)`
  - Embeddable find/replace UI; place with `grid()` in a container using grid layout
- Methods
  - `show_widget()` / `hide_widget()`
  - `search_for_text(text: str)`
  - `perform_search(event=None)`
  - `next_match()` / `previous_match()`
  - `replace_current()` / `replace_all()`
- Helper class: `TextSearchManager(text_widget)`
  - `find_all(search_term, case_sensitive, match_whole_word, use_regex) -> int`
  - `next_match()` / `prev_match()` / `clear_highlights()`
  - `replace_current(replacement: str) -> bool`
  - `replace_all(search_term, replacement, ...) -> int`

## Notes

- The container of `FindReplaceEntry` must use `grid` for proper show/hide.
- Highlights use tags; current match is emphasized and scrolled into view.
