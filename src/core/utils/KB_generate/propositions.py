from dataclasses import dataclass

@dataclass(frozen=True)
class Val:
    i: int   # row    (1..N)
    j: int   # col    (1..N)
    v: int   # value  (1..N)

@dataclass(frozen=True)
class LessH:
    i: int
    j: int   # cell(i,j) < cell(i,j+1)

@dataclass(frozen=True)
class GreaterH:
    i: int
    j: int

@dataclass(frozen=True)
class LessV:
    i: int
    j: int   # cell(i,j) < cell(i+1,j)

@dataclass(frozen=True)
class GreaterV:
    i: int
    j: int

@dataclass(frozen=True)
class Given:
    i: int
    j: int
    v: int