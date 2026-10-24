# Contributing

Thanks for taking a look at ColourTodo.

## Reporting a bug

Please include:

- Windows version (for example Windows 11 23H2)
- what you did, what you expected, and what happened
- the contents of `app.log` from the data directory
- a screenshot if it is a visual issue

Do not attach `todos.json` unless you are comfortable sharing its contents.

## Development

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

- Core model/service code must not import Tkinter.
- Keep appearance in `colour_todo/ui/theme.py`; keep behaviour and paths in `colour_todo/config.py`.
- Geometry uses the FP64 alias/helpers in `colour_todo/fp64.py`.
- Do not commit user data, `.venv`, `dist/`, build output, or logs.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

`test_core.py` runs in GitHub Actions. `test_ui.py` creates real Tk windows and is intended for an interactive Windows desktop.

## Pull requests

- Keep changes focused and explain the user-facing behaviour.
- Add or update tests for model/service changes.
- Update `README.md` and `pre_architecture.md` if behaviour or architecture changes.
- By contributing you agree that your changes are licensed under the MIT License.
