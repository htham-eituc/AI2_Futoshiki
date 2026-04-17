from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class Literal:
    atom: Any
    negated: bool = False

    def __repr__(self):
        return f"{'¬' if self.negated else ''}{self.atom}"

    def complement(self):
        return Literal(self.atom, not self.negated)

                          
def pos(atom) -> Literal:
    return Literal(atom, negated=False)

def neg(atom) -> Literal:
    return Literal(atom, negated=True)

                                          
def clause(*lits) -> frozenset:
    return frozenset(lits)