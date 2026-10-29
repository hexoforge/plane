# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest

from plane.utils.github_app.markdown import html_to_markdown, render_markdown


@pytest.mark.unit
class TestRenderMarkdownConstructs:
    def test_heading(self):
        assert "<h3>Heading</h3>" in render_markdown("### Heading")

    def test_bold_and_italic(self):
        html = render_markdown("**bold** and _it_")
        assert "<strong>bold</strong>" in html
        assert "<em>it</em>" in html

    def test_strikethrough(self):
        assert "<s>gone</s>" in render_markdown("~~gone~~")

    def test_bullet_list(self):
        html = render_markdown("- a\n- b")
        assert "<ul><li>a</li><li>b</li></ul>" in html

    def test_ordered_list(self):
        html = render_markdown("1. one\n2. two")
        assert "<ol><li>one</li><li>two</li></ol>" in html

    def test_link(self):
        html = render_markdown("[plane](https://plane.so)")
        assert 'href="https://plane.so"' in html
        assert ">plane</a>" in html

    def test_blockquote(self):
        assert "<blockquote><p>quote</p></blockquote>" in render_markdown("> quote")

    def test_fenced_code_with_language(self):
        html = render_markdown("```python\nprint('hi')\n```")
        assert '<pre><code class="language-python">' in html
        assert "print('hi')" in html

    def test_fenced_code_without_language(self):
        html = render_markdown("```\nraw\n```")
        assert "<pre><code>raw" in html

    def test_inline_code(self):
        assert "<code>plane build</code>" in render_markdown("run `plane build` now")

    def test_table(self):
        html = render_markdown("| a | b |\n|---|---|\n| 1 | 2 |")
        assert "<table>" in html
        assert "<thead><tr><th>a</th><th>b</th></tr></thead>" in html
        assert "<tbody><tr><td>1</td><td>2</td></tr></tbody>" in html

    def test_task_list_checked_and_unchecked(self):
        html = render_markdown("- [ ] todo\n- [x] done")
        assert '<ul data-type="taskList">' in html
        assert 'data-type="taskItem" data-checked="false"' in html
        assert 'data-type="taskItem" data-checked="true"' in html
        assert 'type="checkbox" checked' in html
        assert '<input type="checkbox">' in html

    def test_image(self):
        html = render_markdown("![alt text](http://example.com/y.png)")
        assert '<img src="http://example.com/y.png" alt="alt text">' in html

    def test_details_summary_passthrough(self):
        html = render_markdown("<details><summary>More</summary>hidden text</details>")
        assert "<details>" in html
        assert "<summary>More</summary>" in html
        assert "hidden text" in html

    def test_mentions_and_refs_kept_as_text(self):
        html = render_markdown("cc @octocat see #42")
        assert "@octocat" in html
        assert "#42" in html
        assert "<a" not in html


@pytest.mark.unit
class TestRenderMarkdownEdgeCases:
    def test_empty_and_none_body(self):
        assert render_markdown("") == "<p></p>"
        assert render_markdown(None) == "<p></p>"

    def test_whitespace_only_body(self):
        assert render_markdown("   \n\n\t  ") == "<p></p>"

    def test_very_large_body(self):
        html = render_markdown("word " * 50000)
        assert html.startswith("<p>")
        assert "word" in html

    def test_html_comments_from_issue_templates_are_stripped(self):
        html = render_markdown("<!-- please fill this out -->\n\nActual content")
        assert "please fill this out" not in html
        assert "Actual content" in html

    def test_raw_script_is_neutralised(self):
        html = render_markdown("<script>alert(1)</script>")
        assert "<script" not in html
        assert "alert(1)" not in html

    def test_onclick_and_javascript_links_are_stripped(self):
        html = render_markdown('<a href="javascript:alert(1)" onclick="steal()">click</a>')
        assert "javascript:" not in html
        assert "onclick" not in html

    def test_crlf_line_endings(self):
        html = render_markdown("first\r\n\r\nsecond")
        assert "<p>first</p>" in html
        assert "<p>second</p>" in html

    def test_code_block_markdown_not_rendered(self):
        html = render_markdown("```\n**not bold**\n```")
        assert "<strong>" not in html
        assert "**not bold**" in html

    def test_mixed_task_and_plain_list_falls_back_to_readable_list(self):
        html = render_markdown("- [ ] todo\n- plain")
        assert "taskList" not in html
        assert "<ul>" in html
        assert "todo" in html
        assert "plain" in html


