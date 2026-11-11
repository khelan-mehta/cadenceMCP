"""IEEE two-column conference-style report for the gpdk090 Widlar current mirror.
Mirrors the structure of the reference report (Vaghela/Raiyani) with this
project's own measured results and Cadence screenshots."""
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                Spacer, Image, Table, TableStyle, KeepTogether,
                                FrameBreak, NextPageTemplate)
from PIL import Image as PILImage

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))),
                   "Widlar_IEEE_Report_Mangal_Mehta.pdf")
OUT = r"C:\Users\NG\Desktop\cadence MCP\Widlar_IEEE_Report_Mangal_Mehta.pdf"

PAGE_W, PAGE_H = letter
MARGIN = 0.75 * inch
COL_GAP = 0.25 * inch
COL_W = (PAGE_W - 2 * MARGIN - COL_GAP) / 2
TITLE_H = 1.55 * inch

# ---------- styles ----------
S = {}
S["title"] = ParagraphStyle("title", fontName="Times-Roman", fontSize=17.5,
                            leading=21, alignment=TA_CENTER, spaceAfter=10)
S["author"] = ParagraphStyle("author", fontName="Times-Roman", fontSize=11,
                             leading=13, alignment=TA_CENTER)
S["affil"] = ParagraphStyle("affil", fontName="Times-Roman", fontSize=10,
                            leading=12, alignment=TA_CENTER)
S["abstract"] = ParagraphStyle("abstract", fontName="Times-Bold", fontSize=9,
                               leading=10.8, alignment=TA_JUSTIFY, spaceAfter=6)
S["body"] = ParagraphStyle("body", fontName="Times-Roman", fontSize=10,
                           leading=11.8, alignment=TA_JUSTIFY, firstLineIndent=10)
S["bodyni"] = ParagraphStyle("bodyni", parent=S["body"], firstLineIndent=0)
S["sec"] = ParagraphStyle("sec", fontName="Times-Roman", fontSize=10, leading=12,
                          alignment=TA_CENTER, spaceBefore=10, spaceAfter=5)
S["subsec"] = ParagraphStyle("subsec", fontName="Times-Italic", fontSize=10,
                             leading=12, alignment=TA_LEFT, spaceBefore=7, spaceAfter=3)
S["caption"] = ParagraphStyle("caption", fontName="Times-Roman", fontSize=8.5,
                              leading=10, alignment=TA_LEFT, spaceBefore=3, spaceAfter=8)
S["tabcap"] = ParagraphStyle("tabcap", fontName="Times-Roman", fontSize=8.5,
                             leading=10, alignment=TA_CENTER, spaceBefore=2, spaceAfter=3)
S["ref"] = ParagraphStyle("ref", fontName="Times-Roman", fontSize=9, leading=10.6,
                          alignment=TA_JUSTIFY, leftIndent=14, firstLineIndent=-14,
                          spaceAfter=2)

def sc(txt):
    """Poor man's small caps for headings."""
    return txt.upper()

def fig(path, caption, width=COL_W):
    im = PILImage.open(path)
    w, h = im.size
    draw_w = width
    draw_h = h * draw_w / w
    return KeepTogether([Image(path, width=draw_w, height=draw_h),
                         Paragraph(caption, S["caption"])])

def ieee_table(title_lines, data, colw=None):
    t = Table(data, colWidths=colw, hAlign="CENTER")
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Times-Roman"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("LEADING", (0, 0), (-1, -1), 10),
        ("LINEABOVE", (0, 0), (-1, 0), 0.8, colors.black),
        ("LINEBELOW", (0, 0), (-1, 0), 0.4, colors.black),
        ("LINEBELOW", (0, -1), (-1, -1), 0.8, colors.black),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    parts = [Paragraph(l, S["tabcap"]) for l in title_lines]
    return KeepTogether(parts + [t, Spacer(1, 6)])

