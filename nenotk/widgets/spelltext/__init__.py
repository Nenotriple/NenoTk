"""
# Purpose
Provides a custom Tkinter Text widget (`SpellCheckText`) with integrated spell checking,
custom dictionary support, and a right-click context menu for editing and suggestions.

## API
- Class: `SpellCheckText(master=None, dictionary_path=None, **kwargs) -> SpellCheckText`
    - `master`: Tkinter parent widget
    - `dictionary_path`: Optional path to a custom dictionary file (words are persisted)
    - `**kwargs`: Standard tk.Text options (e.g., wrap, width, height, undo, ...)

- SpellCheckText.add_context_menu_item(label, command)
    - `label`: str, menu item text
    - `command`: callable, function to execute on selection

- SpellCheckText.set_spellcheck_enabled(enabled=None) -> bool
    - `enabled`: bool or None (toggles if None)

- SpellCheckText.refresh_dictionary()
    - Reloads custom dictionary from file

- SpellCheckText.add_to_dictionary(word, start, end)
    - Adds a word to the custom dictionary and removes highlight

## Example
```
import tkinter as tk
from nenotk.widgets.spelltext import SpellCheckText
root = tk.Tk()
spell_text = SpellCheckText(root, wrap="word", width=60, height=20, dictionary_path="custom_dictionary.txt")
spell_text.pack(expand=True, fill="both")
root.mainloop()
```
"""

#region Imports


# Standard
import re
import os
import threading

# tkinter
import tkinter as tk
from tkinter import Menu

# Third-Party
from spellchecker import SpellChecker


#endregion
#region Class Definition


