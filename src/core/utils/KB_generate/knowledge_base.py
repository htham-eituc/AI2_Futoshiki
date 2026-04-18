from core.utils.KB_generate.clause import Literal, pos, neg

class KnowledgeBase:
    def __init__(self, clauses: list, N: int):
        self.N        = N
        self.clauses  = list(clauses)                          
        self.facts    = set()                                      
        self.negated  = set()                                    

    def add_fact(self, lit: Literal):
        self.facts.add(lit)
                                                  
        self.negated.add(lit.atom if lit.negated else lit.atom)

    def is_true(self, lit: Literal) -> bool:
        return lit in self.facts

    def is_false(self, lit: Literal) -> bool:
        return lit.complement() in self.facts

    def unit_clauses(self):
        return [c for c in self.clauses if len(c) == 1]

    def simplify(self):
        changed = True
        while changed:
            changed = False
            units = self.unit_clauses()
            for unit in units:
                lit = next(iter(unit))
                self.add_fact(lit)
                new_clauses = []
                for c in self.clauses:
                    if lit in c:
                        changed = True                                   
                        continue
                    trimmed = c - {lit.complement()}
                    if trimmed != c:
                        changed = True
                    new_clauses.append(trimmed)
                self.clauses = new_clauses

    def has_empty_clause(self) -> bool:
        """An empty clause means contradiction (UNSAT)."""
        return any(len(c) == 0 for c in self.clauses)

    def is_solved(self) -> bool:
        """All clauses satisfied."""
        return len(self.clauses) == 0

    def __len__(self):
        return len(self.clauses)

    def __repr__(self):
        return f"KnowledgeBase(N={self.N}, clauses={len(self.clauses)})"