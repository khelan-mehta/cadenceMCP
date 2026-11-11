"""IEEE two-column report: Energy-Harvester-Powered PMU — two-stage CMOS error
amplifier (gpdk180, Cadence Virtuoso). Built strictly from the Review II
evidence; proposed LDO values labelled as proposals; placeholders where the
evidence does not fix a value."""
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
OUT = r"C:\Users\NG\Desktop\cadence MCP\PMU_ErrorAmp_IEEE_Report.pdf"

PAGE_W, PAGE_H = letter
MARGIN = 0.72 * inch
COL_GAP = 0.24 * inch
COL_W = (PAGE_W - 2 * MARGIN - COL_GAP) / 2
TITLE_H = 1.5 * inch

S = {}
S["title"] = ParagraphStyle("title", fontName="Times-Roman", fontSize=16.5,
                            leading=20, alignment=TA_CENTER, spaceAfter=9)
S["author"] = ParagraphStyle("author", fontName="Times-Roman", fontSize=11,
                             leading=13, alignment=TA_CENTER)
S["affil"] = ParagraphStyle("affil", fontName="Times-Roman", fontSize=9.5,
                            leading=11.5, alignment=TA_CENTER)
S["abstract"] = ParagraphStyle("abstract", fontName="Times-Bold", fontSize=9,
                               leading=10.6, alignment=TA_JUSTIFY, spaceAfter=5)
S["body"] = ParagraphStyle("body", fontName="Times-Roman", fontSize=9.4,
                           leading=10.8, alignment=TA_JUSTIFY, firstLineIndent=10)
S["bodyni"] = ParagraphStyle("bodyni", parent=S["body"], firstLineIndent=0)
S["eq"] = ParagraphStyle("eq", fontName="Times-Italic", fontSize=9.4, leading=11,
                         alignment=TA_CENTER, spaceBefore=3, spaceAfter=3)
S["sec"] = ParagraphStyle("sec", fontName="Times-Roman", fontSize=9.8, leading=12,
                          alignment=TA_CENTER, spaceBefore=7, spaceAfter=3)
S["subsec"] = ParagraphStyle("subsec", fontName="Times-Italic", fontSize=9.8,
                             leading=12, alignment=TA_LEFT, spaceBefore=5, spaceAfter=2)
S["caption"] = ParagraphStyle("caption", fontName="Times-Roman", fontSize=8.0,
                              leading=9.3, alignment=TA_LEFT, spaceBefore=2, spaceAfter=5)
S["tabcap"] = ParagraphStyle("tabcap", fontName="Times-Roman", fontSize=8.2,
                             leading=9.6, alignment=TA_CENTER, spaceBefore=2, spaceAfter=2)
S["ref"] = ParagraphStyle("ref", fontName="Times-Roman", fontSize=8.2, leading=9.6,
                          alignment=TA_JUSTIFY, leftIndent=13, firstLineIndent=-13,
                          spaceAfter=2)

PLOT_W = 2.55*inch
def fig(path, *args, width=COL_W, crop_top=0):
    caption = args[0] if args else ""
    if crop_top:
        im0 = PILImage.open(path)
        path2 = path.replace(".png", "_c.png")
        im0.crop((0, crop_top, im0.size[0], im0.size[1])).save(path2)
        path = path2
    im = PILImage.open(path); w, h = im.size
    return KeepTogether([Image(path, width=width, height=h * width / w),
                         Paragraph(caption, S["caption"])])

def tab(title_lines, data, colw=None, fs=7.5):
    t = Table(data, colWidths=colw, hAlign="CENTER")
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Times-Roman"),
        ("FONTSIZE", (0, 0), (-1, -1), fs),
        ("LEADING", (0, 0), (-1, -1), fs + 1.6),
        ("LINEABOVE", (0, 0), (-1, 0), 0.8, colors.black),
        ("LINEBELOW", (0, 0), (-1, 0), 0.4, colors.black),
        ("LINEBELOW", (0, -1), (-1, -1), 0.8, colors.black),
        ("TOPPADDING", (0, 0), (-1, -1), 0.9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0.9),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return KeepTogether([Paragraph(l, S["tabcap"]) for l in title_lines] + [t, Spacer(1, 5)])

def P(cell):
    return Paragraph(cell, ParagraphStyle("c", fontName="Times-Roman", fontSize=7.5,
                                          leading=8.7, alignment=TA_LEFT))

doc = BaseDocTemplate(OUT, pagesize=letter, leftMargin=MARGIN, rightMargin=MARGIN,
                      topMargin=MARGIN, bottomMargin=MARGIN,
                      title="Design of an Energy-Harvester-Powered Power Management "
                            "Unit for Low-Power Applications in 0.18 um CMOS",
                      author="Purvesh Vaghela, Utsav Raiyani")
