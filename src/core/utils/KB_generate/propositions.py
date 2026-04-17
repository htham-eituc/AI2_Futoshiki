from dataclasses import dataclass

@dataclass(frozen=True)
class Val:
    i: int                  
    j: int                  
    v: int                  

@dataclass(frozen=True)
class LessH:
    i: int
    j: int                            

@dataclass(frozen=True)
class GreaterH:
    i: int
    j: int

@dataclass(frozen=True)
class LessV:
    i: int
    j: int                            

@dataclass(frozen=True)
class GreaterV:
    i: int
    j: int

@dataclass(frozen=True)
class Given:
    i: int
    j: int
    v: int