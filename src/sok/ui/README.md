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
│   ├── file_row.py      # Row of a media list (before/after, tags, gauge)
│   ├── inputs.py        # Input elements and Drop Zones
│   ├── layouts.py       # Custom layouts (FlowLayout)
│   ├── media_visual.py  # Dominant color, stand-in for a missing poster
│   ├── search.py        # Widgets dedicated to search results
│   ├── nav.py           # Navigation (media types as words, icons)
│   ├── scene.py         # Scene: the selected item shown large, lit
│   └── window.py        # Window controls (Custom title bar)
├── pages/               # Main application pages
│   ├── home_page.py     # Dashboard
│   ├── organize_page.py # Generic organization page
│   └── settings_page.py # Settings page
├── workers/             # Asynchronous tasks (QThreads)
├── i18n.py              # Translation system
├── main_window.py       # Main window (Container)
├── theme.py             # Palettes (dark and light) and theme helpers
└── tokens.py            # Colors of the art direction (generated)
```

## Development Principles

1. **Logic Separation**: Heavy operations (API, files) should be performed
in `workers`.
2. **Translations**: All displayed texts must go through the `tr()` function
from the `i18n` module.
3. **Theming**: Use the palettes defined in `theme.py`, never a hard-coded
color. Their colors come from `tokens.py`, generated from the `tokens.json` of
the SOKTeam art direction by `scripts/make_theme_tokens.py`: never edit it by
hand. The interface supports a dynamic dark mode.
4. **Modularity**: Prefer creating new components in `components/` rather than
overloading page files.

## Graphic Style

S.O.K uses a custom frameless interface following the SOKTeam art direction:
dark by default, with the S.O.K coral as the only accent. The fonts are Geist
for the interface and Geist Mono for data (paths, file names, years, figures),
bundled in `resources/fonts/` and loaded on every system. `theme.ui_font()`
gives an exact size and weight (stylesheets round 650 down to 600). Rendering is managed through a mix of
**QSS** (Qt Style Sheets) and custom drawing in `paintEvent`.
