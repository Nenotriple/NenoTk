# Simple Dialogs

A collection of dialogs for input, choice, info, progress, and path confirmation.

## Functions

| Function         | Signature                                                                                                                        | Returns                                | Description                                                     |
|------------------|----------------------------------------------------------------------------------------------------------------------------------|---------------------------------------:|-----------------------------------------------------------------|
| `askstring`      | `askstring(title, prompt, initialvalue=None, detail=None, parent=None, icon_image=None)`                                         | `Optional[str]`                        | Prompt for a text string.                                       |
| `askinteger`     | `askinteger(title, prompt, initialvalue=None, minvalue=None, maxvalue=None, detail=None, parent=None, icon_image=None)`          | `Optional[int]`                        | Prompt for an integer with optional bounds.                     |
| `askfloat`       | `askfloat(title, prompt, initialvalue=None, minvalue=None, maxvalue=None, detail=None, parent=None, icon_image=None)`            | `Optional[float]`                      | Prompt for a float with optional bounds.                        |
| `askcombo`       | `askcombo(title, prompt, values, initialvalue=None, detail=None, parent=None, icon_image=None)`                                  | `Optional[str]`                        | Choose from a dropdown list of values.                          |
| `askradio`       | `askradio(title, prompt, values, initialvalue=None, parent=None, icon_image=None)`                                               | `Optional[str]`                        | Choose a single option (radio-style).                           |
| `askyesno`       | `askyesno(title, prompt, detail=None, parent=None, icon_image=None)`                                                             | `bool`                                 | Simple Yes/No confirmation.                                     |
| `askyesnocancel` | `askyesnocancel(title, prompt, detail=None, parent=None, icon_image=None)`                                                       | `Optional[bool]`                       | Yes / No / Cancel tri-state response.                           |
| `showinfo`       | `showinfo(title, prompt, detail=None, parent=None, icon_image=None)`                                                             | `None`                                 | Display an informational dialog.                                |
| `showprogress`   | `showprogress(title, prompt, task_function, args=(), kwargs=None, max_value=100, parent=None, icon_image=None, auto_close=True)` | `Any`                                  | Run a background task with a progress dialog.                   |
| `confirmpath`    | `confirmpath(title, prompt, path, detail=None, parent=None, icon_image=None)`                                                    | `tuple[Optional[bool], Optional[str]]` | Confirm or modify a filesystem path, returns (confirmed, path). |

## Quick Start

```python
import nenotk as ntk

name = ntk.askstring("Name", "Enter name:", initialvalue="Alice")
count = ntk.askinteger("Count", "Enter a number:", initialvalue=5, minvalue=1, maxvalue=10, detail="Between 1 and 10")
confirmed, path = ntk.confirmpath("Confirm Output", "Save to:", "C:/output")
```

## Notes

- If no `parent` is provided, a temporary root is created and destroyed automatically.
- `askradio` accepts either a list of strings or a list of tuples `(value, label[, detail])`.
- `showprogress` runs `task_function` in a background thread; it can be cancelled by raising `InterruptedError` in the task.
