"""Conversion fidelity test for gdoc_builder.

Generates a representative .docx that exercises every formatting feature
used by build_readout(). Upload this file to Google Drive with
convert_to_google_doc=True and manually check what survives.

Usage:
    python tests/test_gdoc_conversion.py

Output:
    tests/fixtures/conversion_test.docx

Manual test checklist (check each in the converted Google Doc):
    [ ] H1 title renders as Heading 1 in doc outline
    [ ] H2 sections (Context, Summary, Analysis, Next Steps, Resources)
    [ ] H3 sub-sections (Primary Learnings, Finding 1, etc.)
    [ ] H4 sub-findings (Sub-finding 1a, etc.)
    [ ] Bold text (headlines, labels, confidence badge)
    [ ] Italic text (subtitle, captions, caveats)
    [ ] Numbered lists (Primary Learnings, Recommendations)
    [ ] Gray-shaded table cell with monospace SQL
    [ ] Embedded PNG chart image (centered, ~6 inches)
    [ ] Figure caption (italic, gray, small font, centered)
    [ ] Internal bookmark links (>> See Finding 1 jumps to Finding 1)
    [ ] Page breaks between major sections
    [ ] Bold label detection ("The Insight:" auto-bolded)
    [ ] Confidence badge renders as colored shaded cell (green/yellow/orange)
    [ ] Data stamp renders as gray shaded cell under Finding heading
    [ ] Methodology & SQL section appears under findings (H4 gray heading)
    [ ] Cross-verification label renders in gray italic
    [ ] Resources section shows "Additional Queries" (not duplicating inline SQL)
    [ ] Tighter spacing (no triple blank lines between sections)
"""

import os
import sys
import tempfile

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helpers.gdoc_builder import (
    build_readout, AnalysisData, Finding, SubFinding,
    Recommendation, SqlQuery, SuccessTracking,
)


