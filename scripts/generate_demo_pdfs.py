#!/usr/bin/env python3
"""Render the 6 Markdown sources under `docs/sources/*.md` into `docs/*.pdf`.

Uses `reportlab` (pure Python, bundled via `uv add reportlab`) so a clean
clone can regenerate PDFs without installing `pandoc` or any system tool.

The Markdown support is intentionally minimal — just what the source docs
actually use:

    # H1, ## H2, ### H3          headings
    **bold**                     inline bold
    - bullet / * bullet           list items
    > quoted line                 blockquote (for cited examples)
    | col | col |                 simple 2+ column tables (header row + `---` divider)
    ```                          fenced code block (monospace, preserved)
    ---                          horizontal rule
    (blank line)                 paragraph break

Anything beyond that is rendered as plain paragraph text.

Usage:
    make ingest-kb   # runs this automatically if PDFs are missing
    # or
    uv run python scripts/generate_demo_pdfs.py

Both the `docs/sources/*.md` and the rendered `docs/*.pdf` are committed
to the repo, so this script is only needed after editing a source file.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import List

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Table,
    TableStyle,
)

# ── Styles ────────────────────────────────────────────────────────────────
_BASE = getSampleStyleSheet()

_H1 = ParagraphStyle(
    "DemoH1",
    parent=_BASE["Heading1"],
    fontSize=20,
    leading=24,
    spaceBefore=12,
    spaceAfter=12,
    textColor=colors.HexColor("#1a1a2e"),
)
_H2 = ParagraphStyle(
    "DemoH2",
    parent=_BASE["Heading2"],
    fontSize=15,
    leading=19,
    spaceBefore=14,
    spaceAfter=8,
    textColor=colors.HexColor("#1a1a2e"),
)
_H3 = ParagraphStyle(
    "DemoH3",
    parent=_BASE["Heading3"],
    fontSize=12,
    leading=16,
    spaceBefore=10,
    spaceAfter=6,
    textColor=colors.HexColor("#333333"),
)
_BODY = ParagraphStyle(
    "DemoBody",
    parent=_BASE["BodyText"],
    fontSize=10,
    leading=14,
    alignment=TA_LEFT,
    spaceBefore=0,
    spaceAfter=6,
)
_BULLET = ParagraphStyle(
    "DemoBullet",
    parent=_BODY,
    leftIndent=12,
)
_QUOTE = ParagraphStyle(
    "DemoQuote",
    parent=_BODY,
    leftIndent=16,
    rightIndent=16,
    textColor=colors.HexColor("#555555"),
    backColor=colors.HexColor("#f3f3f7"),
    borderPadding=6,
    spaceBefore=6,
    spaceAfter=8,
    fontName="Helvetica-Oblique",
)
_CODE = ParagraphStyle(
    "DemoCode",
    parent=_BODY,
    fontName="Courier",
    fontSize=8,
    leading=11,
    leftIndent=12,
    backColor=colors.HexColor("#f7f7f7"),
    borderPadding=4,
    spaceBefore=6,
    spaceAfter=8,
)


# ── Minimal inline-markdown expander ──────────────────────────────────────

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")


def _inline(text: str) -> str:
    """Convert a subset of inline markdown into reportlab's HTML-ish tags.

    reportlab's Paragraph accepts a limited set of tags (<b>, <i>, <font>,
    <br/>). We also need to escape stray '<' and '&' so the Paragraph
    parser doesn't choke on them.
    """
    # Escape HTML-ish chars first, but re-apply our own tags after.
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = _BOLD_RE.sub(r"<b>\1</b>", text)
    text = _ITALIC_RE.sub(r"<i>\1</i>", text)
    text = _INLINE_CODE_RE.sub(r'<font face="Courier" size="9">\1</font>', text)
    return text


# ── Markdown → Flowable parser ────────────────────────────────────────────


def _build_flowables(md: str) -> List:
    """Walk a markdown string line-by-line and emit a list of reportlab
    flowables. Keeps ~100 lines of state so the parser stays readable.
    """
    flowables: List = []
    lines = md.splitlines()
    i = 0
    n = len(lines)

    def flush_paragraph(buf: List[str]) -> None:
        if buf:
            flowables.append(Paragraph(_inline(" ".join(buf).strip()), _BODY))

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # Fenced code block
        if stripped.startswith("```"):
            i += 1
            code_lines: List[str] = []
            while i < n and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing fence
            code_html = "<br/>".join(
                line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                for line in code_lines
            )
            flowables.append(Paragraph(code_html, _CODE))
            continue

        # Horizontal rule
        if stripped == "---":
            flowables.append(
                HRFlowable(
                    width="100%",
                    thickness=0.5,
                    color=colors.HexColor("#cccccc"),
                    spaceBefore=6,
                    spaceAfter=6,
                )
            )
            i += 1
            continue

        # Headings
        if stripped.startswith("### "):
            flowables.append(Paragraph(_inline(stripped[4:]), _H3))
            i += 1
            continue
        if stripped.startswith("## "):
            flowables.append(Paragraph(_inline(stripped[3:]), _H2))
            i += 1
            continue
        if stripped.startswith("# "):
            flowables.append(Paragraph(_inline(stripped[2:]), _H1))
            i += 1
            continue

        # Blockquote (single line)
        if stripped.startswith("> "):
            flowables.append(Paragraph(_inline(stripped[2:]), _QUOTE))
            i += 1
            continue

        # Bullet list — consecutive lines starting with "- " or "* "
        if stripped.startswith(("- ", "* ")):
            items: List[ListItem] = []
            while i < n and lines[i].strip().startswith(("- ", "* ")):
                item_text = lines[i].strip()[2:]
                items.append(
                    ListItem(
                        Paragraph(_inline(item_text), _BULLET),
                        leftIndent=12,
                        bulletColor=colors.HexColor("#555555"),
                    )
                )
                i += 1
            flowables.append(
                ListFlowable(
                    items,
                    bulletType="bullet",
                    start="•",
                    leftIndent=16,
                )
            )
            continue

        # Table — header row + divider (`|---|---|`) + body rows
        if "|" in stripped and i + 1 < n and re.match(r"\|?\s*-+\s*\|", lines[i + 1]):
            table_rows: List[List[str]] = []
            header_cells = [c.strip() for c in stripped.strip("|").split("|")]
            table_rows.append(header_cells)
            i += 2  # skip header + divider
            while i < n and "|" in lines[i] and lines[i].strip().startswith("|"):
                body_cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                table_rows.append(body_cells)
                i += 1
            flowables.append(_render_table(table_rows))
            continue

        # Blank line → flush nothing special, just move on
        if stripped == "":
            i += 1
            continue

        # Default: collect contiguous non-special lines into a single paragraph.
        para_lines: List[str] = []
        while i < n:
            peek = lines[i].strip()
            if peek == "" or peek.startswith(("#", "- ", "* ", "> ", "```", "---", "|")):
                break
            para_lines.append(lines[i].strip())
            i += 1
        flush_paragraph(para_lines)

    return flowables


def _render_table(rows: List[List[str]]) -> Table:
    """Render a parsed table's cells. First row is treated as the header."""
    # Turn every cell into a Paragraph so reportlab wraps long text.
    cell_style = ParagraphStyle("cell", parent=_BODY, fontSize=9, leading=12)
    data = [[Paragraph(_inline(c), cell_style) for c in row] for row in rows]

    table = Table(data, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#bbbbbb")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9f9fb")]),
            ]
        )
    )
    return table


# ── Entry point ───────────────────────────────────────────────────────────


def render(source: Path, target: Path) -> None:
    """Render one Markdown file to one PDF."""
    md_text = source.read_text(encoding="utf-8")
    flowables = _build_flowables(md_text)

    target.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(target),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=source.stem.replace("_", " ").title(),
        author="Delivery Service Internal Docs",
    )
    doc.build(flowables)


def main() -> int:
    sources_dir = Path("docs/sources")
    target_dir = Path("docs")

    if not sources_dir.exists():
        print(f"❌ Sources directory not found: {sources_dir}")
        return 1

    md_files = sorted(sources_dir.glob("*.md"))
    if not md_files:
        print(f"❌ No Markdown files under {sources_dir}")
        return 1

    for src in md_files:
        dst = target_dir / (src.stem + ".pdf")
        render(src, dst)
        print(f"✓ Rendered {src.name} → {dst}")

    print(f"\nGenerated {len(md_files)} PDFs under {target_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
