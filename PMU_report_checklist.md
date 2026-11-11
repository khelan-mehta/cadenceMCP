# PMU / Error-Amplifier Report — Figure Checklist & Technical-Consistency Checklist

Companion to `PMU_ErrorAmp_IEEE_Report.pdf` and `newRequest/report_build/pmu_report.tex`.
Date: 2026-10-25. Evidence base: `newRequest/` (Review II presentation PDF + Cadence
screenshot PNGs). "LDO Implementation Manual" was **not present** in the evidence
folder — its values are reproduced from the project brief and must be cross-checked.

---

## Part 1 — Figure checklist

| Fig. | Caption (as used in the report) | Evidence file supplying it | Status |
|---|---|---|---|
| 1 | Proposed PMU block diagram: solar-cell equivalent model feeding reference, error amp, pass element, R1/R2 divider, C_L = 10 µF, voltage monitor, load switch P1 | Review II PDF, slide 6 (rendered) | In report ✔ |
| 2 | Virtuoso schematic of the two-stage amplifier (gpdk180) | `...Unit.png` (clean schematic capture) | In report ✔ |
| 3 | DC operating point annotated on schematic; i(V_DD) = 3.26964 µA, all devices region 2 | `...Unit (1).png` | In report ✔ |
| 4 | Open-loop magnitude; 70.5 dB; UGB marker 1.62875 MHz; −3 dB marker 550.915 Hz | `...Unit (5).png` (UGB) — −3 dB marker variant is `...(4).png` | In report ✔ |
| 5 | Phase + magnitude at unity gain: 51.7764° @ 0.193 dB → PM ≈ 51.8° | `...Unit (6).png` | In report ✔ |
| 6 | CMRR vs frequency: 87.8133 dB at 10 Hz | `...Unit (7).png` | In report ✔ |
| 7 | Open-loop transient, ±1 mV differential at 0.5 V CM — output clips rail-to-rail | `...Unit (2).png` | In report ✔ |
| — | Proposed LDO schematic | **Does not exist yet** — draw when LDO is entered in Virtuoso | Pending |
| — | LDO DC regulation / load & line sweeps | Pending LDO simulation | Pending |
| — | LDO loop-gain & phase-margin plots | Pending LDO simulation | Pending |
| — | Load-step / input-step waveforms | Pending LDO simulation | Pending |
| — | Complete PMU schematic / post-layout view | Only after those stages actually exist | Pending |

Never substitute a textbook or internet image for the pending figures; generate them
from the actual Cadence database when the corresponding block is built.

## Part 2 — Values that are VERIFIED by the evidence (safe to state)

| Quantity | Value | Evidence |
|---|---|---|
| Technology / tool | gpdk180, Cadence Virtuoso ADE + Spectre | ADE window titles ("gpdk180 err schematic", "Simulator: spectre") |
| Supply / common mode | 1.8 V / 0.5 V | ADE captures; transient input waveforms at 500 mV |
| DC open-loop gain | ≈ 70.5 dB | AC plot flat region |
| −3 dB bandwidth | 550.915 Hz | marker at 67.5 dB |
| Unity-gain bandwidth | 1.62875 MHz | marker at 0 dB |
| Phase margin | ≈ 51.78° (51.7764° @ 193.305 mdB) | phase plot markers |
| CMRR @ 10 Hz | 87.8133 dB | CMRR plot marker; expression visible in plot header |
| Slew rate | 611.877 kV/s ≈ 0.612 V/µs | ADE Outputs window, tran 0–2 ms |
| Supply current (DC op) | 3.26964 µA | Vdd annotation, DC op schematic |
| ADE "Power" output | 4.7345 µW | ADE Outputs window |
| Per-device op point | Table V of the report | annotated schematic |
| Sizing table (W, L, I_D, V_ov) | Table IV of the report | presentation "Calculated Table" |
| I_ref node voltage | 1.15083 V | DC op annotation |

## Part 3 — UNVERIFIED items (placeholders in the report — resolve before submission)