class SpellCheckText(tk.Text):
    def __init__(self, master=None, dictionary_path=None, **kwargs):
        kwargs.setdefault('undo', True)
        super().__init__(master, **kwargs)
        # Create a SpellChecker instance (using default language)
        self.spell = SpellChecker()
        # Track if spellcheck is enabled (default: True)
        self.spellcheck_enabled = True
        # Variable to track spellcheck state for the checkbutton
        self.spellcheck_var = tk.BooleanVar(value=True)
        # Load custom dictionary if provided
        self.dictionary_path = dictionary_path
        # List to track custom words added to dictionary
        self.custom_words = []
        # Track modified lines since last lint
        self.modified_lines = set()
        # Track if a full document lint is needed
        self.full_lint_needed = True
        # Track the currently edited word
        self.current_word_info = {"word": None, "start": None, "end": None}
        # Track last cursor position
        self.last_cursor_pos = None

        if self.dictionary_path:
            # Ensure the directory exists if needed
            dir_path = os.path.dirname(self.dictionary_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            # Load existing dictionary or create a new one
            if os.path.exists(self.dictionary_path):
                self.refresh_dictionary()
            else:
                # Create an empty file
                with open(self.dictionary_path, 'w') as f:
                    pass
        # Configure a tag to highlight misspelled words (red underline)
        self.tag_configure("misspelled", underline=True, underlinefg="red")
        # Timer for delayed spell checking
        self.lint_timer = None
        self.lint_delay = 500  # milliseconds
        # Replace KeyRelease binding with more specific handlers
        self.bind("<KeyRelease>", self._on_key_release)
        # Add bindings for cursor movement
        self.bind("<ButtonRelease-1>", self._on_cursor_moved)  # Mouse click
        self.bind("<KeyRelease-Left>", self._on_cursor_moved)
        self.bind("<KeyRelease-Right>", self._on_cursor_moved)
        self.bind("<KeyRelease-Up>", self._on_cursor_moved)
        self.bind("<KeyRelease-Down>", self._on_cursor_moved)
        # Add bindings for paste operations and text modifications
        self.bind("<<Paste>>", self._on_paste)
        self.bind("<<Cut>>", self._on_content_modified)
        self.bind("<<Modified>>", self._on_content_modified)
        # Right-click context menu setup
        self.bind("<Button-3>", self.show_context_menu)
        # Store the current right-click position
        self.right_click_pos = None
        # Custom context menu items dictionary: {label: callback_function}
        self.custom_menu_items = {}
        # Store the original cursor to restore after context menu
        self.current_cursor = self.cget("cursor")


#endregion
#region Spell check Logic


    def _on_key_release(self, event=None):
        """Handle key release events to track the current word and schedule linting."""
        # Update the current word being edited
        word, start, end = self._get_word_at_position(tk.INSERT)
        self.current_word_info = {"word": word, "start": start, "end": end}
        # Track the modified line
        if event:
            current_index = self.index(tk.INSERT)
            line = int(current_index.split('.')[0])
            self.modified_lines.add(line)
        # Cancel any existing timer to reset the delay
        if self.lint_timer:
            self.after_cancel(self.lint_timer)
        # Schedule linting after the delay
        self.lint_timer = self.after(self.lint_delay, self._lint)


    def _on_cursor_moved(self, event=None):
        """Check if cursor has moved away from a word and lint that word."""
        new_pos = self.index(tk.INSERT)
        # If we have a last position and it's different, check if we've moved from a word
        if self.last_cursor_pos and new_pos != self.last_cursor_pos:
            word, start, end = self._get_word_at_position(new_pos)
            # If we've moved to a different word, lint the previous one
            if self.current_word_info["word"] and (
                word != self.current_word_info["word"] or
                start != self.current_word_info["start"]
            ):
                # Get line of previous word and schedule it for linting
                if self.current_word_info["start"]:
                    line = int(self.index(self.current_word_info["start"]).split('.')[0])
                    self.modified_lines.add(line)
                    # Clear current word info before linting
                    prev_word_info = self.current_word_info.copy()
                    self.current_word_info = {"word": word, "start": start, "end": end}
                    # Immediate lint for the previous word
                    self._lint()
            # Update current word info
            self.current_word_info = {"word": word, "start": start, "end": end}
        # Update last cursor position
        self.last_cursor_pos = new_pos


    def _schedule_lint(self, event=None):
        """Schedule a spell check after a delay to avoid checking while typing."""
        # Cancel any existing timer to reset the delay
        if self.lint_timer:
            self.after_cancel(self.lint_timer)
        # Track the modified line
        if event:
            # Get the current line index
            current_index = self.index(tk.INSERT)
            line = int(current_index.split('.')[0])
            self.modified_lines.add(line)
        # Schedule linting after the delay
        self.lint_timer = self.after(self.lint_delay, self._lint)


    def _lint(self):
        # Only proceed if spellcheck is enabled
        if not self.spellcheck_enabled:
            return
        # Get the current word being edited to exclude from linting
        current_word = self.current_word_info["word"]
        current_word_start = self.current_word_info["start"]
        current_word_end = self.current_word_info["end"]
        if self.full_lint_needed:
            # Perform full document lint if needed
            self.tag_remove("misspelled", "1.0", tk.END)
            text = self.get("1.0", tk.END)
            matches = list(re.finditer(r'\b\w+\b', text))
            if matches:
                word_list = [match.group() for match in matches]
                misspelled = self.spell.unknown(word.lower() for word in word_list)
                for match in matches:
                    word = match.group()
                    if word.lower() in misspelled:
                        start_index = f"1.0+{match.start()}c"
                        end_index = f"1.0+{match.end()}c"
                        # Skip the current word being edited
                        if current_word and start_index == current_word_start and end_index == current_word_end:
                            continue
                        self.tag_add("misspelled", start_index, end_index)
            self.full_lint_needed = False
        elif self.modified_lines:
            # Only check modified lines
            for line in self.modified_lines:
                # Remove misspelled tags from this line
                line_start = f"{line}.0"
                line_end = f"{line}.end"
                self.tag_remove("misspelled", line_start, line_end)
                # Get text of just this line
                line_text = self.get(line_start, line_end)
                # Find all words in this line
                matches = list(re.finditer(r'\b\w+\b', line_text))
                if matches:
                    word_list = [match.group() for match in matches]
                    misspelled = self.spell.unknown(word.lower() for word in word_list)
                    # Tag misspelled words
                    for match in matches:
                        word = match.group()
                        if word.lower() in misspelled:
                            start_index = f"{line}.{match.start()}"
                            end_index = f"{line}.{match.end()}"
                            # Skip the current word being edited
                            if current_word and start_index == current_word_start and end_index == current_word_end:
                                continue
                            self.tag_add("misspelled", start_index, end_index)
            # Clear the modified lines tracking after processing
            self.modified_lines.clear()


    def refresh_dictionary(self):
        """
        Read the dictionary file and update the spellchecker's word frequency.
        This allows tracking of words that might have been removed from the file by the user.
        """
        if not self.dictionary_path or not os.path.exists(self.dictionary_path):
            return
        # Read words from the dictionary file
        with open(self.dictionary_path, 'r') as f:
            self.custom_words = [line.strip() for line in f if line.strip()]
        # Reset the spellchecker to ensure a clean state
        self.spell = SpellChecker()
        # Add all words from the custom dictionary
        for word in self.custom_words:
            self.spell.word_frequency.add(word.lower())
        # Force a full lint after dictionary refresh
        self.full_lint_needed = True
        self._lint()


    def add_to_dictionary(self, word, start, end):
        """Add the word to the spellchecker dictionary and custom dictionary file."""
        if word:
            word = word.lower()
            self.spell.word_frequency.add(word)
            self.tag_remove("misspelled", start, end)  # Remove the misspelled tag
            # If a custom dictionary file is specified, append the word to it
            if self.dictionary_path:
                # Only add if not already in custom_words list
                if word not in self.custom_words:
                    self.custom_words.append(word)
                    with open(self.dictionary_path, 'a') as f:
                        f.write(word + '\n')
            # A full lint is needed because the same word might be elsewhere in the document
            self.full_lint_needed = True
            self._lint()


    def set_spellcheck_enabled(self, enabled=None):
        """
        Enable or disable the spell checking functionality.

        Args:
            enabled (bool, optional): If True, enable spellcheck. If False, disable it. If None, toggle the current state.

        Returns:
            bool: The new state of the spell checker (True=enabled, False=disabled)
        """
        # Toggle if no specific state provided
        if enabled is None:
            enabled = not self.spellcheck_enabled
        # Update the state
        self.spellcheck_enabled = enabled
        # Update the checkbutton variable to match the current state
        self.spellcheck_var.set(enabled)
        if enabled:
            # Re-check spelling if enabling - need to do a full lint
            self.full_lint_needed = True
            self._lint()
        else:
            # Remove all highlighting if disabling
            self.tag_remove("misspelled", "1.0", tk.END)
            # Cancel any pending lint timer
            if self.lint_timer:
                self.after_cancel(self.lint_timer)
                self.lint_timer = None
            # Clear any tracked modified lines
            self.modified_lines.clear()
        return self.spellcheck_enabled


#endregion
#region Word Process logic


    def _get_word_at_position(self, index):
        """Get the word at the given position in the text."""
        # Get the line and column of the index
        line, col = map(int, self.index(index).split('.'))
        # Get the text of the line
        line_text = self.get(f"{line}.0", f"{line}.end")
        # Find all words in the line
        for match in re.finditer(r'\b\w+\b', line_text):
            start, end = match.span()
            # Check if the column is within this word
            if start <= col <= end:
                word = match.group()
                word_start = f"{line}.{start}"
                word_end = f"{line}.{end}"
                return word, word_start, word_end
        return None, None, None


    def _replace_word(self, suggestion, start, end):
        """Replace the misspelled word with the selected suggestion."""
        self.delete(start, end)
        self.insert(start, suggestion)
        # Mark line as modified to ensure it gets checked
        line = int(self.index(start).split('.')[0])
        self.modified_lines.add(line)
        self._lint()  # Re-check spelling after replacement


#endregion
#region Context Menu logic

    def _can_redo(self):
        """Safely check if there's anything to redo."""
        try:
            return self.edit_redo()
        except tk.TclError:
            return False


    def _can_undo(self):
        """Safely check if there's anything to undo."""
        try:
            return self.edit_modified()
        except tk.TclError:
            return False


    def _populate_misspelled_suggestions(self, context_menu, word, start, end):
        """
        Populate the context menu with spelling suggestions for misspelled words.

        Args:
            context_menu (Menu): The context menu to populate
            word (str): The word to check
            start (str): The starting position of the word
            end (str): The ending position of the word

        Returns:
            bool: True if suggestions were added, False otherwise
        """
        # Check if spell check is enabled and the word is misspelled
        if not (self.spellcheck_enabled and word and self.tag_ranges("misspelled") and
                self.tag_nextrange("misspelled", start, end)):
            return False
        # Change cursor to watch to indicate processing
        self.config(cursor="watch")
        # Use threading to get suggestions with a timeout
        suggestions = []
        suggestion_ready = threading.Event()
        def get_suggestions():
            nonlocal suggestions
            try:
                # Handle potential None return from candidates() method
                candidates = self.spell.candidates(word.lower())
                suggestions = list(candidates or [])[:6]  # Convert to list, use empty list if None
            except Exception:
                suggestions = []  # Handle any other exceptions by using an empty list
            suggestion_ready.set()
        # Start the suggestion thread
        suggestion_thread = threading.Thread(target=get_suggestions)
        suggestion_thread.daemon = True  # Don't let this thread prevent program exit
        suggestion_thread.start()
        # Wait for the thread to complete or timeout after 300ms
        suggestion_ready.wait(timeout=0.3)
        if suggestions:
            for suggestion in suggestions:
                context_menu.add_command(label=suggestion, command=lambda s=suggestion, st=start, en=end: self._replace_word(s, st, en))
        else:
            context_menu.add_command(label="No suggestions", state="disabled")
        # Add option to add word to dictionary
        context_menu.add_command(label="Add to dictionary", command=lambda: self.add_to_dictionary(word, start, end))
        return True  # Indicate items were added


    def show_context_menu(self, event):
        """Show context menu with standard options and spelling suggestions if applicable."""
        # Save the right-click position
        self.right_click_pos = f"@{event.x},{event.y}"
        # Create a new context menu
        context_menu = Menu(self, tearoff=0)
        # Get the word at the click position
        word, start, end = self._get_word_at_position(self.right_click_pos)
        # Add spell check options if applicable
        added_spell_items = self._populate_misspelled_suggestions(context_menu, word, start, end)
        # Add separator if spell items were added
        if added_spell_items:
            context_menu.add_separator()
        # Add standard text editing options
        has_selection = bool(self.tag_ranges(tk.SEL))
        context_menu.add_command(label="Undo", command=lambda: self.event_generate("<<Undo>>"), state=tk.NORMAL if self._can_undo() else tk.DISABLED)
        context_menu.add_command(label="Redo", command=lambda: self.event_generate("<<Redo>>"), state=tk.NORMAL if self._can_redo() else tk.DISABLED)
        context_menu.add_separator()
        context_menu.add_command(label="Cut", command=lambda: self.event_generate("<<Cut>>"), state=tk.NORMAL if has_selection else tk.DISABLED)
        context_menu.add_command(label="Copy", command=lambda: self.event_generate("<<Copy>>"), state=tk.NORMAL if has_selection else tk.DISABLED)
        context_menu.add_command(label="Paste", command=lambda: self.event_generate("<<Paste>>"))
        context_menu.add_command(label="Delete", command=lambda: self.delete(start, end) if word else None, state=tk.NORMAL if word else tk.DISABLED)
        context_menu.add_separator()
        context_menu.add_command(label="Select All", command=lambda: self.select_all())
        context_menu.add_command(label="Clear All", command=lambda: self.delete("1.0", tk.END))
        # Add custom menu items if any
        if self.custom_menu_items:
            context_menu.add_separator()
            for label, command in self.custom_menu_items.items():
                context_menu.add_command(label=label, command=command)
        # Add Spellcheck Options submenu
        context_menu.add_separator()
        spellcheck_submenu = Menu(context_menu, tearoff=0)
        spellcheck_submenu.add_command(label="Open Dictionary", command=lambda: os.startfile(self.dictionary_path) if self.dictionary_path else None, state=tk.NORMAL if self.dictionary_path else tk.DISABLED)
        spellcheck_submenu.add_command(label="Refresh Dictionary", command=self.refresh_dictionary, state=tk.NORMAL if self.dictionary_path else tk.DISABLED)
        spellcheck_submenu.add_separator()
        spellcheck_submenu.add_command(label="Re-Check All Words", command=self._schedule_lint)
        spellcheck_submenu.add_checkbutton(label="Toggle Spell Check", variable=self.spellcheck_var, command=lambda: self.set_spellcheck_enabled(self.spellcheck_var.get()))
        context_menu.add_cascade(label="Spellcheck Options", menu=spellcheck_submenu)
        # Show the context menu
        self.config(cursor=self.current_cursor)
        context_menu.tk_popup(event.x_root, event.y_root)
        return "break"  # Prevent the default context menu


    def select_all(self):
        """Select all text in the widget."""
        self.tag_add(tk.SEL, "1.0", tk.END)
        self.mark_set(tk.INSERT, tk.END)
        self.see(tk.INSERT)
        return "break"


    def add_context_menu_item(self, label, command):
        """
        Add a custom item to the context menu.

        Args:
            label (str): The text to display in the menu item
            command (callable): The function to call when the item is selected
        """
        # For "Clear All" item, wrap the command to ensure full lint is performed on next paste
        if label == "Clear All":
            original_command = command
            def wrapped_command():
                original_command()
                self.full_lint_needed = True
            self.custom_menu_items[label] = wrapped_command
        else:
            self.custom_menu_items[label] = command


#endregion
#region Event Handlers


    def _on_paste(self, event=None):
        """Handle paste operations by triggering a full lint."""
        self.full_lint_needed = True
        self._schedule_lint()
        return


    def _on_content_modified(self, event=None):
        """Handle cut or other content modifications."""
        self.full_lint_needed = True
        self._schedule_lint()
        return


#endregion
#region Test/Example

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Spell Check Text Widget")
    # Create a dictionary file path
    custom_dict_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "custom_dictionary.txt")
    # Create an instance of our custom widget with custom dictionary
    spell_text = SpellCheckText(root, wrap="word", width=60, height=20, dictionary_path=custom_dict_path)
    spell_text.pack(expand=True, fill="both", padx=10, pady=10)
    # Example of adding custom context menu items
    #spell_text.add_context_menu_item("Clear All", lambda: spell_text.delete("1.0", tk.END))
    root.mainloop()
