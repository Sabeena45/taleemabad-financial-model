"""
PDF Export for Taleemabad Financial Model.
Generates professional report with key metrics and analysis.
"""

import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT


def export_to_pdf(
    cashflow_model,
    scenario_model,
    sensitivity_model,
    custom_assumptions: dict,
) -> bytes:
    """
    Generate PDF report with financial summary.

    Args:
        cashflow_model: CashFlowModel instance
        scenario_model: ScenarioModel instance
        sensitivity_model: SensitivityModel instance
        custom_assumptions: Dict of user-modified assumptions

    Returns:
        bytes: PDF file as bytes
    """
    output = io.BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=1*cm,
        leftMargin=1*cm,
        topMargin=1*cm,
        bottomMargin=1*cm,
    )

    # Styles
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#1A1A1A'),
    )

    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#6B7280'),
    )

    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=16,
        spaceBefore=20,
        spaceAfter=10,
        textColor=colors.HexColor('#3B82F6'),
    )

    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=8,
    )

    elements = []

    # =========================================================================
    # Title Page
    # =========================================================================
    elements.append(Spacer(1, 2*inch))
    elements.append(Paragraph("Taleemabad", title_style))
    elements.append(Paragraph("Financial Model Report", title_style))
    elements.append(Spacer(1, 0.5*inch))
    elements.append(Paragraph("Budget 2026 Analysis", subtitle_style))
    elements.append(Paragraph(
        f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}",
        subtitle_style
    ))
    elements.append(Spacer(1, 1*inch))
    elements.append(Paragraph(
        "Source: Budget 2026 v2.0 Draft Baseline Internal",
        body_style
    ))
    elements.append(PageBreak())

    # =========================================================================
    # Executive Summary
    # =========================================================================
    elements.append(Paragraph("Executive Summary", section_style))

    opening = custom_assumptions.get('opening_balance', 723248)
    year_end = cashflow_model.get_year_end_position()
    runway = year_end / cashflow_model.get_average_monthly_burn()

    summary_text = f"""
    The financial model projects a year-end surplus of <b>${year_end:,.0f}</b> based on
    total inflows of <b>${cashflow_model.get_total_inflows():,.0f}</b> and total expenses
    of <b>${cashflow_model.get_total_outflows():,.0f}</b>. Starting with an opening balance
    of <b>${opening:,.0f}</b>, Taleemabad maintains healthy cash position throughout 2026
    with <b>{runway:.1f} months</b> of runway at year-end.
    """
    elements.append(Paragraph(summary_text.strip(), body_style))
    elements.append(Spacer(1, 0.3*inch))

    # Key Metrics Table
    elements.append(Paragraph("Key Metrics", section_style))

    metrics_data = [
        ['Metric', 'Value'],
        ['Opening Balance (Jan 1, 2026)', f'${opening:,.0f}'],
        ['Total Inflows', f'${cashflow_model.get_total_inflows():,.0f}'],
        ['Total Expenses', f'${cashflow_model.get_total_outflows():,.0f}'],
        ['Net Cash Flow', f'${cashflow_model.get_net_cash_flow():,.0f}'],
        ['Year-End Surplus', f'${year_end:,.0f}'],
        ['Runway at Year-End', f'{runway:.1f} months'],
        ['Average Monthly Burn', f'${cashflow_model.get_average_monthly_burn():,.0f}'],
    ]

    metrics_table = Table(metrics_data, colWidths=[3.5*inch, 2*inch])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
    ]))
    elements.append(metrics_table)
    elements.append(Spacer(1, 0.3*inch))

    # =========================================================================
    # Scenario Analysis
    # =========================================================================
    elements.append(Paragraph("Scenario Analysis", section_style))

    scenario_model.run_all_scenarios()
    comparison = scenario_model.compare_scenarios()

    scenario_text = """
    Three scenarios have been modeled: Base Case (current budget), Optimistic (+20% revenue,
    -10% expenses), and Pessimistic (-30% revenue, +15% expenses).
    """
    elements.append(Paragraph(scenario_text.strip(), body_style))
    elements.append(Spacer(1, 0.2*inch))

    scenario_data = [['Scenario', 'Year-End Surplus', 'Runway']]
    for name, data in comparison.items():
        scenario_data.append([
            name,
            f'${data["year_end_surplus"]:,.0f}',
            f'{data["runway_months"]:.1f} months'
        ])

    scenario_table = Table(scenario_data, colWidths=[3*inch, 1.8*inch, 1.5*inch])
    scenario_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
    ]))
    elements.append(scenario_table)
    elements.append(Spacer(1, 0.3*inch))

    # =========================================================================
    # Grant Dependency
    # =========================================================================
    elements.append(Paragraph("Grant Dependency Analysis", section_style))

    grant_analysis = sensitivity_model.analyze_grant_dependency()

    grant_text = """
    Analysis of grant concentration risk. Grants marked as "Critical" would result in
    a negative year-end surplus if not received.
    """
    elements.append(Paragraph(grant_text.strip(), body_style))
    elements.append(Spacer(1, 0.2*inch))

    grant_data = [['Grant', 'Amount', '% of Total', 'Critical']]
    for name, data in grant_analysis.items():
        grant_data.append([
            name.replace('_', ' ').title(),
            f'${data["grant_amount"]:,.0f}',
            f'{data["percentage_of_total"]:.1f}%',
            'Yes' if data['critical'] else 'No'
        ])

    grant_table = Table(grant_data, colWidths=[2.5*inch, 1.5*inch, 1.2*inch, 1*inch])
    grant_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (3, 0), (3, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
    ]))
    elements.append(grant_table)
    elements.append(Spacer(1, 0.3*inch))

    # =========================================================================
    # Footer
    # =========================================================================
    elements.append(Spacer(1, 0.5*inch))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#9CA3AF'),
        alignment=TA_CENTER,
    )
    elements.append(Paragraph(
        "Taleemabad Financial Model | Data Source: Budget 2026 v2.0 Draft Baseline Internal | "
        "All figures from budget PDF only",
        footer_style
    ))

    # Build PDF
    doc.build(elements)
    return output.getvalue()