1. **[INSERT VERIFIED C_C / R_Z / C_L FROM CADENCE]** — component values are not
   legible in any capture. Obtain: open schematic → select Cc, Rz, CL → `q`
   (properties), record values; update Section V-B and the C_C ≈ 0.63 pF
   consistency check.
2. **[CONFIRM ADE POWER EXPRESSION]** — the Outputs pane shows `Power  4.7345u`
   but not its expression, and the enabled dc analysis in that session was a
   **V_dd sweep (0→1.8 V)**, so the averaging basis is unknown. Obtain: ADE →
   Outputs → Setup, copy the exact expression; then reconcile with
   V_DD·I_DD = 5.885 µW. Until then the report deliberately carries **both**
   numbers, clearly distinguished (Eq. 6 / Table VI).
3. **LDO Implementation Manual** — absent from `newRequest/`. The proposed values
   (1.8 V in, 1.2 V out, 0.5 V ref, 100 µA, 60 µm/0.5 µm pass PMOS,
   700 kΩ/500 kΩ, 10 µF, 16 Ω ESR) come from the project brief; cross-check
   against the manual and cite it properly.
4. Transient drive frequency in Fig. 7 is read from the waveform (~1 kHz over
   10 ms); confirm the exact vsin parameters from the testbench.

## Part 4 — Missing simulations (must NOT be claimed)

- PSRR, noise, output swing, ICMR sweeps — not evidenced.
- Closed-loop (unity-gain or LDO) transient / load-step — not evidenced; the only
  transient is **open-loop and clipping**.
- LDO DC closure, line/load regulation, loop gain, start-up — none performed.
- Corners (SS/FF/SF/FS), temperature sweeps, Monte Carlo / mismatch — none.
- Layout, DRC/LVS, parasitic extraction, post-layout sims — none.
- Boost/switched-capacitor stage, voltage reference, voltage monitor — design not
  started; only block-level intent exists.

## Part 5 — Claims that must NOT be made (and what to say instead)

| Forbidden claim | Say instead |
|---|---|
| "All design targets were met" | Gain/GBW/CMRR/SR/power targets met; **phase margin 51.8° is below the 60° guideline** and will be retuned before loop closure |
| "The LDO regulates 1.2 V at 100 µA" | The LDO is **proposed**; Eq. (7) predicts 1.2 V from the 700k/500k divider, pending simulation |
| "The PMU operates from the 0.3–1 V harvester" | The amplifier was characterized from an **ideal 1.8 V supply**; a boost/conditioning stage is required and not yet designed |
| "Power consumption is 4.73 µW" (as a settled fact) | ADE reports 4.7345 µW (definition pending); the DC operating point implies 5.885 µW; both < 10 µW budget |
| "Transient response verifies settling/stability" | The transient is an **open-loop clipping test**; closed-loop settling is future work |
| "Second stage biased at 2 µA as designed" | Simulated second-stage current is **1.273 µA (−36 % vs design)**; total supply current 3.27 µA vs 4 µA planned |
| Any post-layout / PVT / Monte Carlo result | Not performed |
| "Novel / optimal / superior to published work" | Positioned as a strong-inversion alternative to the subthreshold reference design [1], with the trade-offs stated |

## Part 6 — Consistency cross-checks already applied in the report

- gpdk180 + Virtuoso/Spectre named consistently throughout; no gpdk090/other PDK.
- 51.8° reported as a shortfall, with the presentation's late target relaxation
  (45–60°) disclosed rather than hidden.
- GBW sanity: A_v·f_−3dB ≈ 3350 × 551 Hz ≈ 1.85 MHz vs measured 1.629 MHz —
  first-order consistent.
- Implied C_C ≈ g_m1/(2π·GBW) ≈ 0.63 pF presented **only** as a derived
  consistency check, never as the drawn value.
- Divider check: 0.5 V × (1 + 700/500) = 1.2 V ✔ (Eq. 7).
- Literature table uses NR for every value the cited source copy at hand does not
  establish; only verifiable references retained (the presentation's reference
  list items that could not be bibliographically confirmed were omitted rather
  than guessed).
- Author/institution details taken from the presentation title slide, not invented.
