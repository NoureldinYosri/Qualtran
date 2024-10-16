#  Copyright 2023 Google LLC
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""Functionality for the `Bloq.call_graph()` protocol."""

import collections.abc
from collections import defaultdict
from typing import (
    Callable,
    cast,
    Dict,
    Iterable,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

import networkx as nx
import sympy

from qualtran import Bloq, CompositeBloq, DecomposeNotImplementedError, DecomposeTypeError

BloqCountT = Tuple[Bloq, Union[int, sympy.Expr]]
BloqCountDictT = Mapping[Bloq, Union[int, sympy.Expr]]
MutableBloqCountDictT = MutableMapping[Bloq, Union[int, sympy.Expr]]
from ._generalization import _make_composite_generalizer, GeneralizerT


def big_O(expr) -> sympy.Order:
    """Helper to deal with CS-style big-O notation that takes the infinite limit by default."""
    if isinstance(expr, (int, float)):
        return sympy.Order(expr)
    return sympy.Order(expr, *[(var, sympy.oo) for var in expr.free_symbols])


class SympySymbolAllocator:
    """A class that allocates unique sympy symbols for integrating out bloq attributes.

    When counting, we group bloqs that only differ in attributes that do not affect
    resource costs. In practice, we do this by replacing bloqs with a version where
    the offending attributes have been set to an arbitrary (but unique) symbol allocated
    by this class. We refer to this process as "generalizing".
    """

    def __init__(self):
        self._idxs: Dict[str, int] = defaultdict(lambda: 0)

    def new_symbol(self, prefix: str) -> sympy.Symbol:
        """Return a unique symbol beginning with _prefix."""
        s = sympy.Symbol(f'_{prefix}{self._idxs[prefix]}')
        self._idxs[prefix] += 1
        return s


def build_cbloq_call_graph(cbloq: CompositeBloq) -> BloqCountDictT:
    """Count all the subbloqs in a composite bloq.

    This is the function underpinning `CompositeBloq.build_call_graph`.

    Args:
        cbloq: The composite bloq.
    """
    counts: Dict[Bloq, int] = defaultdict(lambda: 0)
    for binst in cbloq.bloq_instances:
        counts[binst.bloq] += 1

    return counts


def _generalize_callees(
    raw_callee_counts: Union[BloqCountDictT, Set[BloqCountT]], generalizer: GeneralizerT
) -> List[BloqCountT]:
    """Apply `generalizer` to the results of `bloq.build_call_graph`.

    This calls `generalizer` on each of the callees returned from that function,
    and filters out cases where `generalizer` returns `None`.
    """
    callee_counts: Dict[Bloq, Union[int, sympy.Expr]] = defaultdict(lambda: 0)
    if isinstance(raw_callee_counts, set):
        raw_callee_iterator: Iterable[BloqCountT] = raw_callee_counts
    else:
        raw_callee_iterator = raw_callee_counts.items()
    for callee, n in raw_callee_iterator:
        generalized_callee = generalizer(callee)
        if generalized_callee is None:
            # Signifies that this callee should be ignored.
            continue
        callee_counts[generalized_callee] += n
    return list(callee_counts.items())


def get_bloq_callee_counts(
    bloq: 'Bloq',
    generalizer: Optional[Union['GeneralizerT', Sequence['GeneralizerT']]] = None,
    ssa: Optional[SympySymbolAllocator] = None,
    ignore_decomp_failure: bool = True,
) -> List[BloqCountT]:
    """Get the direct callees of a bloq and the number of times they are called.

    This calls `bloq.build_call_graph()` with the correct configuration options.

    Args:
        bloq: The bloq.
        generalizer: If provided, run this function on each callee to consolidate attributes
            that do not affect resource estimates. If the callable
            returns `None`, the bloq is omitted from the counts graph. If a sequence of
            generalizers is provided, each generalizer will be run in order.
        ssa: A sympy symbol allocator that can be provided if one already exists in your
            computation.
        ignore_decomp_failure: If set to True, failing to find callees will be returned as an
            empty list. Otherwise, raise the `DecomposeNotImplementedError` or `DecomposeTypeError`
            causing the failure.

    Returns:
        A list of (bloq, n) bloq counts.
    """
    if generalizer is None:
        generalizer = lambda b: b
    if isinstance(generalizer, (list, tuple)):
        generalizer = _make_composite_generalizer(*generalizer)
    if ssa is None:
        ssa = SympySymbolAllocator()

    try:
        return _generalize_callees(bloq.build_call_graph(ssa), cast(GeneralizerT, generalizer))
    except (DecomposeNotImplementedError, DecomposeTypeError) as e:
        if ignore_decomp_failure:
            return []
        else:
            raise e


def _build_call_graph(
    bloq: Bloq,
    generalizer: GeneralizerT,
    ssa: SympySymbolAllocator,
    keep: Callable[[Bloq], bool],
    max_depth: Optional[int],
    g: nx.DiGraph,
    depth: int,
) -> None:
    """Recursively build the call graph.

    Arguments are the same as `get_bloq_call_graph`, except `g` is the graph we're building
    (i.e. it is mutated by this function) and `depth` is the current recursion depth.
    """
    if bloq in g:
        # We already visited this node.
        return

    # Make sure this node is present in the graph.
    g.add_node(bloq)

    # Base case 1: This node is requested by the user to be a leaf node via the `keep` parameter.
    if keep(bloq):
        return

    # Base case 2: Max depth exceeded
    if max_depth is not None and depth >= max_depth:
        return

    # Prep for recursion: get the callees and modify them according to `generalizer`.
    callee_counts = get_bloq_callee_counts(bloq, generalizer)

    # Base case 3: Empty list of callees
    if not callee_counts:
        return

    for callee, n in callee_counts:
        # Quite important: we do the recursive call first before adding in the edges.
        # Otherwise, adding the edge would mark the callee node as already-visited by
        # virtue of it being added to the graph with the `g.add_edge` call.

        # Do the recursive step, which will continue to mutate `g`
        _build_call_graph(callee, generalizer, ssa, keep, max_depth, g, depth + 1)

        # Update edge in `g`
        if (bloq, callee) in g.edges:
            g.edges[bloq, callee]['n'] += n
        else:
            g.add_edge(bloq, callee, n=n)


def _compute_sigma(root_bloq: Bloq, g: nx.DiGraph) -> Dict[Bloq, Union[int, sympy.Expr]]:
    """Iterate over nodes to sum up the counts of leaf bloqs."""
    bloq_sigmas: Dict[Bloq, Dict[Bloq, Union[int, sympy.Expr]]] = defaultdict(
        lambda: defaultdict(lambda: 0)
    )
    for bloq in reversed(list(nx.topological_sort(g))):
        callees = list(g.successors(bloq))
        sigma = bloq_sigmas[bloq]
        if not callees:
            # 1. `bloq` is a leaf node. Its count is one of itself.
            sigma[bloq] = 1
            continue

        for callee in callees:
            callee_sigma = bloq_sigmas[callee]
            # 2. Otherwise, sigma of the caller is sum(n * sigma of callee) for all the callees.
            n = g.edges[bloq, callee]['n']
            for k in callee_sigma.keys():
                sigma[k] += callee_sigma[k] * n

    return dict(bloq_sigmas[root_bloq])


def get_bloq_call_graph(
    bloq: Bloq,
    generalizer: Optional[Union['GeneralizerT', Sequence['GeneralizerT']]] = None,
    ssa: Optional[SympySymbolAllocator] = None,
    keep: Optional[Callable[[Bloq], bool]] = None,
    max_depth: Optional[int] = None,
) -> Tuple[nx.DiGraph, Dict[Bloq, Union[int, sympy.Expr]]]:
    """Recursively build the bloq call graph and call totals.

    See `Bloq.call_graph()` as a convenient way of calling this function.

    Args:
        bloq: The bloq to count sub-bloqs.
        generalizer: If provided, run this function on each (sub)bloq to replace attributes
            that do not affect resource estimates with generic sympy symbols. If the function
            returns `None`, the bloq is omitted from the counts graph. If a sequence of
            generalizers is provided, each generalizer will be run in order.
        ssa: a `SympySymbolAllocator` that will be passed to the `Bloq.build_call_graph` method. If
            your `generalizer` function closes over a `SympySymbolAllocator`, provide it here as
            well. Otherwise, we will create a new allocator.
        keep: If this function evaluates to True for the current bloq, keep the bloq as a leaf
            node in the call graph instead of recursing into it.
        max_depth: If provided, build a call graph with at most this many layers.

    Returns:
        g: A directed graph where nodes are (generalized) bloqs and edge attribute 'n' reports
            the number of times successor bloq is called via its predecessor.
        sigma: Call totals for "leaf" bloqs. We keep a bloq as a leaf in the call graph
            according to `keep` and `max_depth` (if provided) or if a bloq cannot be
            decomposed.
    """
    if ssa is None:
        ssa = SympySymbolAllocator()
    if keep is None:
        keep = lambda b: False
    if generalizer is None:
        generalizer = lambda b: b
    if isinstance(generalizer, collections.abc.Sequence):
        generalizer = _make_composite_generalizer(*generalizer)

    g = nx.DiGraph()
    bloq = generalizer(bloq)
    if bloq is None:
        raise ValueError("You can't generalize away the root bloq.")
    _build_call_graph(bloq, generalizer, ssa, keep, max_depth, g=g, depth=0)
    sigma = _compute_sigma(bloq, g)
    return g, sigma


def format_call_graph_debug_text(g: nx.DiGraph) -> str:
    """Print the graph returned from `get_bloq_counts_graph`."""
    lines = []
    for gen in nx.topological_generations(g):
        for b in sorted(gen, key=str):
            for succ in sorted(g.succ[b], key=str):
                lines.append(f"{b} -- {g.edges[b, succ]['n']} -> {succ}")
    return '\n'.join(lines)
