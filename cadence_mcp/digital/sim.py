"""Simulate the 8-bit CPU (pure-Python Amaranth sim), capture a per-cycle trace,
a VCD file, cache statistics, final memory, and export synthesizable Verilog.
"""
from __future__ import annotations

import io
from pathlib import Path

from amaranth.sim import Simulator

from .. import config
from .assembler import assemble
from .cpu import CPU


def run_program(source: str, max_cycles: int = 2000, cache_lines: int = 8,
                line_bytes: int = 4, miss_penalty: int = 8,
                vcd_name: str | None = None) -> dict:
    image, meta = assemble(source)
    dut = CPU(program=image, cache_lines=cache_lines, line_bytes=line_bytes,
              miss_penalty=miss_penalty)

    trace = {k: [] for k in ("cycle", "pc", "acc", "out", "zero", "halted",
                             "instret", "cache_hits", "cache_misses", "stall_cycles")}
    final = {}

    async def tb(ctx):
        for c in range(max_cycles):
            trace["cycle"].append(c)
            trace["pc"].append(int(ctx.get(dut.pc)))
            trace["acc"].append(int(ctx.get(dut.acc)))
            trace["out"].append(int(ctx.get(dut.out_port)))
            trace["zero"].append(int(ctx.get(dut.zero)))
            trace["halted"].append(int(ctx.get(dut.halted)))
            trace["instret"].append(int(ctx.get(dut.instret)))
            trace["cache_hits"].append(int(ctx.get(dut.cache_hits)))
            trace["cache_misses"].append(int(ctx.get(dut.cache_misses)))
            trace["stall_cycles"].append(int(ctx.get(dut.stall_cycles)))
            if int(ctx.get(dut.halted)):
                break
            await ctx.tick()
        # snapshot final register + memory state
        final["acc"] = int(ctx.get(dut.acc))
        final["pc"] = int(ctx.get(dut.pc))
        final["out"] = int(ctx.get(dut.out_port))
        final["instret"] = int(ctx.get(dut.instret))
        final["cache_hits"] = int(ctx.get(dut.cache_hits))
        final["cache_misses"] = int(ctx.get(dut.cache_misses))
        final["stall_cycles"] = int(ctx.get(dut.stall_cycles))
        final["memory"] = [int(ctx.get(dut._ram[i])) for i in range(dut.mem_size)]

    sim = Simulator(dut)
    sim.add_clock(1e-8)  # 100 MHz nominal
    sim.add_testbench(tb)

    vcd_path = None
    if vcd_name:
        vdir = config.DATA_DIR / "digital"
        vdir.mkdir(parents=True, exist_ok=True)
        vcd_path = vdir / f"{vcd_name}.vcd"
        with sim.write_vcd(str(vcd_path)):
            sim.run()
    else:
        sim.run()

    hits = final.get("cache_hits", 0)
    misses = final.get("cache_misses", 0)
    total = hits + misses
    hit_rate = (hits / total) if total else 0.0
    base_cycles = len(trace["cycle"])
    final["hit_rate"] = hit_rate
    final["effective_cycles"] = base_cycles + final.get("stall_cycles", 0)

    return {
        "ok": True,
        "labels": meta["labels"],
        "image": image,
        "trace": trace,
        "final": final,
        "halted": bool(trace["halted"][-1]) if trace["halted"] else False,
        "cycles_run": base_cycles,
        "vcd": str(vcd_path) if vcd_path else None,
        "cache_cfg": {"lines": cache_lines, "line_bytes": line_bytes,
                      "size_bytes": cache_lines * line_bytes, "miss_penalty": miss_penalty},
    }


def export_verilog() -> str:
    """Emit synthesizable Verilog for the CPU core (via Amaranth's yosys backend)."""
    from amaranth.back import verilog
    dut = CPU()
    ports = [dut.pc, dut.acc, dut.out_port, dut.zero, dut.halted,
             dut.cache_hits, dut.cache_misses, dut.instret]
    return verilog.convert(dut, name="cpu8", ports=ports)


# a couple of ready-made demo programs
DEMOS = {
    "sum_1_to_n": """
; OUT = 1+2+...+N  (loop shows cache reuse of sum/i/n)
        LDI 0
        STA sum
        LDI 1
        STA i
loop:
        LDA i
        SUB n
        JZ  done        ; while i != n+1... (approx)
        LDA sum
        ADD i
        STA sum
        LDA i
        INC
        STA i
        JMP loop
done:
        LDA sum
        OUT
        HLT
sum:    .byte 0
i:      .byte 0
n:      .byte 6
""",
    "fibonacci": """
; compute Fibonacci, leave last value in OUT
        LDI 0
        STA a
        LDI 1
        STA b
        LDI 8
        STA cnt
loop:
        LDA a
        ADD b
        STA c
        LDA b
        STA a
        LDA c
        STA b
        LDA cnt
        DEC
        STA cnt
        JNZ loop
        LDA b
        OUT
        HLT
a:   .byte 0
b:   .byte 0
c:   .byte 0
cnt: .byte 0
""",
    "count_down": """
        LDI 10
loop:
        OUT
        DEC
        JNZ loop
        OUT
        HLT
""",
}