frame_title = Frame(MARGIN, PAGE_H - MARGIN - TITLE_H, PAGE_W - 2 * MARGIN, TITLE_H,
                    id="title", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
def cols(top_y):
    h = top_y - MARGIN
    return [Frame(MARGIN, MARGIN, COL_W, h, id="c1", leftPadding=0, rightPadding=0,
                  topPadding=0, bottomPadding=0),
            Frame(MARGIN + COL_W + COL_GAP, MARGIN, COL_W, h, id="c2", leftPadding=0,
                  rightPadding=0, topPadding=0, bottomPadding=0)]
doc.addPageTemplates([
    PageTemplate(id="first", frames=[frame_title] + cols(PAGE_H - MARGIN - TITLE_H - 6)),
    PageTemplate(id="rest", frames=cols(PAGE_H - MARGIN))])

E = []

# ---------------- title block ----------------
E.append(Paragraph("Design of an Energy-Harvester-Powered Power Management Unit for "
                   "Low-Power Applications Using 0.18 \u00b5m CMOS Technology in "
                   "Cadence Virtuoso", S["title"]))
E.append(Paragraph("Purvesh Vaghela (23BEC201) \u2003 Utsav Raiyani (23BEC199)", S["author"]))
E.append(Paragraph("Department of Electronics and Communication Engineering, Institute of "
                   "Technology, Nirma University<br/>"
                   "Mentor: Prof. Purvi Patel \u2014 Course: Research Methodology &amp; Seminar",
                   S["affil"]))
E.append(NextPageTemplate("rest"))
E.append(FrameBreak())

# ---------------- abstract ----------------
E.append(Paragraph(
    "<i>Abstract</i>\u2014Battery-less sensor nodes and Internet of Things (IoT) devices "
    "depend on energy harvested from the environment, but harvested sources such as small "
    "solar cells deliver low and fluctuating voltages, approximately 0.3\u20131 V, which "
    "cannot power electronic loads directly. A power management unit (PMU) is therefore "
    "required to condition, store and regulate the harvested energy. This report presents "
    "the architecture of a proposed solar energy-harvesting PMU and the design and "
    "standalone characterization of its first implemented block: a two-stage CMOS "
    "operational amplifier intended as the error amplifier of a future low-dropout (LDO) "
    "regulator. The amplifier uses a PMOS differential input pair with a current-mirror "
    "load, a common-source second stage, and Miller compensation with a series nulling "
    "resistor. It was designed by square-law hand sizing and simulated in Cadence Virtuoso "
    "using the gpdk180 process at a 1.8 V supply and a 0.5 V input common mode. The "
    "simulated amplifier achieves approximately 70.5 dB open-loop gain, 1.629 MHz "
    "unity-gain bandwidth, 51.8\u00b0 phase margin, 87.8 dB CMRR at 10 Hz, and a reported "
    "ADE power figure of 4.73 \u00b5W at 3.27 \u00b5A supply current. The phase margin "
    "falls short of the 60\u00b0 design guideline, and the complete PMU \u2014 LDO, "
    "reference, boost/conditioning stage and voltage monitor \u2014 remains proposed "
    "rather than implemented. The report separates verified amplifier results from "
    "proposed LDO values and sets out the verification plan for the remaining blocks.",
    S["abstract"]))
E.append(Paragraph(
    "<i>Index Terms</i>\u2014Energy harvesting, power management unit, low-dropout "
    "regulator, error amplifier, two-stage CMOS operational amplifier, Miller "
    "compensation, 0.18 \u00b5m CMOS.", S["abstract"]))

# ---------------- I. introduction ----------------
E.append(Paragraph("I. INTRODUCTION", S["sec"]))
E.append(Paragraph(
    "Wireless sensor networks and IoT deployments increasingly favour nodes that operate "
    "without battery replacement, which places the burden of supplying power on energy "
    "harvested from the environment. Among the available ambient sources, small solar "
    "cells are attractive for such nodes because of their comparatively high power "
    "density and their natural compatibility with CMOS integration; this motivated the "
    "solar-harvesting PMU of Patel et al., which regulates the output of on-chip solar "
    "cells using a 0.18 \u00b5m CMOS LDO and serves as the principal reference for this "
    "project [1].", S["body"]))
E.append(Paragraph(
    "Harvested electrical energy is, however, poorly suited to direct use. The project "
    "presentation models two series solar cells that deliver roughly 0.3\u20131 V "
    "depending on illumination, and the available power varies with the environment. A "
    "PMU bridges this gap: it conditions the input, stores energy, generates a reference, "
    "regulates the supply seen by the load, and can disconnect the load when stored "
    "energy is insufficient. Within such a PMU, the regulation duty falls on a linear "
    "LDO stage, whose accuracy and stability are set largely by its error amplifier "
    "[2], [3]. The error amplifier compares a divided copy of the output with a "
    "reference and drives the gate of a PMOS pass transistor, so its gain, bandwidth, "
    "phase margin and quiescent current directly determine the regulation quality and "
    "the power overhead of the whole unit.", S["body"]))
E.append(Paragraph(
    "This project therefore begins the PMU design with its most performance-critical "
    "analog block. A two-stage CMOS operational amplifier was designed by square-law "
    "hand analysis, implemented in Cadence Virtuoso on the generic 0.18 \u00b5m process "
    "design kit (gpdk180), and characterized with the Spectre simulator. The 0.18 "
    "\u00b5m node was selected because it is the technology of the reference PMU [1], "
    "offers well-characterized 1.8 V devices with adequate headroom for a two-stage "
    "topology, and is the process available in the institute's Cadence environment. "
    "This report documents the architecture, sizing, simulation methodology and "
    "measured standalone results of the amplifier, and presents the proposed \u2014 "
    "not yet implemented \u2014 LDO and PMU integration plan.", S["body"]))

# ---------------- II. problem, objectives, scope ----------------
E.append(Paragraph("II. PROBLEM STATEMENT, OBJECTIVES AND SCOPE", S["sec"]))
E.append(Paragraph(
    "<b>Problem statement.</b> To design an energy harvester-powered power management "
    "unit for low-power applications using 0.18 \u00b5m CMOS technology in Cadence "
    "Virtuoso, converting a low and fluctuating harvested input into a regulated supply "
    "suitable for low-power loads such as sensor nodes.", S["bodyni"]))
E.append(Paragraph(
    "The measurable objectives, with their verification methods and present status, are "
    "collected in Table I. Objectives 1\u20133 concern the error amplifier and are "
    "complete at schematic level; objectives 4\u20137 define the remaining system work. "
    "The scope completed so far is the standalone amplifier: schematic entry, DC "
    "operating-point verification, AC gain/phase, CMRR, transient and slew-rate "
    "simulation. The proposed scope \u2014 LDO closure around a PMOS pass device, "
    "reference, input conditioning or boost stage, storage, and voltage monitoring "
    "\u2014 is specified but unverified.", S["body"]))
E.append(tab(["TABLE I", "PROJECT OBJECTIVES AND VERIFICATION CRITERIA"],
    [["#", P("Objective"), P("Requirement"), P("Verification"), P("Status")],
     ["1", P("Design two-stage error amplifier in gpdk180"), P("All devices saturated at V<sub>DD</sub>=1.8 V, V<sub>ICM</sub>=0.5 V"), P("DC operating point"), P("Done (all region 2)")],
     ["2", P("Meet amplifier small-signal targets"), P("A<sub>v</sub>\u226560 dB; GBW 10\u20132000 kHz; CMRR\u226580 dB"), P("AC / CMRR analyses"), P("Done (70.5 dB; 1.629 MHz; 87.8 dB)")],
     ["3", P("Stability and dynamics"), P("PM\u226560\u00b0; SR\u22650.1 V/\u00b5s; P<10\u2013100 \u00b5W"), P("AC phase, transient, ADE power"), P("Partial \u2014 PM 51.8\u00b0 below 60\u00b0")],
     ["4", P("Close LDO loop (PMOS pass + divider)"), P("V<sub>out</sub>=1.2 V from V<sub>ref</sub>=0.5 V at \u2264100 \u00b5A"), P("DC, load/line sweeps, loop gain"), P("Proposed \u2014 not simulated")],
     ["5", P("Voltage reference"), P("0.5 V, low-power"), P("DC, temperature sweep"), P("Proposed")],
     ["6", P("Harvest interface / boost + storage"), P("Operate from 0.3\u20131 V source"), P("System transient"), P("Proposed")],
     ["7", P("Voltage monitor and load control"), P("Connect load only when energy suffices"), P("System transient"), P("Proposed")]],
    colw=[0.14*inch, 0.76*inch, 0.94*inch, 0.66*inch, 0.84*inch]))

# ---------------- III. related work ----------------
E.append(Paragraph("III. RELATED WORK", S["sec"]))
E.append(Paragraph(
    "Patel, Mishra and Nagchoudhuri integrate on-chip solar cells with a 36 nW PMU in "
    "0.18 \u00b5m CMOS, using a subthreshold cascoded error amplifier inside an LDO; "
    "their work demonstrates the feasibility of full integration but accepts modest "
    "amplifier gain (\u224846 dB) and bandwidth as the price of nanowatt operation [1]. "
    "The present project deliberately diverges by biasing the amplifier in strong/"
    "moderate inversion from a 1.8 V rail, trading microwatt quiescent power for "
    "higher, more predictable gain. Rinc\u00f3n-Mora and Allen established the "
    "canonical low-quiescent-current LDO analysis \u2014 pass-device sizing, loop "
    "stability with the output capacitor and its equivalent series resistance (ESR) "
    "\u2014 that the proposed LDO stage follows [2]. For the amplifier itself, the "
    "two-stage Miller-compensated topology and the nulling-resistor technique for "
    "cancelling the right-half-plane (RHP) zero are standard results covered in "
    "Razavi and in Gray et al. [3], [4]; Allen and Holberg give the square-law design "
    "procedure used for hand sizing [5]. On the system side, Seok et al. demonstrate a "
    "picowatt 2-transistor 0.5 V reference suitable for harvesting PMUs [6], and "
    "Seeman and Sanders provide the analysis framework for the switched-capacitor "
    "conversion stage that the 0.3\u20131 V source will require [7]. Table II compares "
    "these works; NR marks values not reported by the cited source.", S["body"]))
E.append(tab(["TABLE II", "LITERATURE COMPARISON (NR = NOT REPORTED IN THE CITED SOURCE)"],
    [[P("Ref."), P("Tech."), P("Architecture"), P("Supply"), P("Power"), P("Gain / BW"), P("Contribution"), P("Limitation")],
     [P("[1]"), P("0.18 \u00b5m"), P("Solar PMU: LDO + subthreshold cascoded error amp"), P("\u22480.98\u20131.33 V in"), P("36 nW (PMU)"), P("46.39 dB / 206 kHz UGB"), P("Fully integrated nW solar PMU"), P("Subthreshold: low gain, slow")],
     [P("[2]"), P("2 \u00b5m BiCMOS"), P("Low-dropout regulator"), P("NR"), P("NR"), P("NR"), P("LDO stability/quiescent analysis"), P("Older node; discrete C<sub>o</sub><sub>u</sub><sub>t</sub>")],
     [P("[6]"), P("0.13 \u00b5m"), P("2-transistor voltage reference"), P("0.5 V"), P("picowatt"), P("\u2014"), P("Ultra-low-power 0.5 V reference"), P("Untrimmed accuracy limits")],
     [P("[7]"), P("\u2014 (theory)"), P("Switched-capacitor DC\u2013DC analysis"), P("\u2014"), P("\u2014"), P("\u2014"), P("SC converter optimization method"), P("No silicon demonstrator")],
     [P("This work"), P("0.18 \u00b5m (gpdk180)"), P("Two-stage error amp for PMU LDO"), P("1.8 V"), P("4.73 \u00b5W (ADE, def. pending)"), P("70.5 dB / 1.629 MHz"), P("Verified standalone error amp"), P("PM 51.8\u00b0; system blocks proposed only")]],
    colw=[0.24*inch, 0.38*inch, 0.60*inch, 0.36*inch, 0.38*inch, 0.44*inch, 0.48*inch, 0.46*inch]))

# ---------------- IV. proposed PMU architecture ----------------
E.append(Paragraph("IV. PROPOSED PMU ARCHITECTURE", S["sec"]))
E.append(fig(os.path.join(HERE, "fig_block.png"),
             "Fig. 1. Proposed PMU block diagram from the project presentation: solar-"
             "cell equivalent model (left) feeding the proposed regulation chain \u2014 "
             "reference, error amplifier, pass element, R1/R2 feedback divider, "
             "C<sub>L</sub> = 10 \u00b5F output capacitor, voltage monitor and load switch P1. "
             "Only the error amplifier is implemented to date.", width=3.0*inch))
E.append(Paragraph(
    "Energy and signal flow proceed left to right in Fig. 1. The harvester (modelled as "
    "two series solar cells, each an I<sub>solar</sub> source with diodes "
    "and a 2 G\u03a9 shunt behind a 1 m\u03a9 series resistance) feeds the PMU input "
    "node. A reference generator derives V<sub>ref</sub>; the error amplifier "
    "compares V<sub>ref</sub> with the feedback voltage tapped from the R1/R2 "
    "divider and drives the pass element so that the output settles where both inputs "
    "balance. The output capacitor holds V<sub>out</sub> between energy arrivals, "
    "and a voltage monitor gates the load through switch P1 so the node draws power "
    "only when the stored energy permits \u2014 the duty-cycled operating style of "
    "harvesting PMUs [1].", S["body"]))
E.append(Paragraph(
    "<b>Voltage headroom.</b> A 0.3\u20131 V source cannot drive a conventional LDO "
    "whose target output is 1.2 V: a linear regulator only drops voltage, and it needs "
    "an input above the output by at least the pass-device dropout. The architecture "
    "therefore requires either a boost or switched-capacitor conversion stage between "
    "the harvester and the LDO input, together with an energy-storage element that "
    "accumulates charge toward the \u22481.8 V rail assumed for the amplifier "
    "characterization [7]. This conditioning stage is part of the proposed scope; the "
    "amplifier results reported here were obtained from an ideal 1.8 V supply and do "
    "not demonstrate operation from the harvester. Table III summarizes the status of "
    "every block.", S["body"]))
E.append(tab(["TABLE III", "SYSTEM-BLOCK STATUS"],
    [[P("PMU block"), P("Function"), P("Status"), P("Next action")],
     [P("Error amplifier"), P("Compare V<sub>fb</sub> with V<sub>ref</sub>, drive pass gate"), P("Implemented, verified"), P("Re-verify inside closed LDO loop")],
     [P("PMOS pass element"), P("Drop V<sub>IN</sub>\u2212V<sub>out</sub>, source load current"), P("Proposed (60 \u00b5m/0.5 \u00b5m)"), P("DC + load-sweep verification")],
     [P("Feedback divider R1/R2"), P("Scale V<sub>out</sub> to V<sub>fb</sub>"), P("Proposed (700 k\u03a9/500 k\u03a9)"), P("Confirm ratio, current draw")],
     [P("Voltage reference"), P("0.5 V set-point"), P("Proposed"), P("Select & simulate topology [6]")],
     [P("Boost / conditioning + storage"), P("Raise 0.3\u20131 V source to LDO input; buffer energy"), P("Proposed"), P("Topology study [7], sizing")],
     [P("Voltage monitor + P1"), P("Load connect/disconnect"), P("Proposed"), P("Threshold design, hysteresis")]],
    colw=[0.74*inch, 1.06*inch, 0.80*inch, 0.74*inch]))

# ---------------- V. error-amplifier design ----------------
E.append(Paragraph("V. TWO-STAGE ERROR-AMPLIFIER DESIGN", S["sec"]))
E.append(fig(os.path.join(HERE, "fig_sch.png"),
             "Fig. 2. Cadence Virtuoso schematic of the two-stage amplifier (gpdk180): "
             "PMOS input pair M1/M2, NMOS mirror load M3/M4, PMOS bias mirror M8/M5/M7 "
             "from I<sub>ref</sub>, common-source second stage M6 with PMOS load M7, "
             "and R<sub>Z</sub>\u2013C<sub>C</sub> Miller network from the first-stage output to "
             "V<sub>out</sub>; C<sub>L</sub> models the load.", width=3.1*inch))
E.append(Paragraph(
    "The input pair M1/M2 is PMOS. With a 0.5 V common mode an NMOS pair would not "
    "remain in saturation \u2014 its required minimum common mode (tail overdrive plus "
    "V<sub>TH</sub> plus input overdrive) exceeds 0.5 V \u2014 whereas a PMOS pair "
    "referenced to the 1.8 V rail senses low common-mode inputs naturally; PMOS inputs "
    "also exhibit lower 1/f noise, which matters for the low-frequency biomedical-"
    "class loads the project targets [3]. The NMOS mirror M3/M4 converts the "
    "differential current to a single-ended signal at the M4 drain; M8 is the "
    "diode-connected master of the PMOS bias mirror fed by I<sub>ref</sub>, with M5 "
    "supplying the 1 \u00b5A tail and M7 the second-stage load current. M6 forms a "
    "common-source second stage, giving the output swing needed to drive a PMOS pass "
    "gate. Stability is set by pole splitting through C<sub>C</sub> with series resistor "
    "R<sub>Z</sub> \u2248 1/g<sub>m6</sub> to cancel the RHP zero [4], [5]. The exact "
    "C<sub>C</sub>, R<sub>Z</sub> and C<sub>L</sub> component values are not visible in the supplied "
    "schematic captures and must be confirmed from the schematic properties: "
    "[INSERT VERIFIED C<sub>C</sub>/R<sub>Z</sub>/C<sub>L</sub> FROM CADENCE].", S["body"]))
E.append(Paragraph("A. Hand sizing", S["subsec"]))
E.append(Paragraph(
    "Devices were sized with the square-law expression, using the first-order gpdk180 "
    "stand-in constants k<sub>n</sub> = µ<sub>n</sub>C<sub>ox</sub> = 316 \u00b5A/V\u00b2 and "
    "k<sub>p</sub> = 62.5 \u00b5A/V\u00b2 taken from the reference paper's device table [1]:",
    S["body"]))
E.append(Paragraph("W/L = 2 I<sub>D</sub> / ( k \u00b7 V<sub>ov</sub><super>2</super> ) \u2003\u2003 (1)", S["eq"]))
E.append(Paragraph(
    "where I<sub>D</sub> is the branch drain current and V<sub>ov</sub> = V<sub>GS</sub>\u2212"
    "V<sub>TH</sub> the chosen overdrive. Overdrives of 0.12 V (input pair, maximizing "
    "g<sub>m</sub>/I<sub>D</sub>), 0.15 V (NMOS mirror and M6) and 0.20 V (PMOS current sources) "
    "give the sizing of Table IV. Equation (1) is an idealized long-channel "
    "approximation: the final operating point must come from simulation, and Section "
    "VII quantifies where it deviates.", S["body"]))
E.append(tab(["TABLE IV", "TRANSISTOR SIZING (FROM THE PROJECT'S CALCULATED TABLE)"],
    [[P("Device"), P("Type"), P("I<sub>D</sub>"), P("V<sub>ov</sub>"), P("W/L calc"), P("W"), P("L"), P("Sizing rationale")],
     [P("M1, M2"), P("PMOS"), P("0.5 \u00b5A"), P("0.12 V"), P("1.11"), P("1.1 \u00b5m"), P("1 \u00b5m"), P("Input pair; low V<sub>ov</sub> for g<sub>m</sub>/I<sub>D</sub>")],
     [P("M3, M4"), P("NMOS"), P("0.5 \u00b5A"), P("0.15 V"), P("0.14"), P("0.4 \u00b5m"), P("2.855 \u00b5m"), P("Mirror load; min-width bound, long L for matching/r<sub>o</sub>")],
     [P("M5"), P("PMOS"), P("1.0 \u00b5A"), P("0.20 V"), P("0.80"), P("0.8 \u00b5m"), P("1 \u00b5m"), P("Tail source (mirrors M8 \u00d71)")],
     [P("M6"), P("NMOS"), P("2.0 \u00b5A"), P("0.15 V"), P("0.56"), P("0.56 \u00b5m"), P("1 \u00b5m"), P("2nd-stage CS; matches M3/M4 V<sub>ov</sub> for offset")],
     [P("M7"), P("PMOS"), P("2.0 \u00b5A"), P("0.20 V"), P("1.60"), P("1.6 \u00b5m"), P("1 \u00b5m"), P("2nd-stage load (mirrors M8 \u00d72)")],
     [P("M8"), P("PMOS"), P("1.0 \u00b5A"), P("0.20 V"), P("0.80"), P("0.8 \u00b5m"), P("1 \u00b5m"), P("Bias diode from I<sub>ref</sub> = 1 \u00b5A")]],
    colw=[0.34*inch, 0.32*inch, 0.36*inch, 0.30*inch, 0.34*inch, 0.36*inch, 0.38*inch, 0.94*inch]))
E.append(Paragraph("B. Small-signal design relations", S["subsec"]))
E.append(Paragraph(
    "The first-stage gain, second-stage gain, unity-gain bandwidth and slew rate obey "
    "the standard two-stage relations [4], [5]:", S["bodyni"]))
E.append(Paragraph("A<sub>v1</sub> = g<sub>m1</sub> ( r<sub>o2</sub> || r<sub>o4</sub> ) \u2003\u2003 (2)", S["eq"]))
E.append(Paragraph("A<sub>v2</sub> = g<sub>m6</sub> ( r<sub>o6</sub> || r<sub>o7</sub> ) \u2003\u2003 (3)", S["eq"]))
E.append(Paragraph("GBW = g<sub>m1</sub> / ( 2\u03c0 C<sub>C</sub> ) \u2003\u2003 (4)", S["eq"]))
E.append(Paragraph("SR = I<sub>tail</sub> / C<sub>C</sub> \u2003\u2003 (5)", S["eq"]))
E.append(Paragraph(
    "where g<sub>mi</sub> and r<sub>oi</sub> are the transconductance and output "
    "resistance of device M<sub>i</sub>, C<sub>C</sub> the Miller capacitor and I<sub>tail</sub> "
    "the tail current. With the simulated g<sub>m1</sub> = 6.43 \u00b5S and the measured "
    "GBW of 1.629 MHz, (4) implies an effective compensation capacitance of about "
    "0.63 pF; this is a consistency check derived from measured values, not a design "
    "entry, and the drawn C<sub>C</sub> must still be read from the schematic.", S["body"]))

# ---------------- VI. methodology ----------------
E.append(Paragraph("VI. SIMULATION METHODOLOGY", S["sec"]))
E.append(Paragraph(
    "All simulations ran in the Cadence Analog Design Environment (ADE) with the "
    "Spectre engine on gpdk180 models, V<sub>DD</sub> = 1.8 V, I<sub>ref</sub> = "
    "1 \u00b5A and 27 \u00b0C, as evidenced by the ADE session captures. The recorded "
    "analyses are: (i) a DC operating point with on-schematic annotation to confirm "
    "every device in saturation (region 2); (ii) an AC sweep (10 Hz\u20131 GHz) of the "
    "differential gain for DC gain, \u22123 dB bandwidth and unity-gain frequency; "
    "(iii) phase of the same response at the unity-gain frequency for phase margin; "
    "(iv) a CMRR measurement computed as the ratio of differential to common-mode "
    "gain, dB20[(V<sub>out</sub>/V<sub>in+</sub>)/(V<sub>out,cm</sub>/"
    "V<sub>cm</sub>)], using a replica bench driven by a common-mode source; (v) a "
    "transient run (10 ms, \u00b11 mV differential sine at the 0.5 V common mode) and "
    "a 2 ms transient from which ADE's slewRate function reports 611.877 kV/s; and "
    "(vi) an ADE output named Power that reports 4.7345 \u00b5W. The expression behind "
    "that Power output is not visible in the captures, so its definition \u2014 and in "
    "particular whether it averages over a supply sweep that was active in the same "
    "session \u2014 requires confirmation: [CONFIRM ADE POWER EXPRESSION]. Analyses "
    "not evidenced (PSRR, noise, corners, Monte Carlo, post-layout) were not "
    "performed. Closing the LDO will additionally require input-line and load sweeps, "
    "loop-gain (stability) analysis with the 10 \u00b5F output capacitor and its ESR, "
    "start-up transients and PSRR [2].", S["body"]))

# ---------------- VII. results ----------------
E.append(Paragraph("VII. RESULTS AND DISCUSSION", S["sec"]))
E.append(fig(os.path.join(HERE, "fig_dcop.png"),
             "Fig. 3. DC operating point annotated on the schematic: every device "
             "reports region 2 (saturation); supply current i(V<sub>DD</sub>) = 3.26964 "
             "\u00b5A; tail devices carry \u22480.996 \u00b5A and the second stage "
             "1.273 \u00b5A.", width=3.1*inch))
E.append(Paragraph("A. Operating point", S["subsec"]))
E.append(Paragraph(
    "Table V extracts the annotated operating point. All eight transistors sit in "
    "saturation, validating the bias chain: M8 and M5 mirror I<sub>ref</sub> "
    "accurately (0.9964\u20131.0 \u00b5A) and the pair splits the tail evenly "
    "(0.498 \u00b5A each). Two deviations from the hand design deserve note. First, "
    "the second-stage current is 1.273 \u00b5A rather than the intended 2 \u00b5A "
    "(a \u221236 % deviation), so the total supply current is 3.27 \u00b5A instead of "
    "the planned 4 \u00b5A; the W<sub>7</sub>/W<sub>8</sub> = 2 mirror ratio is not realized "
    "exactly at this operating point, which first-order sizing with assumed k<sub>p</sub> "
    "and channel-length modulation at |V<sub>DS</sub>| = 1.65 V readily explains. "
    "Second, the open-loop output node rests at approximately 0.15 V (V<sub>DS</sub> of "
    "M6), far from mid-rail \u2014 expected for an uncommitted high-gain amplifier, "
    "and a reminder that this bench fixes the bias only; in the LDO the feedback loop "
    "will place the output where the pass device requires.", S["body"]))
E.append(tab(["TABLE V", "DC OPERATING POINT (FROM THE ANNOTATED SCHEMATIC, FIG. 3)"],
    [[P("Device"), P("I<sub>D</sub>"), P("V<sub>GS</sub>"), P("V<sub>DS</sub>"), P("g<sub>m</sub>"), P("Region"), P("Interpretation")],
     [P("M1/M2"), P("\u22120.498 \u00b5A"), P("\u2212724.8 mV"), P("\u2212665.1 mV"), P("6.43 \u00b5S"), P("2 (sat)"), P("Balanced input pair")],
     [P("M3/M4"), P("0.498 \u00b5A"), P("559.6 mV"), P("559.6 mV"), P("5.78 \u00b5S"), P("2 (sat)"), P("1:1 mirror load, diode-matched")],
     [P("M5"), P("\u22120.996 \u00b5A"), P("\u2212649.2 mV"), P("\u2212575.2 mV"), P("8.44 \u00b5S"), P("2 (sat)"), P("Tail \u2248 I<sub>ref</sub>")],
     [P("M6"), P("1.273 \u00b5A"), P("559.6 mV"), P("152.5 mV"), P("15.94 \u00b5S"), P("2 (sat)"), P("CS stage; output rests low (open loop)")],
     [P("M7"), P("\u22121.273 \u00b5A"), P("\u2212649.2 mV"), P("\u22121.648 V"), P("10.22 \u00b5S"), P("2 (sat)"), P("36 % below 2 \u00b5A design intent")],
     [P("M8"), P("\u22121.000 \u00b5A"), P("\u2212649.2 mV"), P("\u2212649.2 mV"), P("8.47 \u00b5S"), P("2 (sat)"), P("Bias diode; V(I<sub>ref</sub>)=1.151 V")]],
    colw=[0.36*inch, 0.46*inch, 0.46*inch, 0.46*inch, 0.40*inch, 0.34*inch, 0.86*inch]))
E.append(Paragraph("B. Frequency response, stability, CMRR", S["subsec"]))
E.append(fig(os.path.join(HERE, "fig_gain.png"),
             "Fig. 4. Open-loop magnitude response: \u224870.5 dB low-frequency gain; "
             "marker at the 0 dB crossing gives a unity-gain bandwidth of 1.62875 MHz. "
             "A separate marker at gain\u22123 dB (67.5 dB) gives the \u22123 dB "
             "bandwidth of 550.915 Hz.", width=PLOT_W, crop_top=55))
E.append(fig(os.path.join(HERE, "fig_pm.png"),
             "Fig. 5. Phase (top) and magnitude (bottom) at the unity-gain frequency: "
             "the phase marker reads 51.7764\u00b0 where the gain is 0.193 dB, i.e. a "
             "phase margin of \u224851.8\u00b0.", width=PLOT_W, crop_top=55))
E.append(Paragraph(
    "The amplifier reaches 70.5 dB of DC gain \u2014 inside the 60\u201380 dB target "
    "band \u2014 with a single dominant pole at \u2248551 Hz and a 0 dB crossing at "
    "1.629 MHz, consistent with a gain-bandwidth product of A<sub>v</sub>·f<sub>−3dB</sub> "
    "\u2248 3350\u00d7551 Hz \u2248 1.85 MHz to first order. The phase margin is "
    "approximately 51.8\u00b0. This is a genuine shortfall against the 60\u00b0 "
    "guideline adopted at specification time (the presentation's final table relaxes "
    "the target to 45\u201360\u00b0): 51.8\u00b0 is stable and acceptable for initial "
    "characterization, but a two-stage amplifier destined for an LDO loop \u2014 where "
    "the pass device and output capacitor add further phase lag \u2014 should enter "
    "that loop with margin in hand. Increasing C<sub>C</sub>, retuning R<sub>Z</sub> toward "
    "1/g<sub>m6</sub>, or accepting a lower GBW are the standard remedies [4]; this "
    "retuning is scheduled before loop closure rather than claimed complete.", S["body"]))
E.append(fig(os.path.join(HERE, "fig_cmrr.png"),
             "Fig. 6. CMRR versus frequency computed as dB20[(V<sub>out</sub>/"
             "V<sub>in+</sub>)/(V<sub>out,cm</sub>/V<sub>cm</sub>)]: 87.8133 dB "
             "at 10 Hz, flat through the audio band and rolling off beyond "
             "\u2248100 kHz.", width=PLOT_W, crop_top=55))
E.append(Paragraph("C. Transient behaviour and power", S["subsec"]))
E.append(fig(os.path.join(HERE, "fig_tran.png"),
             "Fig. 7. Open-loop transient with a \u00b11 mV, \u2248 1 kHz differential "
             "drive about the 0.5 V common mode: the 70.5 dB gain saturates the "
             "output, which swings essentially rail to rail (\u22480.05\u20131.8 V).", width=PLOT_W, crop_top=35))
E.append(Paragraph(
    "Fig. 7 is an open-loop test: a millivolt-level differential input multiplied by "
    "\u22483350 V/V exceeds the supply, so the output clips and the waveform mainly "
    "demonstrates polarity, swing and the absence of latch-up \u2014 it is not an LDO "
    "load-step response and must not be read as one. The ADE slewRate output on a "
    "dedicated 2 ms transient reports 611.877 kV/s \u2248 0.612 V/\u00b5s, meeting the "
    "\u22650.1 V/\u00b5s target. For power, two numbers coexist in the evidence and "
    "must not be conflated: the ADE output reports 4.7345 \u00b5W (definition "
    "unconfirmed, Section VI), while the DC operating point implies", S["body"]))
E.append(Paragraph("P = V<sub>DD</sub> \u00b7 I<sub>DD</sub> = 1.8 V \u00d7 3.26964 \u00b5A "
                   "\u2248 5.885 \u00b5W \u2003\u2003 (6)", S["eq"]))
E.append(Paragraph(
    "Both lie comfortably inside the <10\u2013100 \u00b5W budget, but the \u224820 % "
    "gap between them is a measurement-definition question, not a physical result, "
    "and is flagged for resolution. Table VI assembles the verified results.", S["body"]))
E.append(tab(["TABLE VI", "AMPLIFIER SIMULATION RESULTS (STANDALONE, gpdk180, 1.8 V)"],
    [[P("Parameter"), P("Target"), P("Simulated"), P("Unit"), P("Assessment"), P("Evidence")],
     [P("DC open-loop gain"), P("60\u201380"), P("\u224870.5"), P("dB"), P("Met"), P("Fig. 4")],
     [P("\u22123 dB bandwidth"), P("\u2014"), P("550.915"), P("Hz"), P("Consistent w/ GBW"), P("Fig. 4 marker")],
     [P("Unity-gain bandwidth"), P("0.01\u20132"), P("1.62875"), P("MHz"), P("Met"), P("Fig. 4")],
     [P("Phase margin"), P("\u226560 (relaxed 45\u201360)"), P("\u224851.8"), P("\u00b0"), P("Below 60\u00b0 \u2014 retune before LDO"), P("Fig. 5")],
     [P("CMRR @ 10 Hz"), P("80\u2013100"), P("87.8133"), P("dB"), P("Met"), P("Fig. 6")],
     [P("Slew rate"), P("\u22650.1\u20131"), P("\u22480.612"), P("V/\u00b5s"), P("Met"), P("ADE slewRate output")],
     [P("Supply current (DC op)"), P("\u2014"), P("3.26964"), P("\u00b5A"), P("\u2014"), P("Fig. 3")],
     [P("Power (ADE output)"), P("<10\u2013100"), P("4.7345"), P("\u00b5W"), P("Met; definition pending"), P("ADE session capture")],
     [P("Power (V<sub>DD</sub>\u00b7I<sub>DD</sub>)"), P("<10\u2013100"), P("\u22485.885"), P("\u00b5W"), P("Met; from (6)"), P("Fig. 3")],
     [P("PSRR, noise, corners"), P("\u2014"), P("Not measured"), P("\u2014"), P("Pending"), P("\u2014")]],
    colw=[0.72*inch, 0.56*inch, 0.50*inch, 0.28*inch, 0.72*inch, 0.56*inch]))

# ---------------- VIII. proposed LDO ----------------
E.append(Paragraph("VIII. PROPOSED LDO IMPLEMENTATION AND VERIFICATION PLAN", S["sec"]))
E.append(Paragraph(
    "The amplifier connects into the LDO without internal modification: its output "
    "drives the gate of an external PMOS pass transistor whose source ties to the LDO "
    "input rail, V<sub>ref</sub> = 0.5 V drives the inverting input, and the "
    "non-inverting input takes the feedback voltage from the R1/R2 divider across the "
    "output. The divider sets the regulated output as", S["body"]))
E.append(Paragraph("V<sub>out</sub> = V<sub>ref</sub> ( 1 + R<sub>1</sub>/R<sub>2</sub> ) \u2003\u2003 (7)", S["eq"]))
E.append(Paragraph(
    "so the proposed R<sub>1</sub> = 700 k\u03a9 and R<sub>2</sub> = 500 k\u03a9 with a 0.5 V "
    "reference give V<sub>out</sub> = 0.5(1+1.4) = 1.2 V, with \u22481 \u00b5A "
    "standing divider current. The remaining component proposals from the LDO "
    "implementation manual are listed in Table VII; all are starting values for "
    "simulation, none is a verified result. Note that the LDO implementation manual "
    "itself was not present in the supplied evidence folder; its values are reproduced "
    "from the project brief and must be cross-checked against the manual before "
    "submission. Table VIII defines the verification matrix the LDO must pass; the "
    "large 10 \u00b5F output capacitor and its 16 \u03a9 ESR dominate loop dynamics "
    "and will interact with the amplifier's 51.8\u00b0 margin, which is precisely why "
    "loop-gain simulation precedes any performance claim [2].", S["body"]))
E.append(tab(["TABLE VII", "PROPOSED LDO COMPONENTS (STARTING VALUES \u2014 NOT SIMULATED RESULTS)"],
    [[P("Component / parameter"), P("Proposed value"), P("Purpose"), P("Verification status")],
     [P("Nominal LDO input"), P("1.8 V"), P("Supply during initial closure"), P("Pending")],
     [P("Target output"), P("1.2 V"), P("Regulated rail for loads"), P("Pending")],
     [P("Reference voltage"), P("0.5 V"), P("Set-point for (7)"), P("Pending (block proposed)")],
     [P("Max load current"), P("100 \u00b5A"), P("Design load envelope"), P("Pending")],
     [P("PMOS pass device"), P("W = 60 \u00b5m, L = 0.5 \u00b5m"), P("Sources load at low dropout"), P("Pending (ratings, region)")],
     [P("R<sub>1</sub> / R<sub>2</sub>"), P("700 k\u03a9 / 500 k\u03a9"), P("Feedback divider, (7)"), P("Pending")],
     [P("Output capacitor"), P("10 \u00b5F"), P("Hold-up, dominant load pole"), P("Pending (realizability)")],
     [P("Capacitor ESR"), P("16 \u03a9"), P("ESR zero for compensation"), P("Pending")]],
    colw=[0.90*inch, 0.78*inch, 0.94*inch, 0.70*inch]))
E.append(tab(["TABLE VIII", "LDO VERIFICATION MATRIX (ALL ITEMS CURRENTLY: NOT MEASURED)"],
    [[P("Test"), P("Conditions"), P("Measured quantity"), P("Acceptance criterion")],
     [P("DC closure"), P("V<sub>IN</sub>=1.8 V, no load"), P("V<sub>out</sub>, device regions"), P("1.2 V \u00b1 tol.; all devices saturated")],
     [P("Line sweep"), P("V<sub>IN</sub> swept about 1.8 V"), P("\u0394V<sub>out</sub>/\u0394V<sub>IN</sub>"), P("Line regulation within spec to be set")],
     [P("Load sweep"), P("0\u2192100 \u00b5A"), P("\u0394V<sub>out</sub>/\u0394I<sub>L</sub>"), P("Load regulation within spec; dropout noted")],
     [P("Loop gain / stability"), P("With C<sub>o</sub><sub>u</sub><sub>t</sub>=10 \u00b5F, ESR 16 \u03a9"), P("PM, GM of the loop"), P("PM \u2265 45\u00b0 over load range")],
     [P("Load/line step"), P("Step I<sub>L</sub> and V<sub>IN</sub>"), P("Transient over/undershoot, settling"), P("No oscillation; bounded excursion")],
     [P("Start-up"), P("V<sub>IN</sub> ramp"), P("V<sub>out</sub> trajectory"), P("Monotonic, no latch state")],
     [P("PSRR"), P("AC on V<sub>IN</sub>"), P("V<sub>out</sub>/V<sub>IN</sub> (f)"), P("Spec to be set from load needs")]],
    colw=[0.70*inch, 0.90*inch, 0.94*inch, 0.80*inch]))

# ---------------- IX. limitations & future work ----------------
E.append(Paragraph("IX. LIMITATIONS AND FUTURE WORK", S["sec"]))
E.append(Paragraph(
    "Observed limitations from the evidence: the 51.8\u00b0 phase margin; the "
    "second-stage current and mirror-ratio deviation; the open-loop-only transient "
    "characterization; the unresolved power-measurement definition; and the standalone "
    "testbench operating point (ideal 1.8 V supply, output resting near 0.15 V). "
    "Anticipated \u2014 but not yet observed \u2014 challenges concern the system: "
    "start-up from a weak 0.3\u20131 V source, headroom for the amplifier and pass "
    "device when the stored rail sags, reference accuracy at low voltage, quiescent-"
    "current budget once all blocks are active, loop stability with the 10 \u00b5F/"
    "16 \u03a9 output network, output ripple under duty-cycled loads, and the absence "
    "of corner, mismatch and post-layout verification. Table IX ranks these with "
    "remedies; the prioritized plan is: (1) confirm the power definition, C<sub>C</sub>/"
    "R<sub>Z</sub>/C<sub>L</sub> values and re-tune the compensation to \u226560\u00b0; (2) close "
    "and DC-verify the LDO; (3) loop-gain and transient verification with the output "
    "network; (4) implement the 0.5 V reference [6]; (5) design the conditioning/"
    "boost stage and storage [7]; (6) add the voltage monitor and load switch; "
    "(7) full-PMU simulation under varying input and load; (8) PVT, mismatch and "
    "post-layout checks as tools permit.", S["body"]))
E.append(tab(["TABLE IX", "LIMITATIONS AND FUTURE WORK"],
    [[P("Issue"), P("Technical impact"), P("Proposed remedy"), P("Priority")],
     [P("Phase margin 51.8\u00b0 < 60\u00b0 (observed)"), P("Reduced damping; risk inside LDO loop"), P("Increase C<sub>C</sub> / retune R<sub>Z</sub>; re-verify GBW"), P("High")],
     [P("2nd-stage current \u221236 % vs design (observed)"), P("Lower SR/A<sub>v2</sub> than intended; power bookkeeping"), P("Re-size M7 or accept and re-document bias"), P("Medium")],
     [P("Power definition unconfirmed (observed)"), P("4.73 vs 5.89 \u00b5W ambiguity"), P("Re-measure with explicit V<sub>DD</sub>\u00b7I expression"), P("High")],
     [P("Open-loop transient only (observed)"), P("No closed-loop settling evidence"), P("Unity-gain and LDO load-step benches"), P("High")],
     [P("Harvester headroom 0.3\u20131 V (anticipated)"), P("Cannot feed 1.2 V LDO directly"), P("Boost/SC stage + storage [7]"), P("High")],
     [P("Low-voltage reference accuracy (anticipated)"), P("Output set-point error via (7)"), P("Dedicated reference design [6]"), P("Medium")],
     [P("No PVT/mismatch/post-layout data (observed gap)"), P("Unquantified spread"), P("Corners, Monte Carlo, extraction"), P("Medium")]],
    colw=[0.98*inch, 0.94*inch, 0.94*inch, 0.48*inch]))

# ---------------- X. conclusion ----------------
E.append(Paragraph("X. CONCLUSION", S["sec"]))
E.append(Paragraph(
    "This work set out the architecture of a solar energy-harvesting PMU and completed, "
    "at schematic level in 0.18 \u00b5m CMOS, its central analog block: a two-stage, "
    "PMOS-input, Miller-compensated error amplifier intended for the PMU's LDO. "
    "Square-law hand sizing carried the design to a bias point that simulation confirms "
    "device by device, and the standalone characterization yields 70.5 dB gain, "
    "1.629 MHz unity-gain bandwidth, 87.8 dB CMRR, \u22480.612 V/\u00b5s slew rate and "
    "microwatt-level power from a 1.8 V supply \u2014 figures compatible with its role "
    "as an LDO error amplifier. The characterization is equally clear about what is "
    "not yet achieved: the 51.8\u00b0 phase margin must be raised before loop closure, "
    "the power-measurement definition needs confirmation, and the LDO, reference, "
    "conditioning stage, storage and monitor exist only as a specified plan with "
    "starting component values. The next milestone \u2014 closing the LDO around the "
    "unchanged amplifier and verifying regulation and loop stability against Table "
    "VIII \u2014 will convert the proposed PMU from an architecture into a "
    "demonstrated system.", S["body"]))

# ---------------- references ----------------
E.append(Paragraph("REFERENCES", S["sec"]))
refs = [
 "[1]\u2002P. Patel, B. Mishra, and D. Nagchoudhuri, \u201cA 36 nW power management "
 "unit for solar energy harvesters using 0.18 \u00b5m CMOS,\u201d in Proc. IEEE Int. "
 "Symp. VLSI Design and Test (VDAT), 2017.",
 "[2]\u2002G. A. Rinc\u00f3n-Mora and P. E. Allen, \u201cA low-voltage, low quiescent "
 "current, low drop-out regulator,\u201d IEEE J. Solid-State Circuits, vol. 33, no. 1, "
 "pp. 36\u201344, Jan. 1998.",
 "[3]\u2002B. Razavi, Design of Analog CMOS Integrated Circuits, 2nd ed. New York, NY, "
 "USA: McGraw-Hill, 2017.",
 "[4]\u2002P. R. Gray, P. J. Hurst, S. H. Lewis, and R. G. Meyer, Analysis and Design "
 "of Analog Integrated Circuits, 5th ed. Hoboken, NJ, USA: Wiley, 2009.",
 "[5]\u2002P. E. Allen and D. R. Holberg, CMOS Analog Circuit Design, 3rd ed. New "
 "York, NY, USA: Oxford Univ. Press, 2012.",
 "[6]\u2002M. Seok, G. Kim, D. Blaauw, and D. Sylvester, \u201cA portable 2-transistor "
 "picowatt temperature-compensated voltage reference operating at 0.5 V,\u201d IEEE J. "
 "Solid-State Circuits, vol. 47, no. 10, pp. 2534\u20132545, Oct. 2012.",
 "[7]\u2002M. D. Seeman and S. R. Sanders, \u201cAnalysis and optimization of "
 "switched-capacitor DC\u2013DC converters,\u201d IEEE Trans. Power Electron., vol. 23, "
 "no. 2, pp. 841\u2013851, Mar. 2008.",
]
for r in refs:
    E.append(Paragraph(r, S["ref"]))

doc.build(E)
print("written:", OUT)
