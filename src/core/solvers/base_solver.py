from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional, Type

from ..utils.metrics import SolverMetrics


class BaseSolver(ABC):
	"""Abstract base class for all Futoshiki solvers."""

	def __init__(self, problem: Any, *, name: Optional[str] = None) -> None:
		self.problem = problem
		self.name = name or self.__class__.__name__
		self.metrics = SolverMetrics(algorithm=self.name)

	@abstractmethod
	def solve(self) -> Any:
		"""Return the solving result (format decided by concrete solver)."""
		raise NotImplementedError


class SolverFactory:
	"""Factory/registry for creating solvers by name.

	Example:
		@SolverFactory.register("backtracking")
		class BacktrackingSolver(BaseSolver):
			...

		solver = SolverFactory.create("backtracking", problem)
	"""

	_registry: Dict[str, Type[BaseSolver]] = {}

	@classmethod
	def register(
	 cls, name: str
	) -> Callable[[Type[BaseSolver]], Type[BaseSolver]]:
		"""Decorator to register a solver class with a string key."""

		normalized_name = name.strip().lower()

		def decorator(solver_cls: Type[BaseSolver]) -> Type[BaseSolver]:
			if not issubclass(solver_cls, BaseSolver):
				raise TypeError(
				 f"Registered solver must inherit from BaseSolver, got {solver_cls.__name__}."
				)
			cls._registry[normalized_name] = solver_cls
			return solver_cls

		return decorator

	@classmethod
	def create(cls, name: str, problem: Any, **kwargs: Any) -> BaseSolver:
		"""Create solver instance by name."""

		normalized_name = name.strip().lower()
		solver_cls = cls._registry.get(normalized_name)
		if solver_cls is None:
			available = ", ".join(sorted(cls._registry.keys())) or "<empty>"
			raise ValueError(
			 f"Unknown solver '{name}'. Available solvers: {available}"
			)
		return solver_cls(problem, **kwargs)

	@classmethod
	def registered_solvers(cls) -> Dict[str, Type[BaseSolver]]:
		return dict(cls._registry)


__all__ = ["BaseSolver", "SolverFactory"]

