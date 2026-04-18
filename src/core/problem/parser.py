"""
Parser for Futoshiki puzzles using the Adapter Pattern.
This allows the solvers (A*, FOL, Backtracking) to use a unified data structure
from text file inputs.
"""

from typing import List, Any
from abc import ABC, abstractmethod
from core.utils.KB_generate.kb_generate import ground_kb
from core.utils.KB_generate.knowledge_base import KnowledgeBase

class FutoshikiData:
    """
    Standard format for the Futoshiki Problem that all algorithms consume.
    This acts as the standardized state/transfer object from the Adapter to the solvers.
    """
    def __init__(self, size: int, grid: List[List[int]], 
                 h_constraints: List[List[int]], v_constraints: List[List[int]]):
        self.size = size
                                                           
        self.grid = grid
        
                                                                                                            
        self.h_constraints = h_constraints
        
                                                                                                            
        self.v_constraints = v_constraints

    def __str__(self):
        return f"FutoshikiData(size={self.size})"


class BaseParser(ABC):
    """
    Target interface for our Parsers. Any new format must implement this.
    """
    @abstractmethod
    def parse(self, source: Any) -> FutoshikiData:
        pass


class TextParserAdapter(BaseParser):
    """
    Adapter for the default .txt puzzle format generated in `test_generate`.
    Expected format: 
        Line 1: N (Grid Size)
        Lines 2 to N+1: N x N grid initial state (0 = empty, comma separated)
        Lines N+2 to 2N+1: N x N-1 horizontal constraints (1 = <, -1 = >, 0 = none)
        Lines 2N+2 to 3N: N-1 x N vertical constraints (1 = <, -1 = >, 0 = none)
    """
    def parse(self, source_filepath: str) -> FutoshikiData:
        try:
            with open(source_filepath, 'r') as f:
                lines = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            raise FileNotFoundError(f"Puzzle file not found: {source_filepath}")

        idx = 0
        n = int(lines[idx])
        idx += 1

                    
        grid = []
        for _ in range(n):
            row = [int(v.strip()) for v in lines[idx].split(",")]
            grid.append(row)
            idx += 1

                                      
        h_constraints = []
        for _ in range(n):
            row = [int(v.strip()) for v in lines[idx].split(",")]
            h_constraints.append(row)
            idx += 1

                                    
        v_constraints = []
        for _ in range(n - 1):
            row = [int(v.strip()) for v in lines[idx].split(",")]
            v_constraints.append(row)
            idx += 1

        return FutoshikiData(size=n, grid=grid, h_constraints=h_constraints, v_constraints=v_constraints)


class ParserFactory:
    """
    Factory to instantiate the correct Adapter and retrieve the standardized data model.
    """
    @classmethod
    def get_standard_data(cls, source: str) -> FutoshikiData:
        adapter = TextParserAdapter()
        return adapter.parse(source)


class AlgorithmAdapter:
    def __init__(self, data: FutoshikiData):
        self.data = data

    def to_astar(self) -> dict:                                                                           
        return {
            "initial_grid": self.data.grid,
            "h_constraints": self.data.h_constraints,
            "v_constraints": self.data.v_constraints,
            "grid_size": self.data.size
        }

    def to_fol(self) -> List[str]:
        puzzle  = futoshiki_to_puzzle_dict(self.data)
        clauses = ground_kb(self.data.size, puzzle)
        kb      = KnowledgeBase(clauses, self.data.size)
        kb.simplify()                                                  
        return kb

    def to_backtrack(self) -> dict:                                     
        domains = {}
        for r in range(self.data.size):
            for c in range(self.data.size):
                if self.data.grid[r][c] == 0:
                    domains[(r, c)] = set(range(1, self.data.size + 1))
                else:
                    domains[(r, c)] = {self.data.grid[r][c]}
        
        return {
            "variables_domain": domains,
            "h_constraints": self.data.h_constraints,
            "v_constraints": self.data.v_constraints,
            "grid_size": self.data.size
        }

    @classmethod
    def convert_text_to_astar(cls, source_filepath: str) -> dict:
        """Convenience function acting directly like `TextParserToAstar`."""
        standard_data = ParserFactory.get_standard_data(source_filepath)
        return cls(standard_data).to_astar()

    @classmethod
    def convert_text_to_fol(cls, source_filepath: str) -> List[str]:
        """Convenience function acting directly like `TextParserToFOL`."""
        standard_data = ParserFactory.get_standard_data(source_filepath)
        return cls(standard_data).to_fol()

    @classmethod
    def convert_text_to_backtrack(cls, source_filepath: str) -> dict:
        """Convenience function acting directly like `TextParserToBacktrack`."""
        standard_data = ParserFactory.get_standard_data(source_filepath)
        return cls(standard_data).to_backtrack()

def futoshiki_to_puzzle_dict(data: FutoshikiData) -> dict:
        """
        Converts FutoshikiData (0-indexed) into the puzzle dict
        that ground_kb() expects (1-indexed).
        """
        N = data.size
        given     = {}
        less_h    = set()
        greater_h = set()
        less_v    = set()
        greater_v = set()
                                                         
        for r in range(N):
            for c in range(N):
                v = data.grid[r][c]
                if v != 0:
                    given[(r + 1, c + 1)] = v

        for r in range(N):
            for c in range(N - 1):
                val = data.h_constraints[r][c]
                i, j = r + 1, c + 1
                if val ==  1: less_h.add((i, j))
                if val == -1: greater_h.add((i, j))

        for r in range(N - 1):
            for c in range(N):
                val = data.v_constraints[r][c]
                i, j = r + 1, c + 1
                if val ==  1: less_v.add((i, j))
                if val == -1: greater_v.add((i, j))

        return {
            'given':     given,
            'less_h':    less_h,
            'greater_h': greater_h,
            'less_v':    less_v,
            'greater_v': greater_v,
        }
