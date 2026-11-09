from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import pickle
from typing import Iterable

import numpy as np


@dataclass
class CCMCKPInstance:
    name: str
    path: Path
    groups: list[list[int]]
    costs: np.ndarray
    samples: list[np.ndarray]
    nominal: np.ndarray

    @property
    def m(self) -> int:
        return len(self.groups)

    @property
    def n(self) -> int:
        return int(self.costs.size)

    def validate_selection(self, selected: Iterable[int]) -> tuple[int, ...]:
        ids = tuple(int(v) for v in selected)
        if len(ids) != self.m or len(set(ids)) != self.m:
            raise ValueError(f"Expected exactly {self.m} distinct selected items")
        chosen = set(ids)
        canonical: list[int] = []
        for g, group in enumerate(self.groups):
            hits = [int(j) for j in group if int(j) in chosen]
            if len(hits) != 1:
                raise ValueError(f"Selection must contain exactly one item from group {g}")
            canonical.append(hits[0])
        return tuple(canonical)

    def selection_cost(self, selected: Iterable[int]) -> float:
        ids = self.validate_selection(selected)
        return float(np.sum(self.costs[list(ids)]))


def _load_pickle(path: Path):
    with path.open("rb") as f:
        return pickle.load(f)


def load_instance(instance_dir: str | Path) -> CCMCKPInstance:
    p = Path(instance_dir).expanduser().resolve()
    if not p.is_dir():
        raise FileNotFoundError(p)
    cost_path = p / "cost.txt"
    map_path = p / "node_to_factor.pkl"
    if not cost_path.is_file() or not map_path.is_file():
        raise FileNotFoundError(f"Not a CCMCKP benchmark instance: {p}")

    costs = np.asarray(np.loadtxt(cost_path), dtype=float).reshape(-1)
    if costs.size == 0 or not np.all(np.isfinite(costs)):
        raise ValueError("Invalid cost.txt")
    n = int(costs.size)

    raw_groups = _load_pickle(map_path)
    if isinstance(raw_groups, dict):
        keys = sorted(raw_groups, key=lambda x: int(x))
        groups = [[int(v) for v in raw_groups[k]] for k in keys]
    else:
        groups = [[int(v) for v in row] for row in raw_groups]
    if not groups or any(not g for g in groups):
        raise ValueError("Every group must be nonempty")
    flat = [j for group in groups for j in group]
    if len(flat) != len(set(flat)) or set(flat) != set(range(n)):
        raise ValueError("node_to_factor.pkl must partition factor IDs 0..n-1 exactly")

    samples: list[np.ndarray] = []
    nominal = np.empty(n, dtype=float)
    for j in range(n):
        sp = p / f"{j}_sample.txt"
        if not sp.is_file():
            raise FileNotFoundError(sp)
        arr = np.asarray(np.loadtxt(sp), dtype=float).reshape(-1)
        if arr.size == 0 or not np.all(np.isfinite(arr)):
            raise ValueError(f"Invalid sample file: {sp}")
        samples.append(arr)
        nominal[j] = float(np.mean(arr))

    return CCMCKPInstance(
        name=p.name,
        path=p,
        groups=groups,
        costs=costs,
        samples=samples,
        nominal=nominal,
    )


def resolve_instance_dir(instance: str | Path, benchmark_root: str | Path | None = None) -> Path:
    raw = Path(instance).expanduser()
    candidates: list[Path] = []
    if raw.is_dir():
        return raw.resolve()
    if benchmark_root is not None:
        root = Path(benchmark_root).expanduser()
        candidates.extend([root / raw, root / "benchmark" / raw])
    cwd = Path.cwd()
    candidates.extend([
        cwd / raw,
        cwd / "benchmark" / raw,
        cwd / "benchmark" / "benchmark" / raw,
    ])
    for p in candidates:
        if p.is_dir():
            return p.resolve()
    rendered = "\n  ".join(str(p) for p in candidates)
    raise FileNotFoundError(f"Could not resolve instance {instance!r}. Tried:\n  {rendered}")
