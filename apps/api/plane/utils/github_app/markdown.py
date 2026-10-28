# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import html
import re

_CODE_BLOCK_PATTERN = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
_INLINE_CODE_PATTERN = re.compile(r"`([^`]+)`")


def render_markdown(text: str | None) -> str:
    """Minimal, safe markdown-to-HTML conversion for GitHub issue/PR bodies.

    shortcut: only paragraphs and code (fenced + inline) are rendered; other
    markdown constructs are left as escaped plain text. No markdown library
    is an installed dependency of this repo today, so this avoids adding one
    for a handful of constructs. Swap in a real renderer if GitHub body
    formatting fidelity becomes a complaint.
    """
    if not text:
        return "<p></p>"

    segments = []
    last_end = 0
    for match in _CODE_BLOCK_PATTERN.finditer(text):
        segments.append(("text", text[last_end : match.start()]))
        segments.append(("code", match.group(1)))
        last_end = match.end()
    segments.append(("text", text[last_end:]))

    html_parts = []
    for kind, content in segments:
        if kind == "code":
            html_parts.append(f"<pre><code>{html.escape(content)}</code></pre>")
            continue

        for paragraph in re.split(r"\n\s*\n", content.strip()):
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            escaped = html.escape(paragraph)
            escaped = _INLINE_CODE_PATTERN.sub(lambda m: f"<code>{m.group(1)}</code>", escaped)
            escaped = escaped.replace("\n", "<br />")
            html_parts.append(f"<p>{escaped}</p>")

    return "".join(html_parts) or "<p></p>"
