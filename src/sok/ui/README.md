# S.O.K User Interface

This directory contains the entire graphical interface of S.O.K,
built with **PySide6**.

## Folder Architecture

The interface is structured in a modular way to facilitate maintenance and
adding components.

``` bash
ui/
├── components/          # Reusable components (Widgets)
│   ├── integrations/    # Third-party modules (Discord RPC, Updates, OAuth)
│   ├── base.py          # Base elements (Cards, Buttons, Toggles)
│   ├── dialogs.py       # Custom dialog boxes
│   ├── inputs.py        # Input elements and Drop Zones
│   ├── layouts.py       # Custom layouts (FlowLayout)
│   ├── search.py        # Widgets dedicated to search results
│   ├── sidebar.py       # Sidebar navigation components
│   └── window.py        # Window controls (Custom title bar)
├── pages/               # Main application pages
│   ├── home_page.py     # Dashboard
│   ├── organize_page.py # Generic organization page
│   └── settings_page.py # Settings page
├── workers/             # Asynchronous tasks (QThreads)
├── i18n.py              # Translation system
├── main_window.py       # Main window (Container)
└── theme.py             # Style and palette definitions (Orange/Dark mode)
```

## Development Principles

1. **Logic Separation**: Heavy operations (API, files) should be performed
in `workers`.
2. **Translations**: All displayed texts must go through the `tr()` function
from the `i18n` module.
3. **Theming**: Use the palettes defined in `theme.py`.
The interface supports a dynamic dark mode.
4. **Modularity**: Prefer creating new components in `components/` rather than
overloading page files.

## Graphic Style

S.O.K uses a custom frameless interface, inspired by modern macOS design
with a distinctive "Orange" touch. Rendering is managed through a mix of
**QSS** (Qt Style Sheets) and custom drawing in `paintEvent`.
