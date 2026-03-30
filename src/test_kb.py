# main.py
from core.problem.parser import AlgorithmAdapter, ParserFactory 
from core.problem.parser import futoshiki_to_puzzle_dict, verify_conversion

data    = ParserFactory.get_standard_data("test_generate/futoshiki_9x9_medium.txt", source_type="text")
adapter = AlgorithmAdapter(data)

# Cross-check the index conversion before building the KB
puzzle = futoshiki_to_puzzle_dict(data)
verify_conversion(data, puzzle)

# Build KB
kb = adapter.to_fol()