# ---------- document ----------
doc = BaseDocTemplate(OUT, pagesize=letter, leftMargin=MARGIN, rightMargin=MARGIN,
                      topMargin=MARGIN, bottomMargin=MARGIN,
                      title="Design, Simulation and Physical Verification of a "
                            "MOSFET-Based Widlar Current Mirror",
                      author="Kartik Mangal, Khelan Mehta")
frame_title = Frame(MARGIN, PAGE_H - MARGIN - TITLE_H, PAGE_W - 2 * MARGIN, TITLE_H,
                    id="title", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
def col_frames(top_y):
    h = top_y - MARGIN
    return [Frame(MARGIN, MARGIN, COL_W, h, id="c1",
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0),
            Frame(MARGIN + COL_W + COL_GAP, MARGIN, COL_W, h, id="c2",
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)]
first = PageTemplate(id="first", frames=[frame_title] + col_frames(PAGE_H - MARGIN - TITLE_H - 8))
rest = PageTemplate(id="rest", frames=col_frames(PAGE_H - MARGIN))

doc.addPageTemplates([first, rest])

E = []  # story

# ---------- title block ----------
E.append(Paragraph("Design, Simulation and Physical Verification of a<br/>"
                   "MOSFET-Based Widlar Current Mirror", S["title"]))
auth = Table([[Paragraph("Kartik Mangal (23BEC083)", S["author"]),
               Paragraph("Khelan Mehta (23BEC088)", S["author"])]],
             colWidths=[(PAGE_W - 2 * MARGIN) / 2] * 2)
auth.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 0),
                          ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
E.append(auth)
E.append(Paragraph("Department of Electronics and Communication Engineering<br/>"
                   "Institute of Technology<br/>"
                   "Academic Year 2026\u20132027, Semester VII", S["affil"]))
E.append(NextPageTemplate("rest"))
E.append(FrameBreak())

# ---------- abstract ----------
E.append(Paragraph(
    "<i>Abstract</i>\u2014This paper presents the design, simulation, layout and physical "
    "verification of an NMOS-based Widlar current mirror implemented in Cadence Virtuoso "
    "using the GPDK090 technology library. The circuit uses two equal NMOS transistors "
    "(W = 3.12 \u00b5m, L = 280 nm), a 100 \u00b5A reference current, a source-degeneration "
    "resistor realized as an on-chip non-salicided P+ polysilicon resistor, and a 1 M\u03a9 "
    "output load at a 1.8 V supply. The target output current is 1 \u00b5A. A square-law "
    "approximation gives an initial source resistance of approximately 204 k\u03a9; a DC "
    "parametric sweep against the BSIM3v3 technology models selects approximately "
    "271.0 k\u03a9, realized as a 28-segment, 677.46 \u00b5m serpentine poly resistor of "
    "270.98 k\u03a9. The simulated output current is 999.97 nA (0.003% error). A full custom "
    "layout of the mirror was drawn, passing Diva DRC with zero errors and Diva LVS with a "
    "clean match against the schematic. The gap between the hand calculation and simulation, "
    "and the additional constraints imposed by physical design, highlight the importance of "
    "technology-model-based verification.", S["abstract"]))
E.append(Paragraph(
    "<i>Index Terms</i>\u2014Widlar current mirror, MOSFET, current reference, analog "
    "integrated circuits, Cadence Virtuoso, GPDK090, DRC, LVS.", S["abstract"]))

# ---------- I. Introduction ----------
E.append(Paragraph(sc("I. Introduction"), S["sec"]))
E.append(Paragraph(
    "Current mirrors are widely used in analog integrated circuits to establish bias "
    "currents for amplifiers and other circuit blocks. In a basic MOS current mirror, a "
    "diode-connected reference transistor establishes a gate\u2013source voltage that is "
    "applied to an output transistor. With matched devices, the output current is related "
    "to the reference current through the transistor aspect ratios [1], [2].", S["body"]))
