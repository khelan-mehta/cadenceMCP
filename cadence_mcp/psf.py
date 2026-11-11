"""Parser for Spectre PSF-ASCII result files.

Format (validated live against a dc sweep file)::

    HEADER
      "key" value ...
    TYPE
      "TypeName" FLOAT DOUBLE PROP( ... )   # type dictionary, ignored
    SWEEP
      "dc" "sweep" PROP( ... )              # sweep variable name(s)
    TRACE
      "d" "V"                               # ordered signal name / unit-type
      "V0:p" "I"
    VALUE
      "dc" 0.0                              # sweep point, then one line per trace
      "d"  1.8
      ...
    END

For an AC analysis the VALUE numbers are complex: ``(re im)``.
For a transient/dc analysis they are plain floats.

We return a dict:
    {
      "analysis": "dc"|"ac"|"tran"|...,
      "sweep": "<sweep var name>",
      "names": [ ... signal names in trace order ... ],
      "units": { name: unit_code },
      "data": { name: [floats...] },          # includes the sweep var
      "cdata": { name: [(re,im)...] } | None,  # only for complex (ac) results
    }
"""
from __future__ import annotations

import re
from pathlib import Path

_TOK = re.compile(r'"([^"]*)"|(\S+)')


def _tokens(line: str):
    for m in _TOK.finditer(line):
        yield m.group(1) if m.group(1) is not None else m.group(2)


def _to_complex(tok: str):
    # forms: "1.2e-3" or "(1.2e-3 -3.4e-5)"
    if tok.startswith("("):
        return None  # handled separately
    return float(tok)


def parse_psf(path: str | Path) -> dict:
    return parse_psf_text(Path(path).read_text(encoding="utf-8", errors="replace"))


def parse_psf_text(text: str) -> dict:
    lines = text.splitlines()

    section = None
    header: dict = {}
    sweep_names: list[str] = []
    trace_names: list[str] = []
    units: dict[str, str] = {}
    data: dict[str, list[float]] = {}
    cdata: dict[str, list[tuple[float, float]]] = {}
    is_complex = False

    i = 0
    n = len(lines)
    while i < n:
        raw = lines[i].strip()
        i += 1
        if not raw:
            continue
        if raw in ("HEADER", "TYPE", "SWEEP", "TRACE", "VALUE", "END"):
            section = raw
            continue

        if section == "HEADER":
            toks = list(_tokens(raw))
            if len(toks) >= 2:
                key = toks[0]
                val = toks[1]
                try:
                    header[key] = float(val)
                except ValueError:
                    header[key] = val

        elif section == "SWEEP":
            toks = list(_tokens(raw))
            if toks and not raw.startswith("PROP") and toks[0] not in ("PROP(",):
                # first token is the sweep variable name
                if toks[0] != ")" and not raw.startswith('"key"') and not raw.startswith('"units"') \
                   and not raw.startswith('"sweep_direction"') and not raw.startswith('"plot"') \
                   and not raw.startswith('"grid"'):
                    sweep_names.append(toks[0])

        elif section == "TYPE":
            pass  # type dictionary not needed

        elif section == "TRACE":
            toks = list(_tokens(raw))
            if len(toks) >= 2 and not raw.startswith("PROP"):
                name, unit = toks[0], toks[1]
                trace_names.append(name)
                units[name] = unit

        elif section == "VALUE":
            toks = list(_tokens(raw))
            if len(toks) < 2:
                continue
            name = toks[0]
            if "(" in raw and ")" in raw:
                # complex: "name" (re im)
                inner = raw[raw.find("(") + 1:raw.find(")")].split()
                if len(inner) >= 2:
                    try:
                        re_v = float(inner[0]); im_v = float(inner[1])
                    except ValueError:
                        continue
                    is_complex = True
                    cdata.setdefault(name, []).append((re_v, im_v))
                    data.setdefault(name, []).append((re_v ** 2 + im_v ** 2) ** 0.5)
            else:
                try:
                    data.setdefault(name, []).append(float(toks[1]))
                except ValueError:
                    pass

    sweep = sweep_names[0] if sweep_names else (trace_names[0] if trace_names else "sweep")
    names = [sweep] + [t for t in trace_names if t != sweep]
    analysis = str(header.get("analysis type", "")).strip()

    return {
        "analysis": analysis,
        "sweep": sweep,
        "names": names,
        "units": units,
        "header": header,
        "data": data,
        "cdata": cdata if is_complex else None,
    }
