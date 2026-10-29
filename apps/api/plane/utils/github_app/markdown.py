# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import html as _html

import markdownify
import mistune

from plane.utils.content_validator import validate_html_content

_PARSER = mistune.create_markdown(
    renderer=None, plugins=["table", "task_lists", "strikethrough", "url"]
)


def render_markdown(text: str | None) -> str:
    """Convert GitHub Flavored Markdown to the HTML Plane's TipTap editor accepts.

    Renders GFM constructs (headings, emphasis, lists incl. task lists, tables,
    fenced code with language, images, links, blockquotes) and lets raw HTML
    (e.g. `<details>` blocks from issue templates) pass through. Everything is
    sanitized with the same nh3 allowlist the editor's own save path uses
    (plane.utils.content_validator), which strips scripts, event handlers,
    javascript: links and HTML comments, and keeps data-type/data-checked so
    checklists map to TipTap's taskList node.
    """
    if not text or not text.strip():
        return "<p></p>"

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    tokens = _PARSER(normalized)
    rendered = _render_tokens(tokens)
    _, _, sanitized = validate_html_content(rendered)
    sanitized = (sanitized or "").strip()
    return sanitized or "<p></p>"


class _PlaneMarkdownConverter(markdownify.MarkdownConverter):
    """markdownify customized to round-trip Plane's TipTap HTML back to GFM:
    checkbox inputs become `[ ]`/`[x]` markers and block wrappers used only for
    taskItem/list-item layout (`div`, `p` inside `li`) don't add blank lines."""

    def convert_input(self, el, text, parent_tags):
        if el.get("type") == "checkbox":
            return "[x] " if el.has_attr("checked") else "[ ] "
        return text

    def convert_div(self, el, text, parent_tags):
        return text

    def convert_p(self, el, text, parent_tags):
        if "li" in parent_tags:
            return text.strip()
        return super().convert_p(el, text, parent_tags)


def _code_block_language(el):
    code = el.find("code")
    if not code:
        return ""
    for css_class in code.get("class") or []:
        if css_class.startswith("language-"):
            return css_class[len("language-") :]
    return ""


def html_to_markdown(html_content: str | None) -> str:
    """Convert Plane editor HTML back to GitHub Flavored Markdown for outbound
    comments/bodies. Sanitizes first so raw HTML never reaches GitHub verbatim."""
    if not html_content or not html_content.strip():
        return ""

    _, _, sanitized = validate_html_content(html_content)
    sanitized = (sanitized or "").strip()
    if not sanitized:
        return ""

    converter = _PlaneMarkdownConverter(
        heading_style="ATX", bullets="-", code_language_callback=_code_block_language
    )
    return converter.convert(sanitized).strip()


# -- markdown AST -> HTML -----------------------------------------------------


def _render_tokens(tokens):
    return "".join(_render_token(tok) for tok in tokens or [])


def _render_token(tok):
    handler = _RENDERERS.get(tok.get("type"))
    if handler is None:
        # Unknown construct: flatten to its children's content rather than
        # dropping it, so unsupported nodes still degrade to readable text.
        return _render_tokens(tok.get("children"))
    return handler(tok)


def _plain_text(tok):
    if tok.get("type") == "text":
        return tok.get("raw", "")
    return "".join(_plain_text(child) for child in tok.get("children") or [])


def _escape(text):
    return _html.escape(text or "", quote=True)


def _render_text(tok):
    return _escape(tok.get("raw", ""))


def _render_inline_container(tag):
    def render(tok):
        return f"<{tag}>{_render_tokens(tok.get('children'))}</{tag}>"

    return render


def _render_codespan(tok):
    return f"<code>{_escape(tok.get('raw', ''))}</code>"


def _render_link(tok):
    url = (tok.get("attrs") or {}).get("url") or ""
    title = (tok.get("attrs") or {}).get("title")
    title_attr = f' title="{_escape(title)}"' if title else ""
    inner = _render_tokens(tok.get("children"))
    return f'<a href="{_escape(url)}"{title_attr}>{inner}</a>'


def _render_image(tok):
    url = (tok.get("attrs") or {}).get("url") or ""
    alt = _plain_text(tok)
    return f'<img src="{_escape(url)}" alt="{_escape(alt)}">'


