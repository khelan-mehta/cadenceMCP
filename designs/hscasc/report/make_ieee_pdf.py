"""IEEE two-column report: High-Swing Cascode Current Mirror (Somya Bhura)."""
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
OUT = r"C:\Users\NG\Desktop\cadence MCP\HighSwingCascode_IEEE_Report_Bhura.pdf"

PAGE_W, PAGE_H = letter
MARGIN = 0.75 * inch
COL_GAP = 0.25 * inch
COL_W = (PAGE_W - 2 * MARGIN - COL_GAP) / 2
TITLE_H = 1.45 * inch

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

def fig(path, caption, width=COL_W):
    im = PILImage.open(path); w, h = im.size
    return KeepTogether([Image(path, width=width, height=h * width / w),
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
    return KeepTogether([Paragraph(l, S["tabcap"]) for l in title_lines] + [t, Spacer(1, 6)])

doc = BaseDocTemplate(OUT, pagesize=letter, leftMargin=MARGIN, rightMargin=MARGIN,
                      topMargin=MARGIN, bottomMargin=MARGIN,
                      title="Design and Simulation of a High-Swing Cascode Current Mirror",
                      author="Somya Bhura")
frame_title = Frame(MARGIN, PAGE_H - MARGIN - TITLE_H, PAGE_W - 2 * MARGIN, TITLE_H,
                    id="title", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
def col_frames(top_y):
    h = top_y - MARGIN
    return [Frame(MARGIN, MARGIN, COL_W, h, id="c1", leftPadding=0, rightPadding=0,
                  topPadding=0, bottomPadding=0),
            Frame(MARGIN + COL_W + COL_GAP, MARGIN, COL_W, h, id="c2", leftPadding=0,
                  rightPadding=0, topPadding=0, bottomPadding=0)]
doc.addPageTemplates([PageTemplate(id="first", frames=[frame_title] + col_frames(PAGE_H - MARGIN - TITLE_H - 8)),
                      PageTemplate(id="rest", frames=col_frames(PAGE_H - MARGIN))])

E = []
E.append(Paragraph("Design, Simulation and Physical Verification of a<br/>"
                   "High-Swing Cascode Current Mirror", S["title"]))
E.append(Paragraph("Somya Bhura (23BEC187)", S["author"]))
E.append(Paragraph("Department of Electronics and Communication Engineering<br/>"
                   "Institute of Technology<br/>"
                   "Academic Year 2026\u20132027, Semester VII", S["affil"]))
E.append(NextPageTemplate("rest"))
E.append(FrameBreak())

E.append(Paragraph(
    "<i>Abstract</i>\u2014This paper presents the design and simulation of a high-swing "
    "(wide-swing) cascode current mirror that overcomes the low output resistance of a "
    "simple current mirror and the high voltage-headroom requirement of a conventional "
    "cascode mirror, while maintaining stable 100 \u00b5A operation at a 1.8 V supply. "
    "The circuit is implemented in Cadence Virtuoso with the GPDK090 library using five "
    "NMOS transistors (mirror devices W = 12 \u00b5m, L = 1 \u00b5m; bias device W = "
    "3 \u00b5m = W/4), with the cascode gates biased at V<sub>TH</sub> + 2V<sub>ov</sub> "
    "by the quarter-width diode device. Simulation shows an output current of "
    "100.06 \u00b5A, an output resistance of 1.57 M\u03a9 (13\u00d7 the simple mirror's "
    "0.12 M\u03a9), and 99% current compliance at only 0.44 V of output voltage \u2014 "
    "0.35 V less headroom than the conventional cascode's 0.79 V. A full custom layout "
    "was drawn and verified: Diva DRC reports zero errors and LVS matches the schematic "
    "exactly. A side-by-side sweep of all three mirror topologies quantifies the "
    "trade-offs.", S["abstract"]))
E.append(Paragraph(
    "<i>Index Terms</i>\u2014Cascode current mirror, wide-swing, high-swing, output "
    "resistance, voltage headroom, Cadence Virtuoso, GPDK090, DRC, LVS.", S["abstract"]))

E.append(Paragraph("I. INTRODUCTION", S["sec"]))
E.append(Paragraph(
    "A simple two-transistor current mirror has an output resistance of only "
    "r<sub>o</sub> = 1/\u03bb I<sub>D</sub>, so its output current varies appreciably "
    "with output voltage \u2014 a serious limitation when the mirror biases "
    "high-gain stages [1], [2]. Cascoding multiplies the output resistance by "
    "g<sub>m</sub>r<sub>o</sub>, but the conventional cascode connection, which biases "
    "the cascode gate from a stacked diode pair, wastes headroom: its minimum output "
    "voltage is V<sub>TH</sub> + 2V<sub>ov</sub>, a full threshold voltage more than "
    "the physical limit of two saturation voltages.", S["body"]))
E.append(Paragraph(
    "The high-swing (wide-swing) cascode mirror, attributed to Sooch [3], removes this "
    "waste. A separate bias device of width W/4 \u2014 carrying the same reference "
    "current at twice the overdrive \u2014 generates V<sub>B</sub> \u2248 V<sub>TH</sub> "
    "+ 2V<sub>ov</sub> for the cascode gates, while the mirror gates are driven from "
    "the input node. The bottom devices then sit at V<sub>DS</sub> \u2248 V<sub>ov</sub>, "
    "the edge of saturation, and the output complies down to about 2V<sub>ov</sub>. "
    "This work designs the circuit at 100 \u00b5A and 1.8 V in GPDK090, verifies it "
    "against the BSIM3v3 models, compares all three topologies in one simulation, and "
    "carries the design through layout, DRC and LVS.", S["body"]))

E.append(Paragraph("II. CIRCUIT CONFIGURATION AND DESIGN", S["sec"]))
E.append(Paragraph("A. Topology", S["subsec"]))
E.append(Paragraph(
    "The circuit (Fig. 1) contains five NMOS devices. M0 (W = 3 \u00b5m) is "
    "diode-connected and fed by I<sub>0</sub> = 100 \u00b5A; its gate voltage "
    "V<sub>B</sub> drives the gates of the cascode devices M3 and M4. The input branch "
    "stacks cascode M3 on mirror device M1; the gates of M1 and M2 are tied to the "
    "input node (the wide-swing connection), not to M1's drain. The output branch "
    "stacks M4 on M2. All mirror and cascode devices use W = 12 \u00b5m, L = 1 \u00b5m. "
    "The output is exercised by a swept/AC source V2.", S["body"]))
E.append(ieee_table(
    ["TABLE I", "DESIGN SPECIFICATIONS"],
    [["Parameter", "Value"],
     ["Supply voltage, VDD", "1.8 V"],
     ["Reference currents I0, I1", "100 \u00b5A each"],
     ["Mirror/cascode devices M1\u2013M4", "W = 12 \u00b5m, L = 1 \u00b5m"],
     ["Bias device M0", "W = 3 \u00b5m = W/4, L = 1 \u00b5m"],
     ["Technology", "GPDK090, nmos2v, BSIM3v3"],
     ["Output test source", "DC sweep + 100 mV, 1 kHz sine"]],
    colw=[2.0 * inch, 1.5 * inch]))
E.append(Paragraph("B. Bias design", S["subsec"]))
E.append(Paragraph(
    "With I<sub>D</sub> = \u00bd\u00b5<sub>n</sub>C<sub>ox</sub>(W/L)V<sub>ov</sub>"
    "<super>2</super>, quartering W at constant current doubles the overdrive. M0 "
    "therefore develops V<sub>GS0</sub> = V<sub>TH</sub> + 2V<sub>ov</sub>, which is "
    "exactly the cascode-gate bias that places the bottom devices at V<sub>DS</sub> = "
    "V<sub>B</sub> \u2212 V<sub>GS3</sub> \u2248 V<sub>ov</sub>. Simulation gives "
    "V<sub>B</sub> = 1.121 V, and the bottom devices indeed settle at V<sub>DS</sub> "
    "\u2248 0.251 V against V<sub>Dsat</sub> = 0.24 V \u2014 the edge of saturation, "
    "as intended. The ideal minimum output voltage is 2V<sub>ov</sub> \u2248 0.48 V, "
    "versus V<sub>TH</sub> + 2V<sub>ov</sub> \u2248 0.96 V for the conventional "
    "cascode.", S["body"]))
E.append(fig(os.path.join(HERE, "fig_sch.png"),
             "Fig. 1.  Cadence Virtuoso schematic with the simulated DC operating "
             "point annotated (V<sub>B</sub> = 1.121 V, node na = 251 mV, "
             "I<sub>OUT</sub> = 100.06 \u00b5A)."))

E.append(Paragraph("III. SIMULATION METHODOLOGY", S["sec"]))
E.append(Paragraph(
    "The schematic was simulated with Spectre (NN corner). The DC operating point was "
    "verified device by device; the output voltage was swept 0\u20131.8 V to measure "
    "compliance; an AC analysis on the output source measured the small-signal output "
    "impedance; a transient analysis applied a 100 mV, 1 kHz sine at the output; and "
    "the supply was swept 0\u20131.8 V. In a second deck, simple, conventional-cascode "
    "and high-swing mirrors \u2014 all from identical devices at 100 \u00b5A \u2014 "
    "share one swept output variable so the three compliance curves superimpose "
    "exactly (Fig. 2).", S["body"]))

E.append(Paragraph("IV. RESULTS AND DISCUSSION", S["sec"]))
E.append(Paragraph("A. Operating point", S["subsec"]))
E.append(Paragraph(
    "All five devices operate in saturation: M0 at V<sub>GS</sub> = 1.121 V "
    "(V<sub>ov</sub> = 0.645 V \u2248 2\u00d7 the mirror overdrive), M1/M2 at "
    "V<sub>GS</sub> = 811 mV with V<sub>DS</sub> \u2248 251 mV, and the cascodes at "
    "V<sub>GS</sub> \u2248 869 mV. The output current is 100.06 \u00b5A at "
    "V<sub>OUT</sub> = 0.9 V \u2014 a 0.06% mirroring error.", S["body"]))
E.append(Paragraph("B. Topology comparison", S["subsec"]))
E.append(fig(os.path.join(HERE, "fig_cmp.png"),
             "Fig. 2.  Output current vs output voltage for the simple mirror (red), "
             "conventional cascode (yellow) and high-swing cascode (green), all at "
             "100 \u00b5A. The high-swing curve is both flat and early."))
E.append(ieee_table(
    ["TABLE II", "MEASURED COMPARISON OF THE THREE TOPOLOGIES"],
    [["Metric", "Simple", "Conv. cascode", "High-swing"],
     ["VOUT for 95% IOUT", "0.31 V", "0.35 V", "0.34 V"],
     ["VOUT for 99% IOUT", "0.68 V", "0.79 V", "0.44 V"],
     ["Rout (slope 1\u20131.7 V)", "0.12 M\u03a9", "4.67 M\u03a9", "1.79 M\u03a9"],
     ["IOUT error at 1.8 V", "+8.4%", "+0.001%", "+0.5%"]],
    colw=[1.35 * inch, 0.7 * inch, 0.95 * inch, 0.8 * inch]))
E.append(Paragraph(
    "The simple mirror reaches 95% quickly but never flattens \u2014 its current is "
    "8.4% high at 1.8 V and its output resistance is only 0.12 M\u03a9. The "
    "conventional cascode is extremely flat but needs 0.79 V before reaching 99% of "
    "the target. The high-swing mirror achieves 99% at just 0.44 V \u2014 saving "
    "0.35 V \u2248 V<sub>TH</sub> of headroom \u2014 while raising output resistance "
    "13\u00d7 over the simple mirror. Its R<sub>out</sub> is lower than the "
    "conventional cascode's because its bottom devices operate at the saturation edge "
    "(V<sub>DS</sub> \u2248 V<sub>ov</sub>), where g<sub>ds</sub> is larger \u2014 the "
    "classic swing-versus-gain trade, bought deliberately for the headroom.", S["body"]))
E.append(Paragraph("C. Output compliance and output resistance", S["subsec"]))
E.append(fig(os.path.join(HERE, "fig_vout.png"),
             "Fig. 3.  I<sub>D</sub>(M4) versus swept output voltage: 92% at 0.3 V, "
             "98% at 0.4 V, 99.8% at 0.6 V."))
E.append(fig(os.path.join(HERE, "fig_rout.png"),
             "Fig. 4.  Small-signal output impedance |V/I| from AC analysis: "
             "1.574 M\u03a9, flat to \u2248100 kHz."))
E.append(Paragraph(
    "The AC measurement (Fig. 4) gives R<sub>out</sub> = 1.574 M\u03a9 at 1 kHz, in "
    "agreement with the small-signal estimate r<sub>o4</sub>(1 + g<sub>m4</sub>"
    "r<sub>o2</sub>) \u2248 1.3 M\u03a9 and with the DC slope (1.79 M\u03a9). The "
    "roll-off above 100 kHz is the output capacitance of M4.", S["body"]))
E.append(Paragraph("D. Transient behaviour", S["subsec"]))
E.append(fig(os.path.join(HERE, "fig_tran.png"),
             "Fig. 5.  Transient output current with a 100 mV, 1 kHz sine on the "
             "output node: 127 nA peak-to-peak ripple about 100.06 \u00b5A."))
E.append(Paragraph(
    "With a 100 mV-peak disturbance on the output node the mirrored current ripples "
    "only 127 nA peak-to-peak (0.13%), equivalent to R<sub>out</sub> = 0.2 V/127 nA = "
    "1.57 M\u03a9 \u2014 confirming the AC result in the time domain and demonstrating "
    "stable current operation.", S["body"]))
E.append(Paragraph("E. Supply sweep", S["subsec"]))
E.append(fig(os.path.join(HERE, "fig_vdd.png"),
             "Fig. 6.  Output current versus supply voltage at V<sub>OUT</sub> = 0.9 V: "
             "with the reference branches biased, I<sub>OUT</sub> varies less than "
             "0.06% over the full sweep — supply-insensitive operation."))

E.append(Paragraph("V. LAYOUT AND PHYSICAL VERIFICATION", S["sec"]))
E.append(Paragraph(
    "The five-transistor core was laid out in \u224817 \u00d7 31 \u00b5m (Fig. 7): "
    "M0, M1, M2 in the bottom row with integrated body ties (all sources grounded), "
    "M3 and M4 stacked above with no local taps (their sources sit at \u2248251 mV; "
    "bulk reaches ground through the substrate). M3 uses the pcell's switchSD option "
    "so its source column lands directly over M1's drain column, making the na "
    "connection a single vertical strap (Fig. 8). The gate bus of M1/M2 (the IIN net) "
    "crosses the na strap on a short Metal2 bridge with Via1 contacts \u2014 the only "
    "use of a second metal; everything else is Metal1. Diva DRC reports zero errors; "
    "extraction recognizes all five devices; and LVS declares \u201cThe net-lists "
    "match\u201d with zero unmatched instances, nets, terminals, and zero size errors "
    "(Table III).", S["body"]))
E.append(fig(os.path.join(HERE, "fig_layf.png"),
             "Fig. 7.  Complete layout: bottom row M0 (W = 3 \u00b5m), M1, M2; top row "
             "cascodes M3, M4; V<sub>B</sub> bus at top, GND rail at bottom."))
E.append(fig(os.path.join(HERE, "fig_laym.png"),
             "Fig. 8.  Mid-region detail: the vertical na/nb straps between rows, the "
             "IIN gate bus, and the Metal2 bridge with Via1 pads."))
E.append(ieee_table(
    ["TABLE III", "PHYSICAL VERIFICATION SUMMARY"],
    [["Check", "Result"],
     ["Diva DRC", "0 errors"],
     ["Extraction", "5 nmos2v devices, 0 errors"],
     ["LVS verdict", "\u201cThe net-lists match\u201d, 0 size errors"]],
    colw=[1.2 * inch, 2.2 * inch]))

E.append(Paragraph("VI. ADVANTAGES, LIMITATIONS, AND APPLICATIONS", S["sec"]))
E.append(Paragraph(
    "The high-swing cascode delivers cascode-class output resistance at nearly the "
    "theoretical minimum compliance voltage, making it the standard mirror for "
    "low-voltage analog design \u2014 op-amp loads, bias distribution and DAC current "
    "sources. Its costs are one extra bias branch (here 100 \u00b5A; in practice the "
    "bias device can be scaled to a fraction of the reference), sensitivity of the "
    "V<sub>TH</sub>+2V<sub>ov</sub> bias to process and body effect (the W/4 rule is "
    "exact only for ideal square-law devices \u2014 margin must be verified against "
    "the technology models, as done here), and a somewhat lower R<sub>out</sub> than "
    "the conventional cascode because the bottom devices sit at the saturation edge.",
    S["body"]))
E.append(Paragraph("VII. CONCLUSION", S["sec"]))
E.append(Paragraph(
    "A high-swing cascode current mirror was designed in Cadence Virtuoso with the "
    "GPDK090 library and verified against BSIM3v3 models at 100 \u00b5A and 1.8 V. "
    "The quarter-width bias device sets the cascode gates at V<sub>TH</sub> + "
    "2V<sub>ov</sub> = 1.121 V, placing the mirror devices at the saturation edge. "
    "Measured against the simple and conventional-cascode mirrors in one simulation, "
    "the design achieves R<sub>out</sub> = 1.57 M\u03a9 (13\u00d7 the simple mirror) "
    "with 99% compliance at 0.44 V (0.35 V better than the conventional cascode), "
    "and holds its current within 0.13% under a 100 mV output disturbance. The "
    "layout passes DRC cleanly and matches the schematic in LVS, completing the "
    "design through physical verification.", S["body"]))

E.append(Paragraph("REFERENCES", S["sec"]))
E.append(Paragraph(
    "[1]\u2002P. R. Gray, P. J. Hurst, S. H. Lewis, and R. G. Meyer, Analysis and "
    "Design of Analog Integrated Circuits, 5th ed. Hoboken, NJ, USA: Wiley, 2009.",
    S["ref"]))
E.append(Paragraph(
    "[2]\u2002B. Razavi, Design of Analog CMOS Integrated Circuits, 2nd ed. New York, "
    "NY, USA: McGraw-Hill, 2017.", S["ref"]))
E.append(Paragraph(
    "[3]\u2002N. S. Sooch, \u201cMOS Cascode Current Mirror,\u201d U.S. Patent "
    "4,550,284, Oct. 29, 1985.", S["ref"]))

doc.build(E)
print("written:", OUT)
