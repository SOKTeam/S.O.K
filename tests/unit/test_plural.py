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
import pytest

from sok.ui.i18n import plural_form


@pytest.mark.parametrize(
    "language, n, form",
    [
        ("en", 1, "one"),
        ("en", 0, "other"),
        ("fr", 0, "one"),
        ("fr", 1, "one"),
        ("fr", 2, "other"),
        ("pl", 1, "one"),
        ("pl", 3, "few"),
        ("pl", 12, "many"),
        ("pl", 22, "few"),
        ("pl", 21, "many"),
        ("ru", 21, "one"),
        ("ru", 11, "many"),
        ("ru", 24, "few"),
        ("ru", 5, "many"),
        ("de", 2, "other"),
    ],
)
def test_plural_forms(language, n, form):
    assert plural_form(language, n) == form
