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
"""Security utilities for application protection.

Provides functions for detecting debugging, protecting against
reverse engineering, and other security measures.
"""

import ctypes
import logging
import sys

logger = logging.getLogger(__name__)


def check_security():
    """Detects if the application is under surveillance (Debugger)."""
    if sys.platform == "win32":
        if ctypes.windll.kernel32.IsDebuggerPresent():
            logger.critical("Security violation detected: debugger attached")
            sys.exit(1)