E.append(Paragraph(
    "Generating a current much smaller than the reference ideally requires either a very "
    "large device-ratio difference or additional circuitry. The Widlar principle introduces "
    "a resistor in the source of the output device, creating a source voltage that reduces "
    "the output transistor's effective gate\u2013source voltage and therefore its current. "
    "The original Widlar circuit was introduced as a low-value bipolar current source; the "
    "same source-degeneration principle applies to MOSFETs [1], [3].", S["body"]))
E.append(Paragraph(
    "The objective of this work is to design an NMOS Widlar mirror that derives 1 \u00b5A "
    "from a 100 \u00b5A reference, to verify it against the GPDK090 technology models, and "
    "\u2014 going beyond schematic-level study \u2014 to carry the circuit through analog "
    "layout, DRC and LVS so that the drawn silicon is proven equivalent to the simulated "
    "schematic.", S["body"]))

# ---------- II. Circuit configuration and design ----------
E.append(Paragraph(sc("II. Circuit Configuration and Design"), S["sec"]))
E.append(Paragraph("A. Topology and specifications", S["subsec"]))
E.append(Paragraph(
    "The circuit contains two NMOS transistors. M1 is diode-connected with its source "
    "grounded, and its gate drives the gate of M2. The source of M2 is returned to ground "
    "through the degeneration resistor R<sub>S</sub>. A 100 \u00b5A DC current source "
    "biases the diode-connected branch, while R<sub>Load</sub> = 1 M\u03a9 connects the "
    "output drain node to the 1.8 V supply. Both devices are gpdk090_nmos2v "
    "(thick-oxide) transistors with W = 3.12 \u00b5m and L = 280 nm. Unlike the ideal "
    "resistor commonly used in schematic exercises, R<sub>S</sub> here is the PDK "
    "polysilicon resistor resnsppoly (400 \u03a9/sq), so the same element can be drawn in "
    "layout. The design values are summarized in Table I.", S["body"]))
E.append(ieee_table(
    ["TABLE I", "D" + "esign Specifications".upper()],
    [["Parameter", "Value"],
     ["Supply voltage, VDD", "1.8 V"],
     ["Reference current, IREF", "100 \u00b5A"],
     ["Target output current, IOUT", "1 \u00b5A"],
     ["Transistor dimensions", "W = 3.12 \u00b5m, L = 280 nm"],
     ["Assumed VTH (hand calc)", "0.52 V"],
     ["Assumed \u00b5nCox (hand calc)", "350 \u00b5A/V\u00b2"],
     ["RS realization", "resnsppoly poly, 400 \u03a9/sq"],
     ["Load resistance, RLoad", "1 M\u03a9"]],
    colw=[1.9 * inch, 1.5 * inch]))
E.append(Paragraph("B. Analytical estimate of the source resistance", S["subsec"]))
E.append(Paragraph(
    "For an NMOS transistor in saturation the simplified square-law model gives "
    "V<sub>GS</sub> = V<sub>TH</sub> + (2I<sub>D</sub>/\u00b5<sub>n</sub>C<sub>ox</sub>"
    "(W/L))<super>1/2</super>. With W/L = 3.12/0.28 = 11.14, the reference branch gives "
    "V<sub>GS1</sub> = 0.52 + 0.226 = 0.746 V and the 1 \u00b5A branch gives "
    "V<sub>GS2</sub> = 0.52 + 0.023 = 0.543 V. Applying Ohm's law to R<sub>S</sub>:",
    S["body"]))
E.append(Paragraph(
    "R<sub>S</sub> \u2248 (V<sub>GS1</sub> \u2212 V<sub>GS2</sub>)/I<sub>OUT</sub> = "
    "(0.746 \u2212 0.543)/1 \u00b5A \u2248 204 k\u03a9.", S["bodyni"]))
E.append(Paragraph(
    "This is an initial estimate only: it neglects body effect on M2 (whose source sits "
    "above ground), subthreshold conduction, and short-channel effects, all of which are "
    "significant at a 100:1 current ratio.", S["body"]))

