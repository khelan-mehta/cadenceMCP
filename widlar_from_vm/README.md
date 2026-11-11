# Widlar current mirror - files brought back from the Cadence VM (2026-10-15)

## widlar_lib/  (Cadence OpenAccess library cells)
- widlar/schematic        - flat annotated test schematic (sources + mirror + loads)
- widlar_core/schematic   - LVS reference core (M1, M2, Rs + IREF/IOUT/GND pins)
- widlar_core/symbol      - generated symbol
- widlar_tb/schematic     - hierarchical testbench
- widlar_lay/layout       - DRC-clean, LVS-matched layout
- widlar_lay/extracted    - Diva extraction result

To use on any Virtuoso install: copy the whole widlar_lib/ folder (with
cdsinfo.tag + data.dm) somewhere and add to cds.lib:
    DEFINE widlar_lib /path/to/widlar_lib
(technology: gpdk090 must be present and bound.)

## mcp_runs/  (Spectre simulation runs - deck + raw results)
- widlar_swrs/   input.scs + psf/  - ideal-RS sweep (IOUT vs RS, 1 uA @ 271 kOhm)
- widlar_main/   input.scs + psf/ + op.info - op point, segL sweep, VDD sweep, transient
- widlar_compl/  input.scs + psf/  - output-compliance sweep
PSF files are psfascii - readable as text, or open the psf/ dir in ViVA.

## mcp_skill_runs/  (physical verification)
- widlar_fix4/CMPRUN/  - LVS compare run: layout/netlist + schematic/netlist
  (auLvs format, dumped from the extracted view), divaLVS.rul, lvsbin.log
  ("The net-lists match"), xref.out
- widlar_fix4/         - also holds the Diva DRC/extract run logs (0 errors)
- widlar_fix2/LVSrun/  - earlier LVS iteration kept for reference

Host-side companions already in this project: designs/widlar/ (all build
scripts, shots/, report figures), Widlar_IEEE_Report_Mangal_Mehta.pdf,
widlar_report.tex.
