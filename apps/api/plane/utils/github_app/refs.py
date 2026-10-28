# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import re

WORK_ITEM_PATTERN = re.compile(r"\b([A-Z][A-Z0-9]{0,11})-(\d+)\b", re.IGNORECASE)
ISSUE_NUMBER_PATTERN = re.compile(r"\b(?:fixes|closes|resolves)\s+#(\d+)\b", re.IGNORECASE)


def extract_refs(text: str, identifiers: list[str]) -> dict:
    """Extract Plane work item refs (IDENT-123) and `fixes #N` style GitHub issue refs.

    `identifiers` are the project identifiers linked to the repo; a work item ref only
    counts if its identifier matches one of them (case insensitive).
    """
    work_items = set()
    issue_numbers = set()

    if not text:
        return {"work_items": work_items, "issue_numbers": issue_numbers}

    identifier_set = {identifier.upper() for identifier in identifiers}
    for match in WORK_ITEM_PATTERN.finditer(text):
        identifier = match.group(1).upper()
        if identifier in identifier_set:
            work_items.add((identifier, int(match.group(2))))

    for match in ISSUE_NUMBER_PATTERN.finditer(text):
        issue_numbers.add(int(match.group(1)))

    return {"work_items": work_items, "issue_numbers": issue_numbers}