# ---------- III. Simulation methodology ----------
E.append(Paragraph(sc("III. Simulation Methodology"), S["sec"]))
E.append(Paragraph(
    "The schematic was implemented in Cadence Virtuoso 6.1.7 (Fig. 1) and simulated with "
    "Spectre using the GPDK090 BSIM3v3 models (NN corner). The DC operating point was "
    "examined; the source resistance was swept (150\u2013400 k\u03a9) to select the value "
    "that brings the output current to 1 \u00b5A; the poly-resistor length was swept to "
    "center the drawn geometry; a supply-voltage sweep, an output-compliance sweep and a "
    "100 \u00b5s transient analysis were also recorded. The 1 M\u03a9 load resistor was "
    "retained for all simulations shown.", S["body"]))
E.append(fig(os.path.join(HERE, "fig_sch.png"),
             "Fig. 1.  Cadence Virtuoso schematic with the DC operating point annotated. "
             "R<sub>S</sub> is the 28-segment resnsppoly resistor (r = 270.98 k\u03a9)."))

# ---------- IV. Results ----------
E.append(Paragraph(sc("IV. Results and Discussion"), S["sec"]))
E.append(Paragraph("A. Operating point", S["subsec"]))
E.append(Paragraph(
    "At the selected resistance the simulator reports I<sub>D</sub>(M2) = 1.00001 \u00b5A, "
    "V<sub>GS2</sub> = 569.70 mV, V<sub>DS2</sub> = 529.05 mV and g<sub>m2</sub> = "
    "23.81 \u00b5S; the source-node voltage is 270.98 mV and the current delivered to the "
    "load is 999.97 nA. M1 operates in strong-inversion saturation (V<sub>GS1</sub> = "
    "840.68 mV). Notably, the simulated V<sub>TH</sub> of M2 rises to 612 mV through the "
    "body effect, so the output device actually operates in moderate/weak inversion "
    "\u2014 exactly the regime where the square-law hand model fails.", S["body"]))
E.append(Paragraph("B. Source-resistance sweep", S["subsec"]))
E.append(Paragraph(
    "Fig. 2 shows the simulated output current as R<sub>S</sub> varies from 150 k\u03a9 to "
    "400 k\u03a9. The current falls monotonically with increasing resistance, consistent "
    "with the source-degeneration mechanism, and crosses the 1 \u00b5A target at "
    "R<sub>S</sub> \u2248 271.0 k\u03a9. Table II lists the output current at selected "
    "resistances for cross-checking the curve.", S["body"]))
E.append(fig(os.path.join(HERE, "fig_swrs.png"),
             "Fig. 2.  DC sweep of output current versus source resistance (ViVA). The "
             "1 \u00b5A target is reached at R<sub>S</sub> \u2248 271.0 k\u03a9."))
E.append(ieee_table(
    ["TABLE II", "OUTPUT CURRENT AT SELECTED SOURCE RESISTANCES"],
    [["RS (k\u03a9)", "IOUT (\u00b5A)"],
     ["200", "1.249171"],
     ["225", "1.147868"],
     ["250", "1.062244"],
     ["275", "0.988911"],
     ["300", "0.925380"],
     ["325", "0.869789"],
     ["350", "0.820722"]],
    colw=[1.1 * inch, 1.3 * inch]))
E.append(Paragraph(
    "The selected resistance is about 33% greater than the 204 k\u03a9 analytical "
    "estimate. The discrepancy reflects the difference between the simplified hand model "
    "and the technology-model simulation \u2014 chiefly the body effect and the "
    "moderate-inversion operation of M2. The drawn resistor (28 series segments of "
    "24.195 \u00b5m \u00d7 1 \u00b5m at 400 \u03a9/sq, total 677.46 \u00b5m, 270.98 "
    "k\u03a9) was centered by a separate sweep of the poly length, which places the "
    "1 \u00b5A point at 677.44 \u00b5m \u2014 within 0.003% of the drawn value.", S["body"]))
