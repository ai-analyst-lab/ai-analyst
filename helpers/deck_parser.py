"""
Deck Parser — Parse presentation formats into a common intermediate representation.

Supported input formats:
- Marp markdown (.marp.md) → split on --- separators, extract structure
- Google Slides → via MCP get_presentation + get_page, extract text/images

Each slide is represented as a SlideObject dataclass with consistent fields
regardless of source format.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SlideObject:
    """Common intermediate representation for a single slide."""

    index: int
    title: str = ""
    body_text: str = ""
    bullets: list[str] = field(default_factory=list)
    bullet_count: int = 0
    has_chart: bool = False
    has_data_table: bool = False
    word_count: int = 0
    slide_class: str = ""
    source_format: str = "marp"  # "marp" | "gslides"
    raw_content: str = ""  # Original slide content for reference


def parse_marp(path: str | Path) -> list[SlideObject]:
    """Parse a Marp markdown file into a list of SlideObjects.

    Splits on '---' slide separators, extracts title (first # or ##),
    body text, bullet items, chart references, and slide classes.
    """
    path = Path(path)
    content = path.read_text(encoding="utf-8")

    # Remove YAML frontmatter if present
    if content.startswith("---"):
        # Find the closing --- of frontmatter
        end = content.find("---", 3)
        if end != -1:
            content = content[end + 3 :].strip()

    # Split on --- slide separators (must be on their own line)
    raw_slides = re.split(r"\n---\n", content)

    slides: list[SlideObject] = []

    for i, raw in enumerate(raw_slides):
        raw = raw.strip()
        if not raw:
            continue

        slide = SlideObject(index=i, source_format="marp", raw_content=raw)

        # Extract slide class from <!-- _class: ... -->
        class_match = re.search(r"<!--\s*_class:\s*(.+?)\s*-->", raw)
        if class_match:
            slide.slide_class = class_match.group(1).strip()

        # Extract title (first heading)
        title_match = re.search(r"^#+\s+(.+)$", raw, re.MULTILINE)
        if title_match:
            slide.title = title_match.group(1).strip()

        # Extract body text (everything that's not the title, directives, or images)
        body_lines = []
        for line in raw.split("\n"):
            stripped = line.strip()
            # Skip directives, headings, image refs, empty lines
            if stripped.startswith("<!--") or stripped.startswith("#"):
                continue
            if stripped.startswith("![") or stripped.startswith("<img"):
                continue
            if stripped:
                body_lines.append(stripped)
        slide.body_text = "\n".join(body_lines)

        # Extract bullets (lines starting with - or *)
        bullets = []
        for line in raw.split("\n"):
            stripped = line.strip()
            if re.match(r"^[-*]\s+", stripped):
                bullet_text = re.sub(r"^[-*]\s+", "", stripped)
                bullets.append(bullet_text)
        slide.bullets = bullets
        slide.bullet_count = len(bullets)

        # Detect charts (image references or chart containers)
        has_chart = bool(
            re.search(r"!\[.*?\]\(.*?\)", raw)
            or re.search(r'<div\s+class="chart', raw)
            or re.search(r"<img\s+", raw)
        )
        slide.has_chart = has_chart

        # Detect data tables (markdown tables or HTML tables)
        has_table = bool(
            re.search(r"\|.+\|.+\|", raw) or re.search(r"<table", raw, re.IGNORECASE)
        )
        slide.has_data_table = has_table

        # Word count (body + title, excluding markup)
        all_text = f"{slide.title} {slide.body_text}"
        words = re.findall(r"\b\w+\b", all_text)
        slide.word_count = len(words)

        slides.append(slide)

    return slides


def parse_google_slides(presentation_id: str) -> list[SlideObject]:
    """Parse a Google Slides presentation into SlideObjects.

    Requires the Google Workspace MCP connection. This function returns
    a structure that can be populated by calling MCP tools:
      1. get_presentation(presentation_id) → slide IDs
      2. get_page(presentation_id, page_id) → per-slide content

    Returns a list of SlideObjects with source_format='gslides'.

    NOTE: This function provides the parsing logic but requires MCP calls
    to be made by the calling agent. It returns a template structure that
    the agent populates with MCP responses.
    """
    # This is a structural helper — the actual MCP calls are made by the
    # agent orchestrating the pipeline. This function processes the raw
    # response data from get_presentation and get_page.
    raise NotImplementedError(
        "Google Slides parsing requires MCP calls. Use parse_gslides_response() "
        "with the raw MCP response data instead."
    )


def parse_gslides_response(
    slides_data: list[dict],
) -> list[SlideObject]:
    """Parse pre-fetched Google Slides data into SlideObjects.

    Args:
        slides_data: List of dicts, each containing:
            - index: slide position
            - title: extracted title text
            - body_text: all non-title text
            - shapes: list of shape descriptions
            - has_image: whether the slide contains image elements
            - has_table: whether the slide contains table elements
    """
    slides: list[SlideObject] = []

    for data in slides_data:
        slide = SlideObject(
            index=data.get("index", 0),
            title=data.get("title", ""),
            body_text=data.get("body_text", ""),
            source_format="gslides",
            raw_content=str(data),
        )

        # Extract bullets from body text
        bullets = []
        for line in slide.body_text.split("\n"):
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                bullets.append(stripped)
        slide.bullets = bullets
        slide.bullet_count = len(bullets)

        slide.has_chart = data.get("has_image", False)
        slide.has_data_table = data.get("has_table", False)

        # Word count
        all_text = f"{slide.title} {slide.body_text}"
        words = re.findall(r"\b\w+\b", all_text)
        slide.word_count = len(words)

        slide.slide_class = data.get("layout", "")

        slides.append(slide)

    return slides


def format_slide_summary(slides: list[SlideObject]) -> str:
    """Format a list of SlideObjects into a human-readable summary.

    Useful for quick deck overview before detailed critique.
    """
    lines = [f"# Deck Summary ({len(slides)} slides)\n"]

    for slide in slides:
        flags = []
        if slide.has_chart:
            flags.append("chart")
        if slide.has_data_table:
            flags.append("table")
        if slide.bullet_count > 6:
            flags.append(f"WALL OF BULLETS ({slide.bullet_count})")

        flag_str = f" [{', '.join(flags)}]" if flags else ""
        title_display = slide.title if slide.title else "(no title)"

        lines.append(
            f"**Slide {slide.index + 1}:** {title_display} "
            f"({slide.word_count} words, {slide.bullet_count} bullets){flag_str}"
        )

    return "\n".join(lines)