def _render_paragraph(tok):
    inner = _render_tokens(tok.get("children"))
    return f"<p>{inner}</p>"


def _render_heading(tok):
    level = (tok.get("attrs") or {}).get("level", 1)
    inner = _render_tokens(tok.get("children"))
    return f"<h{level}>{inner}</h{level}>"


def _render_block_quote(tok):
    return f"<blockquote>{_render_tokens(tok.get('children'))}</blockquote>"


def _render_block_code(tok):
    info = ((tok.get("attrs") or {}).get("info") or "").strip()
    language = info.split()[0] if info else ""
    class_attr = f' class="language-{_escape(language)}"' if language else ""
    # mistune's raw always carries one trailing newline before the closing
    # fence; keeping it would make markdownify add another on every outbound
    # conversion, growing the code block by a blank line on each round trip.
    code = (tok.get("raw") or "").removesuffix("\n")
    return f"<pre><code{class_attr}>{_escape(code)}</code></pre>"


def _render_raw_html(tok):
    # Already-sanitized at the end of render_markdown(); passed through so
    # constructs like <details>/<summary> from issue templates survive.
    return tok.get("raw", "")


def _render_block_text(tok):
    return _render_tokens(tok.get("children"))


def _render_list_item(tok):
    return f"<li>{_render_tokens(tok.get('children'))}</li>"


def _render_task_item(tok, *, standalone):
    checked = bool((tok.get("attrs") or {}).get("checked"))
    checkbox = f'<input type="checkbox"{" checked" if checked else ""}>'
    inner = _render_tokens(tok.get("children"))
    if not standalone:
        return f"<li><label>{checkbox}<span></span></label>{inner}</li>"
    content = inner if inner.startswith("<p>") else f"<p>{inner}</p>"
    checked_attr = "true" if checked else "false"
    return (
        f'<li data-type="taskItem" data-checked="{checked_attr}">'
        f"<label>{checkbox}<span></span></label><div>{content}</div></li>"
    )


def _render_list(tok):
    children = tok.get("children") or []
    ordered = (tok.get("attrs") or {}).get("ordered", False)
    tag = "ol" if ordered else "ul"
    is_task_list = bool(children) and all(child.get("type") == "task_list_item" for child in children)

    if is_task_list:
        items = "".join(_render_task_item(child, standalone=True) for child in children)
        return f'<ul data-type="taskList">{items}</ul>'

    items = []
    for child in children:
        if child.get("type") == "task_list_item":
            items.append(_render_task_item(child, standalone=False))
        else:
            items.append(_render_token(child))
    return f"<{tag}>{''.join(items)}</{tag}>"


def _render_table_cell(tok):
    tag = "th" if (tok.get("attrs") or {}).get("head") else "td"
    return f"<{tag}>{_render_tokens(tok.get('children'))}</{tag}>"


def _render_table_row(tok):
    return f"<tr>{_render_tokens(tok.get('children'))}</tr>"


def _render_table(tok):
    head_html = ""
    body_html = ""
    for child in tok.get("children") or []:
        if child.get("type") == "table_head":
            head_html = f"<thead>{_render_table_row(child)}</thead>"
        elif child.get("type") == "table_body":
            body_html = f"<tbody>{_render_tokens(child.get('children'))}</tbody>"
    return f"<table>{head_html}{body_html}</table>"


_RENDERERS = {
    "text": _render_text,
    "softbreak": lambda tok: "\n",
    "linebreak": lambda tok: "<br />",
    "thematic_break": lambda tok: "<hr>",
    "strong": _render_inline_container("strong"),
    "emphasis": _render_inline_container("em"),
    "strikethrough": _render_inline_container("s"),
    "codespan": _render_codespan,
    "link": _render_link,
    "image": _render_image,
    "paragraph": _render_paragraph,
    "heading": _render_heading,
    "block_quote": _render_block_quote,
    "block_code": _render_block_code,
    "block_html": _render_raw_html,
    "inline_html": _render_raw_html,
    "block_text": _render_block_text,
    "list": _render_list,
    "list_item": _render_list_item,
    "table": _render_table,
    "table_head": _render_table_row,
    "table_cell": _render_table_cell,
    "blank_line": lambda tok: "",
}
