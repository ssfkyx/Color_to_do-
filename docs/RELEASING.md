# Releasing

This project is distributed as a **portable onedir ZIP**. The `.exe` must stay next to `_internal`.

## 1. Bump the version

Update:

- `colour_todo/__init__.py` → `__version__ = "0.1.0"`
- the footer in `colour_todo/ui/todo_panel.py` if the visible version should change

## 2. Run the tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

All 32 tests should pass on an interactive Windows desktop.

## 3. Build

```powershell
.\tools\build_exe.ps1
```

Outputs:

```text
dist\ColourTodo\ColourTodo.exe
dist\ColourTodo-win64.zip
```

Smoke test the folder version: launch it, add a todo, drag it to the timeline, right-click the event, and close/exit.

## 4. Record a checksum (optional)

```powershell
Get-FileHash dist\ColourTodo-win64.zip -Algorithm SHA256
```

Paste the hash into the release notes.

## 5. Tag and publish

```powershell
git add .
git commit -m "Release v0.1.0"
git tag -a v0.1.0 -m "ColourTodo v0.1.0"
git push origin main --tags
```

Using GitHub CLI:

```powershell
gh release create v0.1.0 "dist\ColourTodo-win64.zip" `
  --title "ColourTodo v0.1.0" `
  --notes "First public release. Windows 10/11, portable ZIP."
```

Or create the release in the GitHub web UI and attach `dist\ColourTodo-win64.zip`.

## 6. Checklist

- [ ] `README.md` links and screenshots render correctly
- [ ] `LICENSE` copyright holder is correct
- [ ] no `todos.json`, `app.log`, `.venv`, `dist/`, or build output is tracked
- [ ] `ColourTodo.exe` and `_internal` are in the same ZIP folder
- [ ] the ZIP opens and runs on a clean Windows machine
- [ ] release notes list the Windows requirement and the portable ZIP
- [ ] repository description and topics are set on GitHub

## Repository metadata

Suggested description:

> A local-first Windows todo app with a 24-hour calendar, drag scheduling, and tray reminders.

Suggested topics:

```text
todo, task-manager, calendar, tkinter, python, windows, desktop-app, productivity, local-first
```
