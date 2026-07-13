"""Generate a concise executive intelligence brief in PDF format."""
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, Image, PageBreak, KeepTogether)
import pandas as pd

NAVY = colors.HexColor("#15324B"); TEAL = colors.HexColor("#16817A"); PALE = colors.HexColor("#EAF2F4")


def _fmt_m(value): return f"{float(value)/1e6:,.1f}M"
def _fmt_b(value): return f"${float(value)/1e9:,.2f}B"


def _header_footer(canvas, doc):
    canvas.saveState(); w, h = letter
    canvas.setFillColor(NAVY); canvas.rect(0, h-34, w, 34, fill=1, stroke=0)
    canvas.setFillColor(colors.white); canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(0.65*inch, h-22, "GLOBAL DIAMOND SUPPLY & VALUE INTELLIGENCE")
    canvas.setFillColor(colors.HexColor("#607080")); canvas.setFont("Helvetica", 8)
    canvas.drawRightString(w-0.65*inch, 24, f"Page {doc.page}")
    canvas.restoreState()


def generate_pdf_report(root: Path, annual: pd.DataFrame, forecast: pd.DataFrame,
                        trade: pd.DataFrame, coverage: pd.DataFrame,
                        governance: dict | None) -> Path:
    out = root / "output" / "pdf"; out.mkdir(parents=True, exist_ok=True)
    path = out / "diamond_supply_value_intelligence_brief.pdf"
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Title2", parent=styles["Title"], textColor=NAVY, fontSize=23, leading=27, spaceAfter=12))
    styles.add(ParagraphStyle(name="Kicker", parent=styles["Normal"], textColor=TEAL, fontSize=9, leading=12, spaceAfter=6))
    styles.add(ParagraphStyle(name="Section2", parent=styles["Heading2"], textColor=NAVY, fontSize=15, leading=18, spaceBefore=8, spaceAfter=8))
    styles.add(ParagraphStyle(name="Small2", parent=styles["Normal"], fontSize=8, leading=11, textColor=colors.HexColor("#4B5963")))
    doc = SimpleDocTemplate(str(path), pagesize=letter, rightMargin=.65*inch, leftMargin=.65*inch,
                            topMargin=.65*inch, bottomMargin=.55*inch, title="Diamond Supply and Value Intelligence Brief")
    latest = annual.sort_values("year").iloc[-1]
    confidence = governance["forecast_confidence_score"] if governance else 0
    story = [Spacer(1, .22*inch), Paragraph("INTELLIGENCE BRIEF", styles["Kicker"]),
             Paragraph("Global Diamond Supply<br/>& Value Intelligence", styles["Title2"]),
             Paragraph(f"Official baseline through {int(latest.year)} | Producer-calibrated outlook to 2026", styles["Normal"]), Spacer(1,.22*inch)]
    metrics = [["Official production", "Value pressure", "2026 median", "Confidence"],
               [f"{latest.production_mct:.1f}M ct", f"{latest.value_pressure_index:.1f}/100",
                _fmt_m(forecast.loc[forecast.year==2026,"production_carats_p50"].iloc[0]) if not forecast.empty else "N/A",
                f"{confidence:.1f}/100"]]
    t = Table(metrics, colWidths=[1.65*inch]*4, rowHeights=[.34*inch,.48*inch])
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),NAVY),("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("BACKGROUND",(0,1),(-1,1),PALE),("TEXTCOLOR",(0,1),(-1,1),NAVY),("ALIGN",(0,0),(-1,-1),"CENTER"),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),
        ("LEFTPADDING",(0,0),(-1,-1),4),("RIGHTPADDING",(0,0),(-1,-1),4),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTNAME",(0,1),(-1,1),"Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,0),8),("FONTSIZE",(0,1),(-1,1),13),("LEADING",(0,1),(-1,1),15),
        ("GRID",(0,0),(-1,-1),.25,colors.white)]))
    story += [t, Spacer(1,.22*inch), Paragraph("Executive assessment", styles["Section2"]),
        Paragraph("The model combines Kimberley Process production, UN Comtrade flows, verified producer disclosures and transparent scenario assumptions. Current results indicate restrained value pressure and a 2026 production range that remains sensitive to producer discipline, mine closures, ramp-ups and downstream demand.", styles["BodyText"])]
    if not forecast.empty:
        rows = [["Class","Year","P10","Median","P90"]]
        for r in forecast.itertuples(): rows.append([r.classification.replace("_"," "),str(int(r.year)),_fmt_m(r.production_carats_p10),_fmt_m(r.production_carats_p50),_fmt_m(r.production_carats_p90)])
        ft=Table(rows,colWidths=[2.05*inch,.65*inch,1.1*inch,1.1*inch,1.1*inch],repeatRows=1)
        ft.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),TEAL),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8),("GRID",(0,0),(-1,-1),.25,colors.HexColor("#B7C6CC")),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,PALE]),("ALIGN",(1,1),(-1,-1),"RIGHT"),("VALIGN",(0,0),(-1,-1),"MIDDLE")]))
        story += [Spacer(1,.18*inch),Paragraph("Production outlook",styles["Section2"]),ft]
    chart = root / "outputs" / "charts" / "production_forecast.png"
    if chart.exists(): story += [Spacer(1,.16*inch),Image(str(chart),width=6.65*inch,height=3.7*inch)]
    story += [PageBreak(),Paragraph("Trade coverage and evidence",styles["Section2"])]
    available = int((coverage.coverage_status=="available").sum()) if not coverage.empty else 0
    story += [Paragraph(f"UN Comtrade coverage: <b>{available}/{len(coverage)}</b> requested reporter-year combinations available. Missing and no-data combinations are not treated as zero trade.",styles["BodyText"])]
    tradechart=root/"outputs"/"charts"/"diamond_trade_segments.png"
    if tradechart.exists(): story += [Spacer(1,.12*inch),Image(str(tradechart),width=6.65*inch,height=3.7*inch)]
    story += [Paragraph("Governance and limitations",styles["Section2"]),
        Paragraph("Forecast confidence is a governed coverage score, not a probability of correctness. Full-year verified producer actuals are fixed; quarterly observations and secondary evidence are excluded from annual calibration. Aggregate dollars per carat are mix-sensitive proxies and not gemological appraisals or tradable spot prices.",styles["BodyText"]),
        Spacer(1,.15*inch),Paragraph("Classification",styles["Section2"])]
    class_rows=[["Label","Meaning"],["Official actual","Kimberley Process or official trade observation"],["Preliminary estimate","Observed producer actuals plus modeled residual market"],["Forecast","Guidance-calibrated probabilistic projection"],["Scenario","Conditional analytical case, not a prediction"]]
    ct=Table(class_rows,colWidths=[1.55*inch,5.05*inch],repeatRows=1)
    ct.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),NAVY),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8),("GRID",(0,0),(-1,-1),.25,colors.HexColor("#B7C6CC")),("VALIGN",(0,0),(-1,-1),"TOP"),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,PALE])]))
    story += [ct,Spacer(1,.2*inch),Paragraph("For research and decision support only. Not investment advice.",styles["Small2"])]
    doc.build(story,onFirstPage=_header_footer,onLaterPages=_header_footer)
    return path
