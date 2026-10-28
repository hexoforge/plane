# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest

from plane.utils.github_app.refs import extract_closing_refs, extract_refs


@pytest.mark.unit
class TestExtractRefs:
    def test_matches_known_identifier(self):
        assert extract_refs("fix PROJ-123 please", ["PROJ"]) == [("PROJ", 123)]

    def test_case_insensitive_identifier(self):
        assert extract_refs("fix proj-123 please", ["PROJ"]) == [("PROJ", 123)]

    def test_ignores_unknown_identifier(self):
        assert extract_refs("see OTHER-5", ["PROJ"]) == []

    def test_dedupes_repeated_refs(self):
        assert extract_refs("PROJ-123 and PROJ-123 again", ["PROJ"]) == [("PROJ", 123)]

    def test_multiple_refs(self):
        assert extract_refs("PROJ-1 then PROJ-2", ["PROJ"]) == [("PROJ", 1), ("PROJ", 2)]

    def test_empty_text(self):
        assert extract_refs("", ["PROJ"]) == []
        assert extract_refs(None, ["PROJ"]) == []


@pytest.mark.unit
class TestExtractClosingRefs:
    def test_closes_keyword(self):
        assert extract_closing_refs("this closes #12") == [12]

    def test_fixes_and_resolves(self):
        assert extract_closing_refs("Fixes #1, resolves #2") == [1, 2]

    def test_no_keyword_no_match(self):
        assert extract_closing_refs("see #12 for context") == []

    def test_empty_text(self):
        assert extract_closing_refs("") == []
