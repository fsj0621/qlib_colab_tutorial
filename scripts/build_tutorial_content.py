"""Build compact, safe tutorial content from a Jupyter notebook.

The generated JSON is consumed by docs/tutorial.js.  It intentionally keeps
the notebook as the source of truth while grouping cells under the notebook's
Markdown headings so a long teaching notebook remains usable on the web.
"""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path


MODULE_HEADING = re.compile(r"^##\s+(\d+)\.\s*(.+?)\s*$", re.MULTILINE)
SUBHEADING = re.compile(r"^(#{3,6})\s+(.+?)\s*$", re.MULTILINE)
EXERCISE_MARKERS = ("课后作业", "请补充代码", "TODO", "请补充")


def render_inline(value: str) -> str:
    text = html.escape(value, quote=True)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", text)

    def image(match: re.Match[str]) -> str:
        alt, url = match.group(1), match.group(2)
        if not url.startswith(("https://", "http://")):
            return alt
        return (
            f'<img src="{url}" alt="{alt}" loading="lazy" '
            'referrerpolicy="no-referrer">'
        )

    # Images must be rendered before ordinary links; otherwise the link
    # pattern consumes the [alt](url) part and leaves a literal leading "!".
    text = re.sub(r"!\[([^\]]*)\]\((https?://[^\s)]+)\)", image, text)

    def link(match: re.Match[str]) -> str:
        label, url = match.group(1), match.group(2)
        if not url.startswith(("https://", "http://")):
            return label
        return f'<a href="{url}" target="_blank" rel="noopener">{label}</a>'

    return re.sub(r"\[([^\]]+)\]\((https?://[^\s)]+)\)", link, text)


def markdown_to_html(source: str) -> str:
    """Render the small Markdown subset used by the teaching notebooks."""
    lines = source.strip().splitlines()
    output: list[str] = []
    paragraph: list[str] = []
    list_type: str | None = None
    in_fence = False
    fence_lines: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            output.append(f"<p>{'<br>'.join(render_inline(line) for line in paragraph)}</p>")
            paragraph.clear()

    def close_list() -> None:
        nonlocal list_type
        if list_type:
            output.append(f"</{list_type}>")
            list_type = None

    for raw_line in lines:
        line = raw_line.rstrip()
        if line.strip().startswith("```"):
            flush_paragraph()
            close_list()
            if in_fence:
                output.append(f"<pre><code>{html.escape(chr(10).join(fence_lines))}</code></pre>")
                fence_lines.clear()
            in_fence = not in_fence
            continue
        if in_fence:
            fence_lines.append(line)
            continue
        if not line.strip():
            flush_paragraph()
            close_list()
            continue
        if re.fullmatch(r"\s*---+\s*", line):
            flush_paragraph()
            close_list()
            output.append("<hr>")
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            flush_paragraph()
            close_list()
            level = min(5, len(heading.group(1)) + 1)
            output.append(f"<h{level}>{render_inline(heading.group(2))}</h{level}>")
            continue
        quote = re.match(r"^>\s?(.*)$", line)
        if quote:
            flush_paragraph()
            close_list()
            output.append(f"<blockquote>{render_inline(quote.group(1))}</blockquote>")
            continue
        unordered = re.match(r"^\s*[-*+]\s+(.+)$", line)
        ordered = re.match(r"^\s*\d+[.)]\s+(.+)$", line)
        if unordered or ordered:
            flush_paragraph()
            wanted = "ul" if unordered else "ol"
            if list_type != wanted:
                close_list()
                output.append(f"<{wanted}>")
                list_type = wanted
            output.append(f"<li>{render_inline((unordered or ordered).group(1))}</li>")
            continue
        paragraph.append(line.strip())

    flush_paragraph()
    close_list()
    if in_fence and fence_lines:
        output.append(f"<pre><code>{html.escape(chr(10).join(fence_lines))}</code></pre>")
    return "\n".join(output)


