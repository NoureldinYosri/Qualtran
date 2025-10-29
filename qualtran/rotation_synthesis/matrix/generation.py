#  Copyright 2025 Google LLC
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

from typing import Iterator, Sequence

from tqdm import tqdm

from qualtran.rotation_synthesis.matrix import su2_ct


def generate_rotations_iter(
    max_num_ts: int, with_progress_bar: bool = True, verbose: bool = False
) -> Iterator[Sequence[su2_ct.SU2CliffordT]]:
    """Yield lists where the kth list contains Clifford+T unitaries that use k Ts.

    Args:
        max_num_ts: the maximum number of T gates to use.
        with_progress_bar: whether to display a progress bar or not.
        verbose: whether to print debug statements or not.
    Yields:
        max_num_ts+1 lists where the kth list contains Clifford+T unitaries that use k T gates.
    """
    cliffords = tuple(su2_ct.generate_cliffords())
    frontier: Sequence[su2_ct.SU2CliffordT] = cliffords
    seen = set(cliffords)
    yield cliffords
    for n in range(1, max_num_ts + 1):
        nxt = []
        for r in tqdm(frontier, f"generate level {n}", disable=not with_progress_bar):
            for t in su2_ct.Ts:
                rot = r @ t
                if any(u in seen for u in (rot, -rot)):
                    continue
                seen.add(rot)
                nxt.append(rot)
        if verbose:
            print(n, len(nxt))
        yield nxt
        frontier = nxt


def generate_rotations(
    max_num_ts: int, with_progress_bar: bool = True, verbose: bool = False
) -> list[Sequence[su2_ct.SU2CliffordT]]:
    """Returns a list of lists where the kth list contains Clifford+T unitaries that use k Ts.

    Args:
        max_num_ts: the maximum number of T gates to use.
        with_progress_bar: whether to display a progress bar or not.
        verbose: whether to print debug statements or not.
    Returns:
        list containing max_num_ts+1 lists where the kth list contains Clifford+T unitaries
        that use k T gates.
    """
    return [*generate_rotations_iter(max_num_ts, with_progress_bar, verbose)]
