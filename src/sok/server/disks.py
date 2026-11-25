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
"""The disks of the folders of S.O.K Server: their size and free room.

The Analysis screen shows them under "Your disks": one line per volume (the
folders on the same disk share it), named after its first folder, with a
gauge of the room used.
"""

import os
import shutil
from typing import Any, Dict, List


def disks(folders: List[str]) -> List[Dict[str, Any]]:
    """One entry per volume of the folders given, in their order: its first
    folder ("path"), all its folders, its total size and free room in bytes.
    A missing or unreadable folder is left out."""
    volumes: Dict[int, Dict[str, Any]] = {}
    for folder in folders:
        try:
            device = os.stat(folder).st_dev
            if device in volumes:
                volumes[device]["folders"].append(folder)
                continue
            total, _used, free = shutil.disk_usage(folder)
        except OSError:
            continue
        volumes[device] = {"path": folder, "folders": [folder], "total": total, "free": free}
    return list(volumes.values())
