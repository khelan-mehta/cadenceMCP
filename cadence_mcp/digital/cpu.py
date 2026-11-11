"""An 8-bit accumulator CPU with a direct-mapped cache in front of 256 B RAM.

Written in Amaranth HDL so it can be (a) simulated in pure Python with VCD output
and (b) exported to synthesizable Verilog. Deliberately small but real: a
multi-cycle control FSM, a flat RAM, and a genuine direct-mapped cache structure
(valid + tag arrays) that tracks hits/misses and accumulates a miss-penalty cycle
count — a standard functional+timing split used by architectural simulators.

ISA (2-byte instructions: [opcode][operand]):
  NOP LDI LDA STA ADD SUB AND OR XOR INC DEC JMP JZ JNZ OUT HLT
"""
from __future__ import annotations

from amaranth.hdl import Array, Elaboratable, Module, Signal

# opcode table (shared with the assembler)
OPCODES = {
    "NOP": 0x00, "LDI": 0x01, "LDA": 0x02, "STA": 0x03, "ADD": 0x04,
    "SUB": 0x05, "AND": 0x06, "OR": 0x07, "XOR": 0x08, "INC": 0x0D,
    "DEC": 0x0E, "JMP": 0x09, "JZ": 0x0A, "JNZ": 0x0B, "OUT": 0x0C,
    "HLT": 0x0F,
}
# which opcodes take an operand byte
HAS_OPERAND = {"LDI", "LDA", "STA", "ADD", "SUB", "AND", "OR", "XOR",
               "JMP", "JZ", "JNZ"}


