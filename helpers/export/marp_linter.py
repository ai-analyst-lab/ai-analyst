"""Marp deck linter — validates deck quality before export.

Checks:
  (a) Frontmatter completeness (marp, theme, size, paginate, html, footer)
  (b) HTML component usage (flags plain-markdown-only slides)
  (c) CSS class validation (_class directives vs known theme classes)
  (d) Invalid class detection (e.g. breathing → impact)
  (e) Slide count bounds (8-22)
  (f) R2 title collision: chart title ≠ slide headline
  (g) R6 pacing: consecutive content slides without breathing room
  (h) Image embedding: bare markdown images (IMG-BARE-MD)

Returns a structured lint report with severity levels: ERROR, WARNING, INFO.
"""

import re
from pathlib import Path


# --- Known valid classes per theme ---
VALID_CLASSES_LIGHT = {
    "title", "section-opener", "insight", "impact", "two-col",
    "chart-left", "chart-right", "diagram",
    "chart-full", "kpi", "takeaway", "recommendation", "appendix",
}

VALID_CLASSES_DARK = {
    "dark-title", "dark-impact", "section-opener", "insight", "two-col",
    "chart-left", "chart-right", "diagram",
    "chart-full", "kpi", "takeaway", "recommendation", "appendix",
}

# Classes that exist in no theme — common mistakes
INVALID_CLASSES = {
    "breathing": "impact",
    "hero": "title",
    "break": "impact",
    "transition": "section-opener",
}

# Required frontmatter keys and their expected values
REQUIRED_FRONTMATTER = {
    "marp": True,
    "theme": None,        # any string
    "size": "16:9",
    "paginate": True,
    "html": True,
    "footer": None,       # any non-empty string
}

# HTML components we look for (class names from the CSS)
HTML_COMPONENTS = {
    "metric-callout", "kpi-row", "kpi-card", "so-what", "finding",
    "rec-row", "chart-container", "before-after", "box-grid", "flow",
    "vflow", "layers", "timeline", "checklist", "callout", "badge",
    "delta", "data-source", "accent-bar",
}

# Minimum distinct component types for a passing deck
MIN_COMPONENT_TYPES = 3

# Slide count bounds
MIN_SLIDES = 8
MAX_SLIDES = 22


def _parse_frontmatter(text):
    """Extract YAML frontmatter from Marp markdown.

    Returns (dict, rest_of_text). Returns ({}, text) if no frontmatter.
    """
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}, text

    fm = {}
    for line in match.group(1).split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            # Parse booleans
            if val.lower() == "true":
                val = True
            elif val.lower() == "false":
                val = False
            fm[key] = val

    rest = text[match.end():]
    return fm, rest


def _split_slides(text):
    """Split markdown (after frontmatter) into individual slides."""
    # Marp uses --- as slide separator (on its own line)
    slides = re.split(r"\n---\s*\n", text)
    # First element may be empty if text starts with ---
    return [s.strip() for s in slides if s.strip()]


