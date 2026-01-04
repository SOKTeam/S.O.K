# UI Designer Files

## .ui Files for Qt Designer

This folder contains `.ui` files that can be edited with Qt Designer.

## Available Files

- `mainwindow.ui` - Main window
- `mainwindow2.ui` - Main window v2
- `ui_mainwindow.ui` - Generated UI for main window

## Editing

To edit these files:

```bash
pyside6-designer ui/designer/mainwindow.ui
```

## Conversion

After modification, convert to Python:

```bash
python build_ui.py
```

Generated files will be placed in `ui/generated/`
