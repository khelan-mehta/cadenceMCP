"""Measurement / parameter-extraction toolbox.

Operates on plain Python lists coming out of the PSF parser. Kept dependency-light
(numpy used only where it clearly helps: FFT for THD).
"""
from __future__ import annotations

import math
from typing import Sequence

try:
    import numpy as _np
except Exception:  # pragma: no cover
    _np = None


# --------------------------------------------------------------------------- #
#  generic helpers
# --------------------------------------------------------------------------- #
def interp(x: Sequence[float], y: Sequence[float], x0: float) -> float:
    """Linear interpolation of y at x0 (x assumed monotonic increasing)."""
    n = len(x)
    if n == 0:
        return float("nan")
    if x0 <= x[0]:
        return y[0]
    if x0 >= x[-1]:
        return y[-1]
    for i in range(1, n):
        if x[i] >= x0:
            t = (x0 - x[i - 1]) / (x[i] - x[i - 1]) if x[i] != x[i - 1] else 0.0
            return y[i - 1] + t * (y[i] - y[i - 1])
    return y[-1]


def deriv(x: Sequence[float], y: Sequence[float]) -> list[float]:
    """Central-difference derivative dy/dx."""
    n = len(x)
    d = [0.0] * n
    for i in range(n):
        if i == 0:
            d[i] = (y[1] - y[0]) / (x[1] - x[0]) if n > 1 and x[1] != x[0] else 0.0
        elif i == n - 1:
            d[i] = (y[-1] - y[-2]) / (x[-1] - x[-2]) if x[-1] != x[-2] else 0.0
        else:
            dx = x[i + 1] - x[i - 1]
            d[i] = (y[i + 1] - y[i - 1]) / dx if dx else 0.0
    return d


def cross(x: Sequence[float], y: Sequence[float], level: float, edge: str = "either") -> float | None:
    """First x where y crosses `level`."""
    for i in range(1, len(y)):
        a, b = y[i - 1], y[i]
        if (a - level) == 0:
            return x[i - 1]
        if (a - level) * (b - level) < 0:
            rising = b > a
            if edge == "rising" and not rising:
                continue
            if edge == "falling" and rising:
                continue
            t = (level - a) / (b - a)
            return x[i - 1] + t * (x[i] - x[i - 1])
    return None


def db20(mag: Sequence[float]) -> list[float]:
    return [20.0 * math.log10(m) if m > 0 else -300.0 for m in mag]


def unwrap_deg(phase: Sequence[float]) -> list[float]:
    """Unwrap a phase array (degrees) so jumps stay within ±180°."""
    if not phase:
        return []
    out = [phase[0]]
    off = 0.0
    for i in range(1, len(phase)):
        d = phase[i] - phase[i - 1]
        if d > 180:
            off -= 360
        elif d < -180:
            off += 360
        out.append(phase[i] + off)
    return out


# --------------------------------------------------------------------------- #
#  MOS parameter extraction  (Exp 2)
# --------------------------------------------------------------------------- #
def extract_vt0(vgs: Sequence[float], idd: Sequence[float]) -> dict:
    """Threshold via linear extrapolation at the point of maximum transconductance."""
    idd = [abs(v) for v in idd]
    g = deriv(vgs, idd)
    imax = max(range(len(g)), key=lambda i: g[i])
    gm_max = g[imax]
    if gm_max <= 0:
        return {"vt0": float("nan"), "gm_max": gm_max}
    # tangent line: id = gm_max*(vgs - vt0) -> vt0 = vgs* - id*/gm_max
    vt0 = vgs[imax] - idd[imax] / gm_max
    return {"vt0": vt0, "gm_max": gm_max, "vgs_at_gm_max": vgs[imax]}


def extract_kn(vgs: Sequence[float], idd: Sequence[float], vt0: float) -> dict:
    """Kn = 2*slope^2 of sqrt(Id) vs Vgs in strong inversion (µCox·W/L)."""
    idd = [abs(v) for v in idd]
    xs, ys = [], []
    for v, i in zip(vgs, idd):
        if v > vt0 + 0.1 and i > 0:
            xs.append(v)
            ys.append(math.sqrt(i))
    if len(xs) < 2:
        return {"kn": float("nan")}
    # least-squares slope
    n = len(xs)
    sx = sum(xs); sy = sum(ys); sxx = sum(a * a for a in xs); sxy = sum(a * b for a, b in zip(xs, ys))
    slope = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    return {"kn": 2.0 * slope * slope, "sqrt_slope": slope}


