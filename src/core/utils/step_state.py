from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

@dataclass
class StepState:
    step_number: int
    grid: List[List[int]]
    message: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    active_cell: Optional[Tuple[int, int]] = None
    changed_cell: Optional[Tuple[int, int]] = None
    conflict_cells: List[Tuple[int, int]] = field(default_factory=list)
    is_complete: bool = False
    is_solved: bool = False