class CPU(Elaboratable):
    def __init__(self, program=None, mem_size=256, cache_lines=8, line_bytes=4,
                 miss_penalty=8):
        self.mem_size = mem_size
        self.cache_lines = cache_lines
        self.line_bytes = line_bytes
        self.miss_penalty = miss_penalty
        init = list(program or [])
        init = (init + [0] * mem_size)[:mem_size]
        self._init = init

        # architectural / observable state
        self.pc = Signal(8)
        self.acc = Signal(8)
        self.out_port = Signal(8)
        self.zero = Signal()
        self.halted = Signal()
        self.ir = Signal(8)
        self.operand = Signal(8)
        # counters
        self.cycles = Signal(32)
        self.instret = Signal(32)
        self.cache_hits = Signal(32)
        self.cache_misses = Signal(32)
        self.stall_cycles = Signal(32)   # accumulated miss penalty

    def elaborate(self, platform):
        m = Module()

        # ---- RAM: async read, sync write (small, fine for sim/export) ----
        ram = Array(Signal(8, init=self._init[i], name=f"ram{i}")
                    for i in range(self.mem_size))

        # ---- cache tag/valid arrays (direct-mapped) ----
        idx_bits = (self.cache_lines - 1).bit_length()
        off_bits = (self.line_bytes - 1).bit_length()
        valid = Array(Signal(name=f"v{i}") for i in range(self.cache_lines))
        tags = Array(Signal(8 - idx_bits - off_bits, name=f"t{i}")
                     for i in range(self.cache_lines))

        # single cache access port driven by the current FSM state
        cacc_en = Signal()
        cacc_addr = Signal(8)
        idx = cacc_addr[off_bits:off_bits + idx_bits]
        tag = cacc_addr[off_bits + idx_bits:]
        hit = Signal()
        m.d.comb += hit.eq(valid[idx] & (tags[idx] == tag))
        with m.If(cacc_en):
            with m.If(hit):
                m.d.sync += self.cache_hits.eq(self.cache_hits + 1)
            with m.Else():
                m.d.sync += [
                    self.cache_misses.eq(self.cache_misses + 1),
                    self.stall_cycles.eq(self.stall_cycles + self.miss_penalty),
                    valid[idx].eq(1),
                    tags[idx].eq(tag),
                ]

        # async data read from RAM at the cache-access address
        rdata = Signal(8)
        m.d.comb += rdata.eq(ram[cacc_addr])

        # cycle counter (runs until halt)
        with m.If(~self.halted):
            m.d.sync += self.cycles.eq(self.cycles + 1)

        alu_z = lambda val: self.zero.eq(val == 0)

        with m.FSM(init="F1"):
            # fetch opcode
            with m.State("F1"):
                m.d.comb += [cacc_en.eq(1), cacc_addr.eq(self.pc)]
                m.d.sync += self.ir.eq(rdata)
                m.next = "F2"
            # fetch operand
            with m.State("F2"):
                m.d.comb += [cacc_en.eq(1), cacc_addr.eq(self.pc + 1)]
                m.d.sync += self.operand.eq(rdata)
                m.next = "EX"
            # execute
            with m.State("EX"):
                m.d.sync += [self.pc.eq(self.pc + 2),
                             self.instret.eq(self.instret + 1)]
                op = self.ir
                with m.Switch(op):
                    with m.Case(OPCODES["LDI"]):
                        m.d.sync += [self.acc.eq(self.operand), alu_z(self.operand)]
                    with m.Case(OPCODES["LDA"]):
                        m.d.comb += [cacc_en.eq(1), cacc_addr.eq(self.operand)]
                        m.d.sync += [self.acc.eq(rdata), alu_z(rdata)]
                    with m.Case(OPCODES["STA"]):
                        m.d.comb += [cacc_en.eq(1), cacc_addr.eq(self.operand)]
                        m.d.sync += ram[self.operand].eq(self.acc)
                    with m.Case(OPCODES["ADD"]):
                        m.d.comb += [cacc_en.eq(1), cacc_addr.eq(self.operand)]
                        res = (self.acc + rdata)[:8]
                        m.d.sync += [self.acc.eq(res), alu_z(res)]
                    with m.Case(OPCODES["SUB"]):
                        m.d.comb += [cacc_en.eq(1), cacc_addr.eq(self.operand)]
                        res = (self.acc - rdata)[:8]
                        m.d.sync += [self.acc.eq(res), alu_z(res)]
                    with m.Case(OPCODES["AND"]):
                        m.d.comb += [cacc_en.eq(1), cacc_addr.eq(self.operand)]
                        res = self.acc & rdata
                        m.d.sync += [self.acc.eq(res), alu_z(res)]
                    with m.Case(OPCODES["OR"]):
                        m.d.comb += [cacc_en.eq(1), cacc_addr.eq(self.operand)]
                        res = self.acc | rdata
                        m.d.sync += [self.acc.eq(res), alu_z(res)]
                    with m.Case(OPCODES["XOR"]):
                        m.d.comb += [cacc_en.eq(1), cacc_addr.eq(self.operand)]
                        res = self.acc ^ rdata
                        m.d.sync += [self.acc.eq(res), alu_z(res)]
                    with m.Case(OPCODES["INC"]):
                        res = (self.acc + 1)[:8]
                        m.d.sync += [self.acc.eq(res), alu_z(res)]
                    with m.Case(OPCODES["DEC"]):
                        res = (self.acc - 1)[:8]
                        m.d.sync += [self.acc.eq(res), alu_z(res)]
                    with m.Case(OPCODES["OUT"]):
                        m.d.sync += self.out_port.eq(self.acc)
                    with m.Case(OPCODES["JMP"]):
                        m.d.sync += self.pc.eq(self.operand)
                    with m.Case(OPCODES["JZ"]):
                        with m.If(self.zero):
                            m.d.sync += self.pc.eq(self.operand)
                    with m.Case(OPCODES["JNZ"]):
                        with m.If(~self.zero):
                            m.d.sync += self.pc.eq(self.operand)
                    with m.Case(OPCODES["HLT"]):
                        m.d.sync += [self.halted.eq(1), self.pc.eq(self.pc)]
                with m.If(op == OPCODES["HLT"]):
                    m.next = "HALT"
                with m.Else():
                    m.next = "F1"
            with m.State("HALT"):
                m.next = "HALT"

        # expose ram for the simulator to read out
        self._ram = ram
        return m
