"""
Excel and PDF builders for the gap-detection results.

Excel (XlsxWriter):
  - Sheet "Summary"  : KPI cards + filter echo.
  - Sheet "Detail"   : one row per gap, formatted headers + frozen header row.

PDF (reportlab):
  - Page 1: Executive summary — KPIs + filter echo.
  - Page 2+: Top-50 detail table (so a single PDF is readable but doesn't
    become a 200-page document on big result sets).

Money is rendered with a generic currency symbol (¤); the source dataset
does not specify currency (CLAUDE.md §"Conventions").
"""
from __future__ import annotations

import io
from typing import Iterable

import xlsxwriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .schemas import GapFiltersIn, GapKPIs, GapRow

CURRENCY = "¤"


def _money(n: float) -> str:
    return f"{CURRENCY}{n:,.2f}"


def _percent(n: float) -> str:
    return f"{n * 100:.1f}%"


def _filter_str(f: GapFiltersIn) -> str:
    parts = [
        f"shop={f.shop}",
        f"abc={','.join(c.value for c in f.abc_classes)}",
        f"min_shops={f.min_shops_selling}",
        f"gap_threshold={_percent(f.gap_threshold)}",
    ]
    if f.department:
        parts.append(f"department={f.department}")
    return ", ".join(parts)


# --- Excel ---------------------------------------------------------------


def build_excel(
    rows: list[GapRow], kpis: GapKPIs, filters: GapFiltersIn
) -> bytes:
    buf = io.BytesIO()
    workbook = xlsxwriter.Workbook(buf)

    header_fmt = workbook.add_format({
        "bold": True, "bg_color": "#1F2937", "color": "white",
        "align": "left", "valign": "vcenter", "border": 1,
    })
    money_fmt = workbook.add_format({"num_format": "#,##0.00"})
    pct_fmt = workbook.add_format({"num_format": "0.0%"})
    int_fmt = workbook.add_format({"num_format": "#,##0"})
    title_fmt = workbook.add_format({
        "bold": True, "font_size": 14, "bg_color": "#1F2937",
        "color": "white", "align": "left", "valign": "vcenter",
    })

    # Sheet 1: Summary
    summary = workbook.add_worksheet("Summary")
    summary.set_column(0, 0, 26)
    summary.set_column(1, 1, 24)
    summary.merge_range("A1:B1", "Missing Winners — Summary", title_fmt)
    summary.set_row(0, 24)

    summary.write("A3", "Filter", header_fmt)
    summary.write("B3", _filter_str(filters), header_fmt)
    summary.write("A4", "Total gaps", header_fmt)
    summary.write_number("B4", kpis.total_gaps, int_fmt)
    summary.write("A5", "Missing Winners", header_fmt)
    summary.write_number("B5", kpis.missing_winners, int_fmt)
    summary.write("A6", "Underperforming", header_fmt)
    summary.write_number("B6", kpis.underperforming, int_fmt)
    summary.write("A7", "Class A gaps", header_fmt)
    summary.write_number("B7", kpis.class_a_gaps, int_fmt)
    summary.write("A8", "Class B gaps", header_fmt)
    summary.write_number("B8", kpis.class_b_gaps, int_fmt)
    summary.write("A9", "Potential revenue", header_fmt)
    summary.write_number("B9", kpis.potential_revenue, money_fmt)

    # Sheet 2: Detail
    detail = workbook.add_worksheet("Detail")
    headers = [
        "ArticleCode", "Department", "ABC", "NumShopsSelling",
        "ShopSaleValue", "ChainAvgSaleValue", "GapScore",
        "PotentialLostRevenue", "Status", "NeverStocked",
    ]
    detail.set_row(0, 22)
    for col, name in enumerate(headers):
        detail.write(0, col, name, header_fmt)
    widths = [14, 22, 6, 16, 16, 18, 10, 22, 18, 14]
    for col, w in enumerate(widths):
        detail.set_column(col, col, w)
    detail.freeze_panes(1, 0)

    for r, row in enumerate(rows, start=1):
        detail.write_number(r, 0, row.ArticleCode, int_fmt)
        detail.write_string(r, 1, row.DepartmentName)
        detail.write_string(r, 2, row.ABCClass.value)
        detail.write_number(r, 3, row.NumShopsSelling, int_fmt)
        detail.write_number(r, 4, row.ShopSaleValue, money_fmt)
        detail.write_number(r, 5, row.ChainAvgSaleValue, money_fmt)
        detail.write_number(r, 6, row.GapScore, pct_fmt)
        detail.write_number(r, 7, row.PotentialLostRevenue, money_fmt)
        detail.write_string(r, 8, row.Status.value)
        detail.write_boolean(r, 9, row.NeverStocked)

    workbook.close()
    return buf.getvalue()


