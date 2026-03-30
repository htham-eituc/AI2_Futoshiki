from core.utils.KB_generate.propositions import *
from core.utils.KB_generate.clause import pos, neg, clause

def compute_less(N: int) -> set:
    """All (v1,v2) pairs where v1 < v2, over domain 0..N+1."""
    domain = range(0, N + 2)
    return {(a, b) for a in domain for b in domain if a < b}

def ground_kb(N: int, puzzle: dict) -> list:
    cells  = range(1, N + 1)
    vals   = range(1, N + 1)
    less   = compute_less(N)
    KB     = []                  # list of frozenset[Literal]

    given     = puzzle['given']
    less_h    = puzzle['less_h']
    greater_h = puzzle['greater_h']
    less_v    = puzzle['less_v']
    greater_v = puzzle['greater_v']

    # ── A1: each cell has ≥1 value ────────────────────────────────────────
    # Grounded Skolem: instead of f(i,j), generate the full disjunction
    # {Val(i,j,1) ∨ Val(i,j,2) ∨ ... ∨ Val(i,j,N)}
    for i in cells:
        for j in cells:
            KB.append(clause(*[pos(Val(i, j, v)) for v in vals]))

    # ── A2: each cell has ≤1 value ────────────────────────────────────────
    # {¬Val(i,j,v1) ∨ ¬Val(i,j,v2)}  for every v1 < v2
    for i in cells:
        for j in cells:
            for v1 in vals:
                for v2 in vals:
                    if v1 < v2:
                        KB.append(clause(neg(Val(i,j,v1)), neg(Val(i,j,v2))))

    # ── A3: row uniqueness ────────────────────────────────────────────────
    # {¬Val(i,j1,v) ∨ ¬Val(i,j2,v)}  for every j1 < j2
    for i in cells:
        for v in vals:
            for j1 in cells:
                for j2 in cells:
                    if j1 < j2:
                        KB.append(clause(neg(Val(i,j1,v)), neg(Val(i,j2,v))))

    # ── A4: horizontal less-than ──────────────────────────────────────────
    # For each active LessH(i,j): if v1 >= v2, forbid both values together
    # (tautologies where v1<v2 is already true are skipped)
    for i in cells:
        for j in range(1, N):          # j+1 must stay ≤ N
            if (i, j) in less_h:
                for v1 in vals:
                    for v2 in vals:
                        if (v1, v2) not in less:   # constraint violated
                            KB.append(clause(neg(Val(i,j,v1)), neg(Val(i,j+1,v2))))

    # ── A5: given clues ───────────────────────────────────────────────────
    # Unit clause: {Val(i,j,v)}
    for (i, j), v in given.items():
        KB.append(clause(pos(Val(i, j, v))))

    # ── A6: column uniqueness ─────────────────────────────────────────────
    # {¬Val(i1,j,v) ∨ ¬Val(i2,j,v)}  for every i1 < i2
    for j in cells:
        for v in vals:
            for i1 in cells:
                for i2 in cells:
                    if i1 < i2:
                        KB.append(clause(neg(Val(i1,j,v)), neg(Val(i2,j,v))))

    # ── A7: value bounds ──────────────────────────────────────────────────
    # Implicit: we only iterate v in range(1,N+1), so out-of-range values
    # never appear. No explicit clause needed, but add guard if desired:
    #   clause(neg(Val(i,j,v))) for v outside [1,N]  → always unit-propagated away

    # ── A8: horizontal greater-than ───────────────────────────────────────
    # Symmetric to A4 but requires v2 < v1
    for i in cells:
        for j in range(1, N):
            if (i, j) in greater_h:
                for v1 in vals:
                    for v2 in vals:
                        if (v2, v1) not in less:   # v2 >= v1 → violation
                            KB.append(clause(neg(Val(i,j,v1)), neg(Val(i,j+1,v2))))

    # ── A9: vertical less-than ────────────────────────────────────────────
    for i in range(1, N):             # i+1 must stay ≤ N
        for j in cells:
            if (i, j) in less_v:
                for v1 in vals:
                    for v2 in vals:
                        if (v1, v2) not in less:
                            KB.append(clause(neg(Val(i,j,v1)), neg(Val(i+1,j,v2))))

    # ── A10: vertical greater-than ────────────────────────────────────────
    for i in range(1, N):
        for j in cells:
            if (i, j) in greater_v:
                for v1 in vals:
                    for v2 in vals:
                        if (v2, v1) not in less:
                            KB.append(clause(neg(Val(i,j,v1)), neg(Val(i+1,j,v2))))

    # ── A11: row completeness ─────────────────────────────────────────────
    # Grounded Skolem g(i,v): {Val(i,1,v) ∨ Val(i,2,v) ∨ ... ∨ Val(i,N,v)}
    for i in cells:
        for v in vals:
            KB.append(clause(*[pos(Val(i, j, v)) for j in cells]))

    # ── A12: column completeness ──────────────────────────────────────────
    # Grounded Skolem h(j,v): {Val(1,j,v) ∨ Val(2,j,v) ∨ ... ∨ Val(N,j,v)}
    for j in cells:
        for v in vals:
            KB.append(clause(*[pos(Val(i, j, v)) for i in cells]))

    return KB