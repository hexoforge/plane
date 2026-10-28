# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest

from plane.utils.github_app.refs import extract_refs


@pytest.mark.unit
class TestExtractRefs:
    def test_matches_known_identifier_case_insensitively(self):
        refs = extract_refs("Fixes eng-123 and relates to web-7", ["ENG", "WEB"])
        assert refs["work_items"] == {("ENG", 123), ("WEB", 7)}

    def test_ignores_identifier_not_in_project_list(self):
        refs = extract_refs("See OTHER-9 for context", ["ENG"])
        assert refs["work_items"] == set()

    def test_extracts_issue_numbers_from_closing_keywords(self):
        refs = extract_refs("Fixes #12, closes #3 and resolves #99", [])
        assert refs["issue_numbers"] == {12, 3, 99}

    def test_plain_hash_reference_without_keyword_is_not_an_issue_number(self):
        refs = extract_refs("See #12 for details", [])
        assert refs["issue_numbers"] == set()

    def test_empty_text_returns_empty_sets(self):
        refs = extract_refs("", ["ENG"])
        assert refs == {"work_items": set(), "issue_numbers": set()}