# --- PDF -----------------------------------------------------------------


def build_pdf(
    rows: list[GapRow], kpis: GapKPIs, filters: GapFiltersIn
) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title="Missing Winners Report",
    )

    styles = getSampleStyleSheet()
    h1 = styles["Heading1"]
    h2 = styles["Heading2"]
    body = styles["BodyText"]
    small = ParagraphStyle("small", parent=body, fontSize=8, leading=10)
    cell = ParagraphStyle("cell", parent=body, fontSize=7, leading=9)

    story: list = []

    story.append(Paragraph("Missing Winners Report", h1))
    story.append(Paragraph(f"Filters: {_filter_str(filters)}", small))
    story.append(Spacer(1, 6))

    kpi_data = [
        ["Total gaps", "Missing Winners", "Underperforming", "Class A", "Class B",
         "Potential revenue"],
        [
            str(kpis.total_gaps),
            str(kpis.missing_winners),
            str(kpis.underperforming),
            str(kpis.class_a_gaps),
            str(kpis.class_b_gaps),
            _money(kpis.potential_revenue),
        ],
    ]
    kpi_table = Table(kpi_data, colWidths=[38 * mm] * 6)
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, 1), 14),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
        ("TOPPADDING", (0, 1), (-1, 1), 6),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 8))
    story.append(Paragraph("Top 50 by Potential Lost Revenue", h2))
    story.append(Spacer(1, 4))

    # Detail table — top 50 to keep PDF readable
    top = rows[:50]
    detail_header = [
        "Article", "Department", "ABC", "Status",
        "Shop Sale", "Chain Avg", "Gap %", "Potential Lost",
    ]
    detail_rows: list[list] = [detail_header]
    for r in top:
        detail_rows.append([
            Paragraph(str(r.ArticleCode), cell),
            Paragraph(r.DepartmentName, cell),
            Paragraph(r.ABCClass.value, cell),
            Paragraph(r.Status.value, cell),
            Paragraph(_money(r.ShopSaleValue), cell),
            Paragraph(_money(r.ChainAvgSaleValue), cell),
            Paragraph(_percent(r.GapScore), cell),
            Paragraph(_money(r.PotentialLostRevenue), cell),
        ])

    if len(detail_rows) == 1:
        detail_rows.append([Paragraph("No gaps for current filters.", cell)] * 8)

    col_widths = [
        24 * mm, 56 * mm, 10 * mm, 28 * mm,
        26 * mm, 26 * mm, 16 * mm, 30 * mm,
    ]
    detail_table = Table(detail_rows, colWidths=col_widths, repeatRows=1)
    detail_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("ALIGN", (2, 1), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#F3F4F6")]),
    ]))
    story.append(detail_table)

    if len(rows) > 50:
        story.append(Spacer(1, 6))
        story.append(Paragraph(
            f"Showing top 50 of {len(rows)} rows. Download the Excel export "
            f"for the full result set.",
            small,
        ))

    doc.build(story)
    return buf.getvalue()