def extract_lambda(vds: Sequence[float], idd: Sequence[float], sat_frac: float = 0.6) -> dict:
    """Channel-length modulation λ from Id–Vds slope in saturation.

    In saturation Id ≈ Id_sat·(1+λ·Vds) so λ = (dId/dVds)/Id at high Vds, and
    1/λ is the Vds-axis intercept of the extrapolated saturation line.
    """
    idd = [abs(v) for v in idd]
    n = len(vds)
    i0 = int(n * sat_frac)
    xs = vds[i0:]; ys = idd[i0:]
    if len(xs) < 2:
        return {"lambda": float("nan"), "VA": float("nan")}
    m = len(xs)
    sx = sum(xs); sy = sum(ys); sxx = sum(a * a for a in xs); sxy = sum(a * b for a, b in zip(xs, ys))
    slope = (m * sxy - sx * sy) / (m * sxx - sx * sx)
    inter = (sy - slope * sx) / m
    if inter == 0:
        return {"lambda": float("nan"), "VA": float("nan")}
    lam = slope / inter
    VA = inter / slope if slope else float("inf")   # Early voltage magnitude = 1/lambda
    return {"lambda": lam, "VA": abs(VA), "gds_sat": slope}


# --------------------------------------------------------------------------- #
#  Amplifier metrics  (Exp 4-9)
# --------------------------------------------------------------------------- #
def ac_gain_bw(freq: Sequence[float], mag: Sequence[float]) -> dict:
    """DC gain (dB), -3 dB bandwidth, unity-gain freq from an AC magnitude sweep."""
    if not freq:
        return {}
    gdb = db20(mag)
    dc_gain_db = gdb[0]
    dc_gain = mag[0]
    # -3dB bandwidth
    f3 = cross(freq, gdb, dc_gain_db - 3.0, edge="falling")
    # unity gain (0 dB)
    fu = cross(freq, gdb, 0.0, edge="falling")
    gbw = dc_gain * f3 if (f3 and dc_gain) else None
    return {
        "dc_gain_db": dc_gain_db,
        "dc_gain_vv": dc_gain,
        "bandwidth_hz": f3,
        "unity_gain_hz": fu,
        "gbw_hz": gbw,
    }


def phase_margin(freq: Sequence[float], mag: Sequence[float], phase_deg: Sequence[float]) -> dict:
    gdb = db20(mag)
    fu = cross(freq, gdb, 0.0, edge="falling")
    if fu is None:
        return {"phase_margin_deg": None, "unity_gain_hz": None}
    uw = unwrap_deg(phase_deg)
    ph_dc = uw[0]
    ph_ugf = interp(freq, uw, fu)
    # excess lag accumulated from DC to the unity-gain frequency (convention-free:
    # the DC inversion of the amplifier is factored out). PM = 180 - excess_lag.
    excess_lag = abs(ph_dc - ph_ugf)
    pm = 180.0 - excess_lag
    return {"phase_margin_deg": pm, "excess_lag_deg": excess_lag,
            "phase_at_ugf_deg": ph_ugf, "unity_gain_hz": fu}


def slew_rate(t: Sequence[float], v: Sequence[float]) -> dict:
    """Max |dV/dt| in V/µs from a transient step response."""
    d = deriv(t, v)
    sr = max(abs(x) for x in d) if d else float("nan")
    return {"slew_rate_v_per_us": sr / 1e6, "slew_rate_v_per_s": sr}


def thd(t: Sequence[float], v: Sequence[float], f0: float, nharm: int = 7) -> dict:
    """Total harmonic distortion from a steady-state transient via FFT."""
    if _np is None or len(t) < 16:
        return {"thd_percent": None}
    t = _np.asarray(t); v = _np.asarray(v)
    # resample to uniform grid over an integer number of periods
    tspan = t[-1] - t[0]
    nper = max(1, int(round(tspan * f0)))
    N = 1 << int(math.ceil(math.log2(max(256, nper * 64))))
    tu = _np.linspace(t[0], t[0] + nper / f0, N, endpoint=False)
    vu = _np.interp(tu, t, v)
    vu = vu - vu.mean()
    win = _np.hanning(N)
    sp = _np.abs(_np.fft.rfft(vu * win))
    fund_bin = nper
    if fund_bin >= len(sp):
        return {"thd_percent": None}
    fund = sp[fund_bin]
    harm = 0.0
    for k in range(2, nharm + 1):
        b = fund_bin * k
        if b < len(sp):
            harm += sp[b] ** 2
    thd_v = math.sqrt(harm) / fund if fund > 0 else float("nan")
    return {"thd_percent": 100.0 * thd_v, "thd_db": 20 * math.log10(thd_v) if thd_v > 0 else None}


def cmrr(adm_db: float, acm_db: float) -> dict:
    return {"cmrr_db": adm_db - acm_db}
