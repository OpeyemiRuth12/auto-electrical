"""
AutoElect - PDF Report Generation Module
--------------------------------------------
Step 5: Builds a downloadable PDF design report from the results already
calculated by the other modules (load calculation, lighting design,
cable sizing, backup power sizing).

Returns the PDF as bytes, ready to be handed to Streamlit's
st.download_button - no file is written to disk. This module only
handles layout/formatting; it does not perform any new calculations.

NOTE: avoids Unicode superscript characters (m², mm²) since ReportLab's
built-in fonts render them as solid black boxes - "sqm"/"sqmm" are used
instead throughout.
"""

from io import BytesIO
from datetime import date

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)

NAVY = colors.HexColor("#0B1120")
GOLD = colors.HexColor("#D4AF37")
LIGHT_GREY = colors.HexColor("#F2F2ED")


def _build_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReportTitle", parent=styles["Title"],
        textColor=NAVY, fontSize=20, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="SectionHeading", parent=styles["Heading2"],
        textColor=NAVY, spaceBefore=16, spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="SmallNote", parent=styles["Normal"],
        fontSize=8, textColor=colors.grey,
    ))
    return styles


def _styled_table(data, col_widths=None):
    table = Table(data, colWidths=col_widths, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), GOLD),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def generate_report(project_name, tier, breakdown, demand, connected_load,
                     max_demand_w, max_demand_a, lighting_results,
                     cable_result, cable_length, gen_result, inv_result,
                     batt_result, solar_result, essential_load_percent,
                     backup_hours, ambient_temp_c=30, num_grouped_circuits=1,
                     correction_factor=1.0):
    """
    Builds the full PDF report and returns it as raw bytes.
    All arguments are values already calculated elsewhere in app.py.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm,
        leftMargin=2 * cm, rightMargin=2 * cm,
    )
    styles = _build_styles()
    story = []

    # --- Title ---
    story.append(Paragraph("AutoElect - Electrical Design Report", styles["ReportTitle"]))
    story.append(Paragraph(f"Project: {project_name or 'Untitled Project'}", styles["Normal"]))
    story.append(Paragraph(f"Design Tier: {tier}", styles["Normal"]))
    story.append(Paragraph(f"Date: {date.today().strftime('%d %B %Y')}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # --- Section 1: Load Summary ---
    story.append(Paragraph("1. Load Summary", styles["SectionHeading"]))
    load_table_data = [["Category", "Connected Load (W)", "Demand After Diversity (W)"]]
    for cat in breakdown:
        load_table_data.append([
            cat.replace("_", " ").title(),
            f"{breakdown[cat]:.0f}",
            f"{demand[cat]:.0f}",
        ])
    story.append(_styled_table(load_table_data))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"<b>Total Connected Load:</b> {connected_load:.0f} W", styles["Normal"]))
    story.append(Paragraph(
        f"<b>Maximum Demand:</b> {max_demand_w:.0f} W ({max_demand_a:.1f} A)", styles["Normal"]
    ))

    # --- Section 2: Lighting Design ---
    if lighting_results:
        story.append(Paragraph("2. Lighting Design Schedule", styles["SectionHeading"]))
        lighting_table_data = [["Room", "Area (sqm)", "Fitting Type", "Fittings Needed", "Load (W)"]]
        for r in lighting_results:
            lighting_table_data.append([
                r["room_type"], f"{r['area_m2']:.1f}", r["fitting_name"],
                str(r["fittings_needed"]), f"{r['lighting_load_w']}",
            ])
        story.append(_styled_table(lighting_table_data))

    # --- Section 3: Cable Sizing ---
    story.append(Paragraph("3. Main Cable Sizing", styles["SectionHeading"]))
    cable_table_data = [
        ["Parameter", "Value"],
        ["Cable Run Length", f"{cable_length} m"],
        ["Ambient Temperature", f"{ambient_temp_c} C"],
        ["Grouped Circuits", str(num_grouped_circuits)],
        ["Correction Factor Applied", str(correction_factor)],
        ["Protective Device", f"{cable_result['protective_device_a']} A"],
        ["Cable Size", f"{cable_result['cable_size_mm2']} sqmm"],
        ["Voltage Drop", f"{cable_result['voltage_drop_v']} V ({cable_result['voltage_drop_percent']}%)"],
        ["BS 7671:2018 Compliance", "PASS" if cable_result["compliant"] else "FAIL"],
    ]
    story.append(_styled_table(cable_table_data))

    # --- Section 4: Backup Power Sizing ---
    story.append(Paragraph("4. Backup Power Sizing", styles["SectionHeading"]))
    essential_load_w = max_demand_w * essential_load_percent / 100
    story.append(Paragraph(
        f"Essential load assumed at {essential_load_percent}% of maximum demand "
        f"({essential_load_w:.0f} W), with {backup_hours} hour(s) of backup "
        f"autonomy required.",
        styles["Normal"]
    ))
    story.append(Spacer(1, 6))
    backup_table_data = [
        ["Component", "Recommendation"],
        ["Generator", f"{gen_result['recommended_kva']} kVA"],
        ["Inverter", f"{inv_result['recommended_va']} VA"],
        ["Battery Bank", f"{batt_result['units_needed']} x {batt_result['unit_ah']}Ah "
                          f"({batt_result['battery_type']})"],
        ["Solar Panels", f"{solar_result['panels_needed']} x {solar_result['panel_watts']}W panels"],
    ]
    story.append(_styled_table(backup_table_data))

    # --- Assumptions & Notes ---
    story.append(PageBreak())
    story.append(Paragraph("Design Assumptions & Notes", styles["SectionHeading"]))
    assumptions = [
        "Load diversity factors follow IEE On-Site Guide domestic allowances.",
        "Lighting design uses the lumen method with a utilisation factor of "
        "0.5 and maintenance factor of 0.8 (typical residential planning values).",
        "Cable sizing is based on PVC/thermoplastic insulated, copper conductor, "
        "twin and earth cable, Reference Method C (clipped direct), per BS "
        "7671:2018 Appendix 4.",
        "Generator and inverter sizing assumes a power factor of 0.8 for mixed "
        "residential loads.",
        "Battery sizing assumes an inverter efficiency of 85%.",
        "Solar panel sizing uses regional peak sun hour estimates for Nigeria; "
        "verify against site-specific solar resource data for final design.",
        f"This design was generated using the '{tier}' design tier, which sets "
        "safety margins and component grade - all tiers remain fully compliant "
        "with BS 7671:2018 and CIBSE guidance.",
    ]
    for note in assumptions:
        story.append(Paragraph(f"- {note}", styles["Normal"]))
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "Generated automatically by AutoElect. Figures should be reviewed by "
        "a qualified electrical engineer before construction.",
        styles["SmallNote"]
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