@pytest.mark.unit
class TestHtmlToMarkdown:
    def test_empty(self):
        assert html_to_markdown("") == ""
        assert html_to_markdown(None) == ""
        assert html_to_markdown("<p></p>") == ""

    def test_headings_and_emphasis(self):
        md = html_to_markdown("<h3>Heading</h3><p><strong>bold</strong> and <em>it</em></p>")
        assert "### Heading" in md
        assert "**bold**" in md
        assert "*it*" in md

    def test_list(self):
        md = html_to_markdown("<ul><li>a</li><li>b</li></ul>")
        assert "- a" in md
        assert "- b" in md

    def test_code_block_keeps_language(self):
        md = html_to_markdown('<pre><code class="language-python">print(1)</code></pre>')
        assert "```python" in md
        assert "print(1)" in md

    def test_task_list_round_trips_to_gfm_checkboxes(self):
        html = (
            '<ul data-type="taskList">'
            '<li data-type="taskItem" data-checked="true">'
            "<label><input type=\"checkbox\" checked><span></span></label><div><p>done</p></div></li>"
            '<li data-type="taskItem" data-checked="false">'
            "<label><input type=\"checkbox\"><span></span></label><div><p>todo</p></div></li>"
            "</ul>"
        )
        md = html_to_markdown(html)
        assert "- [x] done" in md
        assert "- [ ] todo" in md

    def test_table(self):
        md = html_to_markdown("<table><thead><tr><th>a</th><th>b</th></tr></thead>"
                               "<tbody><tr><td>1</td><td>2</td></tr></tbody></table>")
        assert "| a | b |" in md
        assert "| 1 | 2 |" in md

    def test_sanitizes_script_before_converting(self):
        md = html_to_markdown("<p>hi</p><script>alert(1)</script>")
        assert "script" not in md
        assert "alert(1)" not in md

    def test_image_and_link(self):
        md = html_to_markdown('<p><img src="http://x/y.png" alt="alt text"></p><p><a href="http://example.com">link</a></p>')
        assert "![alt text](http://x/y.png)" in md
        assert "[link](http://example.com)" in md


@pytest.mark.unit
class TestRoundTrip:
    """md -> html -> md should be stable enough that re-rendering an
    already-converted body doesn't keep producing a different result (which
    would otherwise cause an endless inbound/outbound edit ping-pong)."""

    @pytest.mark.parametrize(
        "markdown",
        [
            "### Heading\n\n**bold** and _it_ and ~~gone~~",
            "- a\n- b\n- c",
            "1. one\n2. two",
            "- [ ] todo\n- [x] done",
            "> a quote",
            "```python\nprint('hi')\n```",
            "inline `code` here",
            "| a | b |\n|---|---|\n| 1 | 2 |",
            "[a link](https://example.com)",
        ],
    )
    def test_second_pass_is_stable(self, markdown):
        first_markdown = html_to_markdown(render_markdown(markdown))
        second_markdown = html_to_markdown(render_markdown(first_markdown))
        assert first_markdown == second_markdown

    def test_html_is_stable_across_two_render_passes(self):
        markdown = "### Title\n\n- [ ] a\n- [x] b\n\n| x | y |\n|---|---|\n| 1 | 2 |"
        first_html = render_markdown(markdown)
        second_html = render_markdown(html_to_markdown(first_html))
        assert first_html == second_html