E.append(Paragraph("C. Supply-voltage sweep", S["subsec"]))
E.append(Paragraph(
    "Fig. 3 shows the DC response as the supply is swept from 0 V to 1.8 V: the output "
    "current (upper trace) is established once sufficient headroom exists, while the "
    "supply current (lower trace) is dominated by the \u2248100 \u00b5A reference branch. "
    "The output branch requires adequate supply voltage before the intended current is "
    "established.", S["body"]))
E.append(fig(os.path.join(HERE, "fig_swvdd.png"),
             "Fig. 3.  DC response during the supply-voltage sweep; upper trace is "
             "I<sub>OUT</sub>, lower trace the supply-source current."))
E.append(Paragraph("D. Output compliance", S["subsec"]))
E.append(Paragraph(
    "Replacing the load with a swept voltage source characterizes the mirror as a current "
    "source (Fig. 4). The output current saturates at \u22480.9 \u00b5A once "
    "V<sub>OUT</sub> exceeds about 0.3 V and rises gently to 1.18 \u00b5A at 1.8 V, "
    "showing the finite output resistance of the simple Widlar stage. For \u00b110% "
    "current accuracy the output node must be held above roughly 0.3 V.", S["body"]))
E.append(fig(os.path.join(HERE, "fig_vout.png"),
             "Fig. 4.  I<sub>D</sub>(M2) versus swept output voltage \u2014 output "
             "compliance of the mirror."))
E.append(Paragraph("E. Transient behaviour", S["subsec"]))
E.append(Paragraph(
    "A 100 \u00b5s transient at the operating point (Fig. 5) shows the output current "
    "steady at 999.9745 nA with sub-5 pA numerical ripple, i.e. a stable DC current with "
    "no start-up anomaly in this configuration.", S["body"]))
E.append(fig(os.path.join(HERE, "fig_tran.png"),
             "Fig. 5.  Transient response of the output current over 100 \u00b5s."))

# ---------- V. Layout ----------
E.append(Paragraph(sc("V. Layout and Physical Verification"), S["sec"]))
E.append(Paragraph(
    "The mirror core (M1, M2, R<sub>S</sub>) was laid out in Metal1 in a \u224848 \u00d7 "
    "37 \u00b5m area (Fig. 6), dominated as expected by the 270.98 k\u03a9 serpentine "
    "poly resistor. M1 and M2 are single-finger nmos2v pcells with top gate straps "
    "(Fig. 7). M1 uses the pcell's integrated body tie \u2014 permissible only because "
    "its source and bulk are both grounded, as the integrated tie shorts S to B. M2, "
    "whose source sits 271 mV above ground, uses no local tap; its bulk is the common "
    "substrate, tied to ground by the taps of M1 and of the resistor. The resistor "
    "carries its own substrate-tap strip, required by the DRC substrate-stamping rule "
    "for its Psub region. The NS net (M2 source to R<sub>S</sub>) is routed down the "
    "right edge and enters the resistor's PLUS terminal from below the pad row, keeping "
    "it clear of every ground shape.", S["body"]))
E.append(fig(os.path.join(HERE, "fig_layf.png"),
             "Fig. 6.  Complete layout: mirror pair (top left) above the 28-segment "
             "serpentine resnsppoly resistor; common ground rail and right-edge NS "
             "routing."))
E.append(fig(os.path.join(HERE, "fig_laym.png"),
             "Fig. 7.  Detail of the transistor row: M1 (left, with integrated tap) and "
             "M2, gate straps, and the IREF / IOUT / GND Metal1 routing."))