def lint_deck(deck_path):
    """Run all lint checks on a Marp deck file.

    Args:
        deck_path: Path to the .marp.md file.

    Returns:
        dict with keys:
          - issues: list of {severity, code, message, slide}
          - summary: {errors, warnings, info, pass}
          - frontmatter: parsed frontmatter dict
          - slide_count: int
          - components_found: set of component class names used
    """
    deck_path = Path(deck_path)
    text = deck_path.read_text(encoding="utf-8")

    issues = []
    fm, body = _parse_frontmatter(text)
    slides = _split_slides(body)

    # --- (a) Frontmatter completeness ---
    if not fm:
        issues.append({
            "severity": "ERROR",
            "code": "FM-MISSING",
            "message": "No YAML frontmatter found. Deck will not render as Marp.",
            "slide": 0,
        })
    else:
        for key, expected in REQUIRED_FRONTMATTER.items():
            if key not in fm:
                issues.append({
                    "severity": "ERROR",
                    "code": f"FM-{key.upper()}",
                    "message": f"Missing required frontmatter key: {key}",
                    "slide": 0,
                })
            elif expected is not None and fm[key] != expected:
                issues.append({
                    "severity": "ERROR",
                    "code": f"FM-{key.upper()}",
                    "message": f"Frontmatter '{key}' should be {expected!r}, got {fm[key]!r}",
                    "slide": 0,
                })

        # Footer should not be empty/placeholder
        if "footer" in fm:
            footer_val = fm["footer"]
            if isinstance(footer_val, str) and ("{{" in footer_val or not footer_val):
                issues.append({
                    "severity": "WARNING",
                    "code": "FM-FOOTER-PLACEHOLDER",
                    "message": f"Footer contains placeholder or is empty: {footer_val!r}",
                    "slide": 0,
                })

    # --- Determine theme for class validation ---
    theme = fm.get("theme", "analytics")
    if "dark" in str(theme):
        valid_classes = VALID_CLASSES_DARK
    else:
        valid_classes = VALID_CLASSES_LIGHT

    # --- (b) HTML component usage ---
    components_found = set()
    slides_without_components = []

    for i, slide in enumerate(slides, start=1):
        slide_components = set()
        for comp in HTML_COMPONENTS:
            # Match class="comp" or class="... comp ..." patterns
            if re.search(rf'class="[^"]*\b{re.escape(comp)}\b[^"]*"', slide):
                slide_components.add(comp)
            # Also match standalone class references
            if f'class="{comp}"' in slide:
                slide_components.add(comp)

        components_found.update(slide_components)

        # Check if this is a content slide with no HTML components
        has_class = re.search(r"<!--\s*_class:\s*(\S+)", slide)
        slide_class = has_class.group(1).strip() if has_class else None

        # Skip title, section-opener, impact slides — they don't need components
        non_content_classes = {"title", "section-opener", "impact", "dark-title", "dark-impact"}
        is_content_slide = slide_class not in non_content_classes

        if is_content_slide and not slide_components and len(slide) > 50:
            slides_without_components.append(i)

    if len(components_found) < MIN_COMPONENT_TYPES:
        issues.append({
            "severity": "ERROR",
            "code": "COMP-MIN",
            "message": (
                f"Only {len(components_found)} HTML component types used "
                f"(minimum {MIN_COMPONENT_TYPES}). Found: {sorted(components_found) or 'none'}"
            ),
            "slide": 0,
        })

    for s in slides_without_components:
        issues.append({
            "severity": "WARNING",
            "code": "COMP-PLAIN",
            "message": f"Slide {s} has no HTML components — consider using styled components",
            "slide": s,
        })

    # --- (c) + (d) CSS class validation ---
    for i, slide in enumerate(slides, start=1):
        class_match = re.search(r"<!--\s*_class:\s*(\S+)", slide)
        if class_match:
            cls = class_match.group(1).strip()
            if cls in INVALID_CLASSES:
                replacement = INVALID_CLASSES[cls]
                issues.append({
                    "severity": "ERROR",
                    "code": "CLASS-INVALID",
                    "message": f"Slide {i}: class '{cls}' does not exist. Use '{replacement}' instead.",
                    "slide": i,
                })
            elif cls not in valid_classes:
                issues.append({
                    "severity": "WARNING",
                    "code": "CLASS-UNKNOWN",
                    "message": f"Slide {i}: class '{cls}' not found in {theme} theme. Valid: {sorted(valid_classes)}",
                    "slide": i,
                })

    # --- (e) Slide count bounds ---
    slide_count = len(slides)
    if slide_count < MIN_SLIDES:
        issues.append({
            "severity": "WARNING",
            "code": "SLIDES-LOW",
            "message": f"Only {slide_count} slides (minimum {MIN_SLIDES}). Deck may feel too brief.",
            "slide": 0,
        })
    elif slide_count > MAX_SLIDES:
        issues.append({
            "severity": "WARNING",
            "code": "SLIDES-HIGH",
            "message": f"{slide_count} slides exceeds maximum of {MAX_SLIDES}. Consider condensing.",
            "slide": 0,
        })

    # --- (f) R2: Title collision detection ---
    for i, slide in enumerate(slides, start=1):
        # Extract slide headline (first ## line)
        headline_match = re.search(r"^##\s+(.+)$", slide, re.MULTILINE)
        if not headline_match:
            continue
        headline = headline_match.group(1).strip()

        # Extract chart titles from chart-container or img alt text
        chart_title_match = re.search(
            r'class="chart-title"[^>]*>([^<]+)', slide
        )
        if chart_title_match:
            chart_title = chart_title_match.group(1).strip()
            if chart_title.lower() == headline.lower():
                issues.append({
                    "severity": "ERROR",
                    "code": "R2-COLLISION",
                    "message": (
                        f"Slide {i}: Chart title identical to slide headline "
                        f"(both: '{headline[:60]}'). R2 violation."
                    ),
                    "slide": i,
                })

    # --- (g) R6: Breathing slide spacing ---
    consecutive_content = 0
    for i, slide in enumerate(slides, start=1):
        class_match = re.search(r"<!--\s*_class:\s*(\S+)", slide)
        cls = class_match.group(1).strip() if class_match else None

        pacing_classes = {"impact", "dark-impact", "section-opener", "takeaway"}
        if cls in pacing_classes:
            consecutive_content = 0
        else:
            consecutive_content += 1
            if consecutive_content > 4:
                issues.append({
                    "severity": "WARNING",
                    "code": "R6-PACING",
                    "message": (
                        f"Slide {i}: {consecutive_content} consecutive content slides "
                        f"without a pacing break (max 4). Insert impact or section-opener."
                    ),
                    "slide": i,
                })

    # --- (h) Image embedding checks ---
    for i, slide in enumerate(slides, start=1):
        # IMG-BARE-MD: bare markdown image syntax ![...](....png/svg)
        # that is NOT inside a <div class="chart-container"> wrapper
        bare_img_matches = re.finditer(
            r'!\[([^\]]*)\]\(([^)]+\.(?:png|svg|jpg|jpeg))\)', slide
        )
        for m in bare_img_matches:
            # Check if this image is inside a chart-container
            # Find the position of the match in the slide text
            pos = m.start()
            preceding = slide[:pos]
            # Look for an unclosed chart-container div before this image
            opens = len(re.findall(r'class="[^"]*chart-container[^"]*"', preceding))
            closes = preceding.count('</div>')
            if opens == 0 or closes >= opens:
                issues.append({
                    "severity": "WARNING",
                    "code": "IMG-BARE-MD",
                    "message": (
                        f"Slide {i}: Bare markdown image `![{m.group(1)[:30]}]({m.group(2)})` — "
                        f"wrap in <div class=\"chart-container\"> for overflow containment"
                    ),
                    "slide": i,
                })

    # --- Build summary ---
    errors = sum(1 for i in issues if i["severity"] == "ERROR")
    warnings = sum(1 for i in issues if i["severity"] == "WARNING")
    infos = sum(1 for i in issues if i["severity"] == "INFO")

    return {
        "issues": issues,
        "summary": {
            "errors": errors,
            "warnings": warnings,
            "info": infos,
            "pass": errors == 0,
        },
        "frontmatter": fm,
        "slide_count": slide_count,
        "components_found": sorted(components_found),
    }


def format_report(result):
    """Format lint results as a human-readable report string."""
    lines = []
    lines.append("=" * 60)
    lines.append("MARP DECK LINT REPORT")
    lines.append("=" * 60)

    s = result["summary"]
    status = "PASS" if s["pass"] else "FAIL"
    lines.append(f"Status: {status}")
    lines.append(f"Slides: {result['slide_count']}")
    lines.append(f"Components: {', '.join(result['components_found']) or 'none'}")
    lines.append(f"Errors: {s['errors']} | Warnings: {s['warnings']} | Info: {s['info']}")
    lines.append("-" * 60)

    for issue in result["issues"]:
        prefix = issue["severity"]
        slide = f" [slide {issue['slide']}]" if issue["slide"] else ""
        lines.append(f"  {prefix}: {issue['code']}{slide}")
        lines.append(f"    {issue['message']}")

    lines.append("=" * 60)
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python marp_linter.py <deck.marp.md>")
        sys.exit(1)

    result = lint_deck(sys.argv[1])
    print(format_report(result))
    sys.exit(0 if result["summary"]["pass"] else 1)
