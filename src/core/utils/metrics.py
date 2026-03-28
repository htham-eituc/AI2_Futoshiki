from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional
import csv
import json


def _utc_now_iso() -> str:
	return datetime.now(timezone.utc).isoformat()


@dataclass
class SolverMetrics:
	"""Metrics captured for one solver run."""

	algorithm: str
	puzzle_id: Optional[str] = None

	started_at: Optional[str] = None
	finished_at: Optional[str] = None
	elapsed_seconds: float = 0.0

	solved: bool = False
	timed_out: bool = False
	error: Optional[str] = None

	nodes_generated: int = 0
	nodes_expanded: int = 0
	max_frontier_size: int = 0
	solution_depth: int = 0

	assignments: int = 0
	backtracks: int = 0
	constraint_checks: int = 0

	extra: Dict[str, Any] = field(default_factory=dict)

	def start(self) -> None:
		self.started_at = _utc_now_iso()

	def stop(self) -> None:
		self.finished_at = _utc_now_iso()
		if self.started_at:
			start_dt = datetime.fromisoformat(self.started_at)
			end_dt = datetime.fromisoformat(self.finished_at)
			self.elapsed_seconds = (end_dt - start_dt).total_seconds()

	def mark_solved(self, value: bool = True) -> None:
		self.solved = value

	def mark_timeout(self, value: bool = True) -> None:
		self.timed_out = value

	def mark_error(self, message: str) -> None:
		self.error = message

	def inc_nodes_generated(self, amount: int = 1) -> None:
		self.nodes_generated += amount

	def inc_nodes_expanded(self, amount: int = 1) -> None:
		self.nodes_expanded += amount

	def set_frontier_size(self, frontier_size: int) -> None:
		if frontier_size > self.max_frontier_size:
			self.max_frontier_size = frontier_size

	def inc_assignments(self, amount: int = 1) -> None:
		self.assignments += amount

	def inc_backtracks(self, amount: int = 1) -> None:
		self.backtracks += amount

	def inc_constraint_checks(self, amount: int = 1) -> None:
		self.constraint_checks += amount

	def set_solution_depth(self, depth: int) -> None:
		self.solution_depth = depth

	def add_extra(self, key: str, value: Any) -> None:
		self.extra[key] = value

	def to_dict(self) -> Dict[str, Any]:
		return asdict(self)


class MetricsStore:
	"""Thread-safe store to collect and persist multiple solver metrics."""

	def __init__(self) -> None:
		self._items: List[SolverMetrics] = []
		self._lock = Lock()

	def add(self, metrics: SolverMetrics) -> None:
		with self._lock:
			self._items.append(metrics)

	def all(self) -> List[SolverMetrics]:
		with self._lock:
			return list(self._items)

	def clear(self) -> None:
		with self._lock:
			self._items.clear()

	def as_dict_list(self) -> List[Dict[str, Any]]:
		return [m.to_dict() for m in self.all()]

	def save_json(self, output_path: str | Path, *, indent: int = 2) -> Path:
		target = Path(output_path)
		target.parent.mkdir(parents=True, exist_ok=True)
		with target.open("w", encoding="utf-8") as f:
			json.dump(self.as_dict_list(), f, ensure_ascii=False, indent=indent)
		return target

	def save_jsonl(self, output_path: str | Path) -> Path:
		target = Path(output_path)
		target.parent.mkdir(parents=True, exist_ok=True)
		with target.open("w", encoding="utf-8") as f:
			for row in self.as_dict_list():
				f.write(json.dumps(row, ensure_ascii=False) + "\n")
		return target

	def save_csv(self, output_path: str | Path) -> Path:
		rows = self.as_dict_list()
		target = Path(output_path)
		target.parent.mkdir(parents=True, exist_ok=True)

		if not rows:
			target.write_text("", encoding="utf-8")
			return target

		scalar_rows: List[Dict[str, Any]] = []
		for row in rows:
			flattened = dict(row)
			flattened["extra"] = json.dumps(flattened.get("extra", {}), ensure_ascii=False)
			scalar_rows.append(flattened)

		fieldnames = list(scalar_rows[0].keys())
		with target.open("w", encoding="utf-8", newline="") as f:
			writer = csv.DictWriter(f, fieldnames=fieldnames)
			writer.writeheader()
			writer.writerows(scalar_rows)
		return target


GLOBAL_METRICS_STORE = MetricsStore()