E.append(Paragraph(
    "Physical verification used the Diva decks shipped with GPDK090. DRC reports zero "
    "errors. Layout extraction recognizes 2 nmos2v and 28 resnsppoly devices, all well "
    "formed. LVS compares the extracted view against the schematic: the rule deck's "
    "series-resistor permutation merges the 28 drawn segments into the single 677.46 "
    "\u00b5m schematic resistor, and the netlists match with zero unmatched instances, "
    "nets or terminals and zero size errors (Table III). The layout is therefore "
    "electrically identical to the simulated circuit; at DC the residual layout "
    "parasitic is \u224887 \u03a9 of Metal1 trace resistance in series with 271 k\u03a9, "
    "a 0.03% effect.", S["body"]))
E.append(ieee_table(
    ["TABLE III", "PHYSICAL VERIFICATION SUMMARY"],
    [["Check", "Result"],
     ["Diva DRC", "0 errors"],
     ["Extraction", "2 nmos2v + 28 resnsppoly, 0 errors"],
     ["LVS devices", "30 vs 3 after series merge \u2014 matched"],
     ["LVS verdict", "\u201cThe net-lists match\u201d, 0 size errors"]],
    colw=[1.2 * inch, 2.2 * inch]))

# ---------- VI/VII ----------
E.append(Paragraph(sc("VI. Advantages, Limitations, and Applications"), S["sec"]))
E.append(Paragraph(
    "The source resistor provides a simple means of generating a small, stable bias "
    "current without extreme device ratios, which is useful in low-current biasing "
    "networks [1], [2]. Its accuracy depends on the transistor models, the resistor "
    "value and temperature coefficient, the available output voltage, and device "
    "mismatch. The resistor dominates the silicon area \u2014 here about 95% of the "
    "cell \u2014 and consumes voltage headroom; the output current departs from target "
    "when the output transistor lacks adequate drain voltage, as quantified by the "
    "compliance sweep of Fig. 4. Process variation of the poly sheet resistance "
    "(\u00b120% across corners) translates directly into output-current variation, a "
    "consideration absent from ideal-resistor exercises.", S["body"]))
E.append(Paragraph(sc("VII. Conclusion"), S["sec"]))
E.append(Paragraph(
    "An NMOS Widlar current mirror producing 999.97 nA from a 100 \u00b5A reference at "
    "1.8 V was designed in Cadence Virtuoso with the GPDK090 library. The square-law "
    "hand calculation gave R<sub>S</sub> \u2248 204 k\u03a9, while the "
    "technology-model sweep selected 271.0 k\u03a9 \u2014 a 33% correction dominated by "
    "body effect and moderate-inversion operation of the output device. The resistor "
    "was realized as an on-chip 28-segment poly serpentine, and the complete cell was "
    "carried through layout, DRC (clean) and LVS (matched). The exercise demonstrates "
    "both the value of analytical estimates refined by simulation with the intended "
    "technology models, and the additional constraints \u2014 body ties, substrate "
    "stamping, routing topology \u2014 that only appear at the physical-design stage.",
    S["body"]))

# ---------- References ----------
E.append(Paragraph(sc("References"), S["sec"]))
E.append(Paragraph(
    "[1]\u2002R. J. Widlar, \u201cLow-Value Current Source for Integrated Circuits,\u201d "
    "U.S. Patent 3,320,439, May 16, 1967. [Online]. Available: "
    "https://patents.google.com/patent/US3320439A/en", S["ref"]))
E.append(Paragraph(
    "[2]\u2002Analog Devices, \u201cChapter 11: The Current Mirror,\u201d Analog Devices "
    "Wiki, section on the Widlar current source. [Online]. Available: "
    "https://wiki.analog.com/university/courses/electronics/text/chapter-11", S["ref"]))
E.append(Paragraph(
    "[3]\u2002P. R. Gray, P. J. Hurst, S. H. Lewis, and R. G. Meyer, Analysis and Design "
    "of Analog Integrated Circuits, 5th ed. Hoboken, NJ, USA: Wiley, 2009.", S["ref"]))

doc.build(E)
print("written:", OUT)
