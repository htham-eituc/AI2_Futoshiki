"""
Parser for Futoshiki puzzles using the Adapter Pattern.
This allows the solvers (A*, FOL, Backtracking) to use a unified data structure
regardless of the original input format (e.g., text files, JSON, GUI strings).
"""

from typing import List, Any
from abc import ABC, abstractmethod


class FutoshikiData:
    """
    Standard format for the Futoshiki Problem that all algorithms consume.
    This acts as the standardized state/transfer object from the Adapter to the solvers.
    """
    def __init__(self, size: int, grid: List[List[int]], 
                 h_constraints: List[List[int]], v_constraints: List[List[int]]):
        self.size = size
        # Expected grid: size x size matrix where 0 = empty
        self.grid = grid
        
        # h_constraints: size x (size-1). 1 means left < right, -1 means left > right, 0 means no constraint
        self.h_constraints = h_constraints
        
        # v_constraints: (size-1) x size. 1 means top < bottom, -1 means top > bottom, 0 means no constraint
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

        # Parse Grid
        grid = []
        for _ in range(n):
            row = [int(v.strip()) for v in lines[idx].split(",")]
            grid.append(row)
            idx += 1

        # Parse Horizontal constraints
        h_constraints = []
        for _ in range(n):
            row = [int(v.strip()) for v in lines[idx].split(",")]
            h_constraints.append(row)
            idx += 1

        # Parse Vertical constraints
        v_constraints = []
        for _ in range(n - 1):
            row = [int(v.strip()) for v in lines[idx].split(",")]
            v_constraints.append(row)
            idx += 1

        return FutoshikiData(size=n, grid=grid, h_constraints=h_constraints, v_constraints=v_constraints)


class JSONParserAdapter(BaseParser):
    """
    Example of another format adapter. 
    Could be used later if inputs come from a Web/GUI API.
    """
    def parse(self, json_data: dict) -> FutoshikiData:
        # Just an example matching standard target format
        n = json_data.get('size', 0)
        grid = json_data.get('grid', [])
        h_const = json_data.get('h_constraints', [])
        v_const = json_data.get('v_constraints', [])
        return FutoshikiData(size=n, grid=grid, h_constraints=h_const, v_constraints=v_const)


class ParserFactory:
    """
    Factory to instantiate the correct Adapter and retrieve the standardized data model.
    """
    @classmethod
    def get_standard_data(cls, source: Any, source_type: str = "text") -> FutoshikiData:
        """
        Instantiates appropriate adapter and returns the `FutoshikiData` model
        ready to be passed to A*, Backtracking, or FOL solvers.
        """
        if source_type == "text":
            adapter = TextParserAdapter()
        elif source_type == "json":
            adapter = JSONParserAdapter()
        else:
            raise ValueError(f"Unknown parser source type: {source_type}")
            
        return adapter.parse(source)


class AlgorithmAdapter:
    """
    Adapter bridging `FutoshikiData` into algorithm-specific domains.
    Each algorithm might require a very different initial setup or structure.
    """
    def __init__(self, data: FutoshikiData):
        self.data = data

    def to_astar(self) -> dict:
        """
        Formats the puzzle data specifically for the A* search algorithm.
        Returns the Initial State node structure or dictionary required by A*.
        """
        # TODO: Adjust this to return exactly what your A* algorithm's init function expects.
        # Commonly, A* just needs an initial State node object and a Problem configuration object.
        return {
            "initial_grid": self.data.grid,
            "h_constraints": self.data.h_constraints,
            "v_constraints": self.data.v_constraints,
            "grid_size": self.data.size
        }

    def to_fol(self) -> List[str]:
        """
        Formats the puzzle data into First Order Logic (FOL) CNF clauses.
        Returns a Knowledge Base (KB) structure (e.g., list of strings or logic objects).
        """
        # TODO: Convert numeric grid/constraints into FOL statements (e.g., "LessThan(X1, Y1)")
        clauses = []
        # Example pseudo-conversion placeholder
        clauses.append(f"GridSize({self.data.size})")
        # Add your precise FOL transformation logic here
        return clauses

    def to_backtrack(self) -> dict:
        """
        Formats the puzzle data specifically for Backtracking (CSP).
        Returns domain configurations, variables, and constraints for constraint satisfaction.
        """
        # TODO: Setup CSP variables domains (1 to N)
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
        standard_data = ParserFactory.get_standard_data(source_filepath, source_type="text")
        return cls(standard_data).to_astar()

    @classmethod
    def convert_text_to_fol(cls, source_filepath: str) -> List[str]:
        """Convenience function acting directly like `TextParserToFOL`."""
        standard_data = ParserFactory.get_standard_data(source_filepath, source_type="text")
        return cls(standard_data).to_fol()

    @classmethod
    def convert_text_to_backtrack(cls, source_filepath: str) -> dict:
        """Convenience function acting directly like `TextParserToBacktrack`."""
        standard_data = ParserFactory.get_standard_data(source_filepath, source_type="text")
        return cls(standard_data).to_backtrack()
