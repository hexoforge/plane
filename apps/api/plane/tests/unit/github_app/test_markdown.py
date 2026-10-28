# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest

from plane.utils.github_app.markdown import render_markdown


@pytest.mark.unit
class TestRenderMarkdown:
    def test_empty_body(self):
        assert render_markdown("") == "<p></p>"
        assert render_markdown(None) == "<p></p>"

    def test_paragraphs(self):
        html = render_markdown("first\n\nsecond")
        assert "<p>first</p>" in html
        assert "<p>second</p>" in html

    def test_escapes_html(self):
        html = render_markdown("<script>alert(1)</script>")
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_inline_code(self):
        html = render_markdown("run `plane build` now")
        assert "<code>plane build</code>" in html

    def test_fenced_code_block(self):
        html = render_markdown("```python\nprint('hi')\n```")
        assert "<pre><code>" in html
        assert "print(&#x27;hi&#x27;)" in html or "print('hi')" in html
