# SpellCheckText

A `tk.Text` subclass with integrated spell checking, a custom dictionary, and a right-click context menu for suggestions and actions.

## Features

- Highlights misspelled words with an underline as you type or paste.
- Custom dictionary file for persisting added words.
- Right-click context menu with suggestions and actions (e.g., add to dictionary).
- Efficient, line-scoped re-checks while typing; full re-check on demand.

## Requirements

- Python package: `pyspellchecker`

## Quick Start

```python
import tkinter as tk
import nenotk as ntk

root = tk.Tk()
text = ntk.SpellCheckText(root, wrap="word", width=60, height=20, dictionary_path="custom_dictionary.txt")
text.pack(fill="both", expand=True)

root.mainloop()
```

## API

- Class: `SpellCheckText(master=None, dictionary_path=None, **kwargs)`
  - Inherits all standard `tk.Text` options
- Methods
  - `add_context_menu_item(label, command)`
  - `set_spellcheck_enabled(enabled=None) -> bool`  (toggle when `None`)
  - `refresh_dictionary()`  (reload custom dictionary from file)
  - `add_to_dictionary(word, start, end)`

## Notes

- Misspellings are tagged as `"misspelled"` (style: red underline by default).
- When a dictionary path is provided, the file is created if missing and changes persist across runs.
