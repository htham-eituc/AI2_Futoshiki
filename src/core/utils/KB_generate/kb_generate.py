from core.utils.KB_generate.propositions import *
from core.utils.KB_generate.clause import pos, neg, clause

def compute_less(N: int) -> set:
    domain = range(0, N + 2)
    return {(a, b) for a in domain for b in domain if a < b}

def ground_kb(N: int, puzzle: dict) -> list:
    cells  = range(1, N + 1)
    vals   = range(1, N + 1)
    less   = compute_less(N)
    KB     = []                                              

    given     = puzzle['given']
    less_h    = puzzle['less_h']
    greater_h = puzzle['greater_h']
    less_v    = puzzle['less_v']
    greater_v = puzzle['greater_v']

    # A1: each cell has >= 1 value
    for i in cells:
        for j in cells:
            KB.append(clause(*[pos(Val(i, j, v)) for v in vals]))

    # A2: each cell has <= 1 value           
    for i in cells:
        for j in cells:
            for v1 in vals:
                for v2 in vals:
                    if v1 < v2:
                        KB.append(clause(neg(Val(i,j,v1)), neg(Val(i,j,v2))))

    # A3: row uniqueness                                      
    for i in cells:
        for v in vals:
            for j1 in cells:
                for j2 in cells:
                    if j1 < j2:
                        KB.append(clause(neg(Val(i,j1,v)), neg(Val(i,j2,v))))                                              

    # A4: horizontal less-than                                            
    for i in cells:
        for j in range(1, N):                             
            if (i, j) in less_h:
                for v1 in vals:
                    for v2 in vals:
                        if (v1, v2) not in less:                        
                            KB.append(clause(neg(Val(i,j,v1)), neg(Val(i,j+1,v2))))
  
    # A5: given clues
    for (i, j), v in given.items():
        KB.append(clause(pos(Val(i, j, v))))

    # A6: column uniqueness                             
    for j in cells:
        for v in vals:
            for i1 in cells:
                for i2 in cells:
                    if i1 < i2:
                        KB.append(clause(neg(Val(i1,j,v)), neg(Val(i2,j,v))))
                    

    # A8: horizontal greater-than                                        
    for i in cells:
        for j in range(1, N):
            if (i, j) in greater_h:
                for v1 in vals:
                    for v2 in vals:
                        if (v2, v1) not in less:                         
                            KB.append(clause(neg(Val(i,j,v1)), neg(Val(i,j+1,v2))))

    # A9: vertical less-than                                                                      
    for i in range(1, N):                                
        for j in cells:
            if (i, j) in less_v:
                for v1 in vals:
                    for v2 in vals:
                        if (v1, v2) not in less:
                            KB.append(clause(neg(Val(i,j,v1)), neg(Val(i+1,j,v2))))

    # A10: vertical greater-than                                                             
    for i in range(1, N):
        for j in cells:
            if (i, j) in greater_v:
                for v1 in vals:
                    for v2 in vals:
                        if (v2, v1) not in less:
                            KB.append(clause(neg(Val(i,j,v1)), neg(Val(i+1,j,v2))))

    # A11: row completeness                                                                
    for i in cells:
        for v in vals:
            KB.append(clause(*[pos(Val(i, j, v)) for j in cells]))

    # A12: column completeness
    for j in cells:
        for v in vals:
            KB.append(clause(*[pos(Val(i, j, v)) for i in cells]))

    return KB