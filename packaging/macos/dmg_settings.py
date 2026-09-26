# ===----------------------------------------------------------------------=== #
#
# This source file is part of the S.O.K open source project
#
# Copyright (c) 2026 S.O.K Team
# Licensed under the MIT License
#
# See LICENSE for license information
#
# ===----------------------------------------------------------------------=== #
"""dmgbuild settings for the S.O.K disk image.

Used by scripts/build_sok.py, which passes the app bundle and background
paths in ``defines``. Positions match scripts/make_macos_assets.py, which
draws the background.
"""

import os.path

app = defines["app"]  # noqa: F821
app_name = os.path.basename(app)

# Volume
format = "UDZO"
files = [app]
symlinks = {"Applications": "/Applications"}
icon = os.path.join(app, "Contents", "Resources", "logo.icns")

# Window
background = defines["background"]  # noqa: F821
# The window height includes the title bar, above the 660x420 background.
window_rect = ((200, 120), (660, 452))
default_view = "icon-view"
show_status_bar = False
show_tab_view = False
show_toolbar = False
show_pathbar = False
show_sidebar = False

# Icons
icon_size = 128
text_size = 13
icon_locations = {
    app_name: (180, 215),
    "Applications": (480, 215),
}