def _create_test_chart(path: str) -> None:
    """Create a simple test chart PNG."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(8, 5))
        categories = ["Jan", "Feb", "Mar", "Apr", "May"]
        values = [78, 72, 65, 59, 55]
        bars = ax.bar(categories, values, color=["#1E293B"] * 3 + ["#D97706"] * 2)
        ax.set_title("Mobile Checkout Conversion Rate (%)", fontsize=14, fontweight="bold")
        ax.set_ylabel("Conversion Rate (%)")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_ylim(0, 100)
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, val + 2,
                    f"{val}%", ha="center", fontsize=11)
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
    except ImportError:
        # If matplotlib isn't available, create a minimal PNG
        # 1x1 white pixel PNG
        import struct, zlib
        def _minimal_png(path):
            sig = b'\x89PNG\r\n\x1a\n'
            ihdr_data = struct.pack('>IIBBBBB', 100, 50, 8, 2, 0, 0, 0)
            ihdr_crc = struct.pack('>I', zlib.crc32(b'IHDR' + ihdr_data) & 0xffffffff)
            ihdr = struct.pack('>I', 13) + b'IHDR' + ihdr_data + ihdr_crc
            raw = b''
            for _ in range(50):
                raw += b'\x00' + b'\xff\xff\xff' * 100
            compressed = zlib.compress(raw)
            idat_crc = struct.pack('>I', zlib.crc32(b'IDAT' + compressed) & 0xffffffff)
            idat = struct.pack('>I', len(compressed)) + b'IDAT' + compressed + idat_crc
            iend = struct.pack('>I', 0) + b'IEND' + struct.pack('>I', zlib.crc32(b'IEND') & 0xffffffff)
            with open(path, 'wb') as f:
                f.write(sig + ihdr + idat + iend)
        _minimal_png(path)


def generate_test_fixture():
    """Generate the conversion test .docx."""
    # Create a test chart
    chart_dir = tempfile.mkdtemp()
    chart_path = os.path.join(chart_dir, "test_chart.png")
    _create_test_chart(chart_path)

    data = AnalysisData(
        title="Conversion Fidelity Test: All Formatting Features",
        subtitle="Test Dataset | 2026-04-03 | Formatting Verification",
        author="Test Author",
        date="2026-04-03",
        confidence_grade="B+",
        confidence_score=85,
        confidence_caveat="Treat as directional — test data only.",
        context=(
            "This document tests every formatting feature used by "
            "gdoc_builder.build_readout(). Upload it to Google Drive with "
            "convert_to_google_doc=True and check each feature against the "
            "manual test checklist in the script header."
        ),
        findings=[
            Finding(
                headline="Bold labels are auto-detected",
                summary="The builder detects known label prefixes and applies bold styling automatically.",
                sub_findings=[
                    SubFinding(
                        title="Sub-finding with chart",
                        body=(
                            "The Insight: This paragraph starts with a known bold label "
                            "prefix. The label should be bold, the rest regular weight.\n\n"
                            "Why this matters for product: Another bold label test. If this "
                            "renders with just the label bold, the detection works."
                        ),
                        chart_path=chart_path,
                        chart_caption="Mobile Checkout Conversion Rate by Month",
                    ),
                    SubFinding(
                        title="Sub-finding without chart",
                        body=(
                            "Bottom line: This tests a third bold label. The text after "
                            "the colon should be regular weight.\n\n"
                            "This paragraph has no bold label — it should render entirely "
                            "in regular weight body text."
                        ),
                    ),
                ],
                data_stamp="[1.2M rows | Jan-Mar 2026 | CHECKOUT_EVENTS | Confidence: B+ (85/100)]",
                methodology=(
                    "Approach: segmented comparison of mobile vs desktop checkout funnels. "
                    "Aggregation: COUNT DISTINCT user_id by step and device. "
                    "Filters: date >= '2026-01-01', status IN ('completed', 'abandoned'). "
                    "Date handling: monthly granularity, UTC."
                ),
                sql=(
                    "SELECT\n"
                    "  device_type,\n"
                    "  step_name,\n"
                    "  COUNT(DISTINCT user_id) AS users\n"
                    "FROM checkout_events\n"
                    "WHERE event_date >= '2026-01-01'\n"
                    "  AND status IN ('completed', 'abandoned')\n"
                    "GROUP BY device_type, step_name\n"
                    "ORDER BY device_type, step_name"
                ),
                cross_verification="Type B: Parts-to-whole — PASS (Within 0.30% tolerance)",
            ),
            Finding(
                headline="Bookmark links connect Summary to Analysis",
                summary="The >> links in Primary Learnings should jump to the corresponding Finding heading.",
                sub_findings=[
                    SubFinding(
                        title="Link target verification",
                        body=(
                            "If you clicked '>> See Finding 2' in the Summary section, "
                            "you should have landed here. This tests internal bookmark "
                            "navigation."
                        ),
                    ),
                ],
                data_stamp="[340K rows | Jan-Mar 2026 | FUNNEL_EVENTS | Confidence: B+ (85/100)]",
                methodology="Approach: bookmark navigation verification. No SQL required.",
                cross_verification="Type A: Boundary check — PASS (3 checks passed)",
            ),
            Finding(
                headline="Missing chart shows placeholder",
                summary="When a chart path doesn't exist, a placeholder message appears.",
                sub_findings=[
                    SubFinding(
                        title="Missing chart test",
                        body="This sub-finding references a chart that does not exist.",
                        chart_path="/nonexistent/path/to/missing_chart.png",
                        chart_caption="This should not appear",
                    ),
                ],
                # No provenance fields — tests backward compatibility
            ),
        ],
        synthesis=(
            "All formatting features should render correctly in the converted "
            "Google Doc. Any feature that does not survive conversion should be "
            "documented in the test results."
        ),
        implications=(
            "Features that do not survive .docx-to-Google-Docs conversion will "
            "need alternative approaches (text references instead of hyperlinks, "
            "plain code blocks instead of shaded cells, etc.)."
        ),
        recommendations=[
            Recommendation(
                "Verify heading hierarchy in doc outline",
                "H1-H4 should appear in the Google Doc outline sidebar.",
                "High",
            ),
            Recommendation(
                "Check bookmark link navigation",
                ">> links should jump to the correct finding.",
                "Medium",
            ),
            Recommendation(
                "Verify SQL formatting survives",
                "Gray background and monospace font should persist.",
                "Low",
            ),
        ],
        next_steps_actions=(
            "1. Upload this .docx to Google Drive\n"
            "2. Open as Google Doc\n"
            "3. Check each item in the manual test checklist"
        ),
        success_tracking=SuccessTracking(
            metric="Formatting features surviving conversion",
            baseline="Unknown",
            target="All 14 features pass",
            check_in_date="After first upload test",
        ),
        open_questions=(
            "Do python-docx bookmarks survive .docx → Google Docs conversion?\n"
            "Does gray table cell shading survive conversion?\n"
            "Do page breaks become section breaks or just spacing?"
        ),
        sql_queries=[
            SqlQuery(
                title="Sample Funnel Query",
                sql=(
                    "SELECT\n"
                    "  step_name,\n"
                    "  COUNT(DISTINCT user_id) AS users,\n"
                    "  ROUND(\n"
                    "    COUNT(DISTINCT user_id) * 100.0\n"
                    "    / FIRST_VALUE(COUNT(DISTINCT user_id))\n"
                    "      OVER (ORDER BY step_order),\n"
                    "    1\n"
                    "  ) AS pct_of_start\n"
                    "FROM funnel_events\n"
                    "WHERE event_date >= '2026-01-01'\n"
                    "GROUP BY step_name, step_order\n"
                    "ORDER BY step_order;"
                ),
                used_in_finding=1,
                database="ecommerce.funnel_events",
            ),
        ],
        companion_analyses="Previous checkout analysis (Dec 2025)\nMobile UX audit report",
        data_sources=(
            "Production database. Tables: checkout_events, "
            "funnel_events. Date range: Jan 1 - Mar 31, 2026. "
            "1.2M sessions, 340K unique users."
        ),
    )

    # Generate to tests/fixtures/
    fixtures_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "fixtures"
    )
    os.makedirs(fixtures_dir, exist_ok=True)

    output_path = build_readout(data, output_dir=fixtures_dir)

    # Rename to a fixed name for easy reference
    final_path = os.path.join(fixtures_dir, "conversion_test.docx")
    if os.path.exists(final_path):
        os.remove(final_path)
    os.rename(output_path, final_path)

    print(f"Test fixture generated: {final_path}")
    print(f"File size: {os.path.getsize(final_path):,} bytes")
    print()
    print("To test conversion fidelity:")
    print("  1. Upload to Google Drive (convert to Google Doc)")
    print("  2. Check each item in the manual test checklist (see script header)")
    print("  3. Document which features survive and which don't")

    # Cleanup temp chart
    os.remove(chart_path)
    os.rmdir(chart_dir)

    return final_path


if __name__ == "__main__":
    generate_test_fixture()
