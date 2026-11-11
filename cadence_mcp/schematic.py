"""Lightweight SVG schematic generation for each experiment topology.

Not a full schematic capture — a clean, labelled diagram of the canonical
circuit for each experiment with the *current parameter values* annotated, so
the dashboard can show "what am I simulating" next to the results.
"""
from __future__ import annotations

from . import experiments


def _svg(w, h, body, title=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
            f'font-family="ui-monospace,Consolas,monospace" font-size="13">'
            f'<rect width="{w}" height="{h}" fill="#0d1117"/>'
            f'<text x="12" y="22" fill="#58a6ff" font-size="15">{title}</text>'
            f'{body}</svg>')


def _nmos(x, y, label, ports=("D", "G", "S")):
    # simple MOS glyph
    return (
        f'<g stroke="#7ee787" stroke-width="2" fill="none">'
        f'<line x1="{x-24}" y1="{y}" x2="{x-6}" y2="{y}"/>'          # gate lead
        f'<line x1="{x-6}" y1="{y-18}" x2="{x-6}" y2="{y+18}"/>'     # gate bar
        f'<line x1="{x}" y1="{y-18}" x2="{x}" y2="{y+18}"/>'         # channel
        f'<line x1="{x}" y1="{y-18}" x2="{x+18}" y2="{y-18}"/>'      # drain
        f'<line x1="{x+18}" y1="{y-18}" x2="{x+18}" y2="{y-34}"/>'
        f'<line x1="{x}" y1="{y+18}" x2="{x+18}" y2="{y+18}"/>'      # source
        f'<line x1="{x+18}" y1="{y+18}" x2="{x+18}" y2="{y+34}"/>'
        f'</g>'
        f'<text x="{x-4}" y="{y+4}" fill="#e6edf3" font-size="12">{label}</text>'
    )


def _label(x, y, t, color="#8b949e"):
    return f'<text x="{x}" y="{y}" fill="{color}">{t}</text>'


def render(exp_id: str, params: dict | None = None) -> str:
    exp = experiments.get(exp_id)
    if exp is None:
        return _svg(400, 100, _label(20, 60, f"unknown experiment {exp_id}", "#f85149"))
    p = dict(exp.default_params())
    if params:
        p.update(params)

    title = f"Exp {exp.id}: {exp.title}"

    if exp_id == "2":
        body = (
            _nmos(200, 150, "M0")
            + _label(120, 155, f"Vg={p.get('vgs_fixed')}V")
            + _label(240, 120, f"Vd={p.get('vdd')}V")
            + _label(150, 235, f"Vb={p.get('vbs')}V")
            + _label(20, 300, f"{p.get('device')}  W={p.get('w')} L={p.get('l')}")
            + _label(20, 320, "Sweeps: Id–Vgs, Id–Vds → VT0, Kn, γ, λ")
        )
        return _svg(460, 340, body, title)

    if exp_id in ("4", "5", "7"):
        rd = p.get("rd", "RD")
        body = (
            _label(180, 40, f"VDD={p.get('vdd')}V")
            + f'<line x1="200" y1="50" x2="200" y2="90" stroke="#f0883e" stroke-width="2"/>'
            + _label(210, 80, f"RD={rd}")
            + f'<rect x="188" y="90" width="24" height="40" fill="none" stroke="#f0883e" stroke-width="2"/>'
            + f'<line x1="200" y1="130" x2="200" y2="150" stroke="#f0883e" stroke-width="2"/>'
            + _nmos(200, 175, "M0")
            + _label(90, 180, f"Vin dc={p.get('vin_dc')}V")
            + _label(230, 150, "out")
            + (_label(120, 235, f"Rs={p.get('rs')}") if exp_id == "5" else "")
            + _label(20, 300, f"{p.get('device')} W={p.get('w')} L={p.get('l')}  "
                              f"load={p.get('load_type','resistive')}")
            + _label(20, 320, f"Target: Gain 20 dB, P<1 mW | AC/DC/Tran")
        )
        return _svg(460, 340, body, title)

    if exp_id in ("8", "9"):
        body = (
            _label(140, 40, f"VDD={p.get('vdd')}V")
            + _nmos(150, 150, "M1") + _nmos(250, 150, "M2")
            + _label(80, 155, "in+") + _label(300, 155, "in-")
            + _label(180, 240, f"Itail={p.get('itail', p.get('ibias'))}")
            + f'<circle cx="200" cy="235" r="14" fill="none" stroke="#7ee787" stroke-width="2"/>'
            + _label(20, 300, ("Diff pair + PMOS load" if exp_id == "8"
                               else "2-stage: diff pair + CS + Miller Cc"))
            + _label(20, 320, exp.spec[:70])
        )
        return _svg(460, 340, body, title)

    # generic
    body = _label(20, 60, exp.title) + _label(20, 90, exp.spec[:80])
    return _svg(500, 160, body, title)