def output_blocks(outputs: list[dict]) -> list[dict]:
    rendered: list[dict] = []
    for output_index, output in enumerate(outputs):
        if output.get("output_type") == "error":
            continue
        data = output.get("data", {})
        figure = data.get("application/vnd.plotly.v1+json")
        if isinstance(figure, dict) and isinstance(figure.get("data"), list):
            rendered.append(
                {
                    "type": "plotly",
                    "index": output_index,
                    "figure": figure,
                }
            )
            continue
        value = data.get("text/plain")
        if value is None:
            continue
        text = "".join(value) if isinstance(value, list) else str(value)
        text = text.strip()
        if not text:
            continue
        clipped = len(text) > 2200
        rendered.append(
            {
                "type": "text",
                "index": output_index,
                "text": text[:2200],
                "truncated": clipped,
            }
        )
    return rendered


def convert_cell(cell: dict, index: int) -> dict | None:
    source = "".join(cell.get("source", [])).strip()
    if not source:
        return None
    if cell.get("cell_type") == "markdown":
        return {"type": "markdown", "html": markdown_to_html(source)}
    if cell.get("cell_type") != "code":
        return None

    lines = source.splitlines()
    exercise = any(marker in source for marker in EXERCISE_MARKERS)
    very_long = len(lines) > 180
    if very_long:
        source = "\n".join(lines[:18])
    return {
        "type": "code",
        "cell": index,
        "source": source,
        "lineCount": len(lines),
        "collapsed": len(lines) > 18 or len(source) > 1600,
        "omitted": very_long,
        "exercise": exercise,
        "outputs": output_blocks(cell.get("outputs", [])),
    }


def build_module(cells: list[dict], start: int, end: int, number: int, title: str) -> dict:
    heading_source = "".join(cells[start].get("source", []))
    heading_match = MODULE_HEADING.search(heading_source)
    intro_source = heading_source[heading_match.end() :].strip() if heading_match else ""
    groups: list[dict] = []
    current = {"title": "本章导入", "cells": []}
    if intro_source:
        current["cells"].append({"type": "markdown", "html": markdown_to_html(intro_source)})

    for index in range(start + 1, end):
        cell = cells[index]
        source = "".join(cell.get("source", []))
        if cell.get("cell_type") == "markdown":
            sub_match = SUBHEADING.search(source)
            if sub_match:
                if current["cells"]:
                    groups.append(current)
                current = {"title": re.sub(r"\*+", "", sub_match.group(2)).strip(), "cells": []}
                remainder = (source[: sub_match.start()] + source[sub_match.end() :]).strip()
                if remainder:
                    current["cells"].append({"type": "markdown", "html": markdown_to_html(remainder)})
                continue
        converted = convert_cell(cell, index)
        if converted:
            current["cells"].append(converted)

    if current["cells"]:
        groups.append(current)
    for group in groups:
        group["codeCount"] = sum(cell["type"] == "code" for cell in group["cells"])
        group["exercise"] = any(cell.get("exercise", False) for cell in group["cells"])

    module_cells = [cell for group in groups for cell in group["cells"]]
    return {
        "number": number,
        "title": title,
        "cellRange": [start, end - 1],
        "stats": {
            "markdown": sum(cell["type"] == "markdown" for cell in module_cells),
            "code": sum(cell["type"] == "code" for cell in module_cells),
            "exercises": sum(cell.get("exercise", False) for cell in module_cells),
        },
        "groups": groups,
    }


def build(notebook_path: Path, revision: str) -> dict:
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    cells = notebook.get("cells", [])
    starts: list[tuple[int, int, str]] = []
    for index, cell in enumerate(cells):
        if cell.get("cell_type") != "markdown":
            continue
        match = MODULE_HEADING.search("".join(cell.get("source", [])))
        if match:
            starts.append((index, int(match.group(1)), match.group(2).strip()))
    modules = []
    for position, (start, number, title) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(cells)
        modules.append(build_module(cells, start, end, number, title))
    return {
        "schemaVersion": 2,
        "source": notebook_path.name,
        "revision": revision,
        "cellCount": len(cells),
        "modules": modules,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--revision", default="working copy")
    args = parser.parse_args()
    content = build(args.input, args.revision)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {args.output}: {len(content['modules'])} modules, {content['cellCount']} cells")


if __name__ == "__main__":
    main()
