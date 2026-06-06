"""可插拔翻後評估後端。"""

from .base import PostflopBackend, PostflopNode
from .equity_backend import EquityBackend
from .solver_backend import SolverBackend, SolverBackendError

__all__ = [
    "EquityBackend",
    "PostflopBackend",
    "PostflopNode",
    "SolverBackend",
    "SolverBackendError",
]


def get_backend(name: str, **kwargs: object) -> PostflopBackend:
    """依名稱取得後端：'equity'（預設）| 'solver'。"""
    if name == "solver":
        return SolverBackend(**kwargs)  # type: ignore[arg-type]
    return EquityBackend(**kwargs)  # type: ignore[arg-type]
