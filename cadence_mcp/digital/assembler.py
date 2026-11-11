"""Tiny two-pass assembler for the 8-bit CPU.

Every instruction assembles to exactly 2 bytes ([opcode][operand]) so PC stays
aligned (operand byte is 0 for operand-less ops). Supports labels, `.org`,
`.byte`, decimal/hex/'label' operands, and `;`/`#` comments.

Example:
    ; sum 1..5 into OUT
        LDI 0
        STA sum
    loop:
        LDA sum
        ADD i
        STA sum
        ...
    sum: .byte 0
    i:   .byte 1
"""
from __future__ import annotations

from .cpu import HAS_OPERAND, OPCODES


class AsmError(ValueError):
    pass


def _val(tok: str) -> int:
    tok = tok.strip()
    if tok.lower().startswith("0x"):
        return int(tok, 16)
    return int(tok)


def assemble(source: str, mem_size: int = 256) -> tuple[list[int], dict]:
    lines = source.splitlines()

    # normalize -> list of (label|None, mnemonic|directive, args)
    toks = []
    for raw in lines:
        line = raw.split(";")[0].split("#")[0].strip()
        if not line:
            continue
        label = None
        if ":" in line:
            label, _, rest = line.partition(":")
            label = label.strip()
            line = rest.strip()
        parts = line.split(None, 1) if line else []
        mnem = parts[0].upper() if parts else None
        arg = parts[1].strip() if len(parts) > 1 else ""
        toks.append((label, mnem, arg))

    # ---- pass 1: assign addresses to labels ----
    labels: dict[str, int] = {}
    addr = 0
    layout = []  # (addr, kind, mnem, arg)
    for label, mnem, arg in toks:
        cur = addr
        if mnem == ".ORG":
            cur = addr = _val(arg)
            if label:
                labels[label] = addr
            continue
        if label:
            labels[label] = addr
        if mnem is None:
            continue
        if mnem == ".BYTE":
            n = len([a for a in arg.split(",") if a.strip() != ""])
            layout.append((addr, "data", mnem, arg))
            addr += max(1, n)
        elif mnem in OPCODES:
            layout.append((addr, "inst", mnem, arg))
            addr += 2
        else:
            raise AsmError(f"unknown mnemonic '{mnem}'")

    # ---- pass 2: emit bytes ----
    image = [0] * mem_size

    def resolve(a: str) -> int:
        a = a.strip()
        if a == "":
            return 0
        if a in labels:
            return labels[a]
        return _val(a)

    for a, kind, mnem, arg in layout:
        if kind == "inst":
            image[a] = OPCODES[mnem]
            operand = resolve(arg) if mnem in HAS_OPERAND else 0
            image[a + 1] = operand & 0xFF
        else:  # data
            for i, part in enumerate([p for p in arg.split(",") if p.strip() != ""]):
                image[a + i] = resolve(part) & 0xFF

    return image, {"labels": labels, "size": len(layout)}
