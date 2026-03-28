# `parser.py` Adapter & Conversion Guide
**File Location**: `src/core/problem/parser.py`

## 1. How It Works
The parsing module uses the **Adapter Design Pattern** to ensure we can read any arbitrary puzzle format (Text, JSON, etc.) and seamlessly convert it for multiple AI algorithms (A*, FOL, Backtracking) without modifying the algorithmic logic itself.

It operates in **two steps**:
1. **Source Adapter (`BaseParser`)**: Reads raw files (e.g., text from `test_generate/*.txt`) and converts them into a completely uniform intermediate object called `FutoshikiData`.
2. **Algorithm Adapter (`AlgorithmAdapter`)**: Takes the intermediate `FutoshikiData` and translates it into the EXACT data types or setup structures your specific algorithm (A*, FOL, CSP Backtracking) needs.

---

## 2. How To Use

You can retrieve the formatted data for your specific algorithm directly in one line! We provided convenience factory-like methods:

**For A* Search:**
```python
from src.core.problem.parser import AlgorithmAdapter

filepath = "src/test_generate/futoshiki_4x4_easy.txt"
astar_input = AlgorithmAdapter.convert_text_to_astar(filepath)

# Now pass to your solver
astar_solver = AStarSolver(initial_data=astar_input)
```

**For First Order Logic (FOL):**
```python
from src.core.problem.parser import AlgorithmAdapter

fol_clauses = AlgorithmAdapter.convert_text_to_fol(filepath)
# returns a list of string clauses logic or KB structure.
```

**For Backtracking (CSP format):**
```python
from src.core.problem.parser import AlgorithmAdapter

backtrack_domains = AlgorithmAdapter.convert_text_to_backtrack(filepath)
# returns a dictionary of domain sets for your CSP variables (e.g. { (0, 0): {1,2,3,4} })
```

---

## 3. How To Update

As algorithms evolve, you will need to update exactly **what** gets returned to them.

**To Update An Existing Algorithm's Input:**
1. Open up `src/core/problem/parser.py`
2. Scroll to the `AlgorithmAdapter` class.
3. If the A* algorithm wants the constraint format changed, look for `def to_astar(self)`. Edit the dictionary and structure returned inside this function. Your A* source code won't need to parse strings ever again.

**To Add a Brand New Algorithm (e.g., Forward Chaining):**
1. Add a new translation method inside `AlgorithmAdapter`:
   ```python
   def to_forward_chaining(self) -> dict:
       # Transform self.data (type: FutoshikiData) into your FC setup!
       return fc_setup_data
   ```
2. Add a new convenience method below it:
   ```python
   @classmethod
   def convert_text_to_fc(cls, source_filepath: str):
       standard_data = ParserFactory.get_standard_data(source_filepath, source_type="text")
       return cls(standard_data).to_forward_chaining()
   ```

**To Add a Brand New Input Form (e.g., Web App JSON string):**
1. Create a class under `BaseParser` (e.g. `JSONParserAdapter`).
2. Make it output standard `FutoshikiData`.
3. Inform the `ParserFactory` about it. The `AlgorithmAdapter` structures will automatically know how to handle the new format without extra work!
