#  Copyright 2024 Google LLC
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
import numpy as np
import pytest
import sympy

from qualtran._infra.data_types import QAny
from qualtran._infra.registers import Register
from qualtran.bloqs.data_loading.qroam_clean import (
    _qroam_clean_multi_data,
    _qroam_clean_multi_dim,
    get_optimal_log_block_size_clean_ancilla,
    QROAMClean,
    QROAMCleanAdjoint,
    QROAMCleanAdjointWrapper,
)
from qualtran.drawing.musical_score import Circle, LarrowTextBox, RarrowTextBox, Text, TextBox
from qualtran.resource_counting import get_cost_value, QubitCount
from qualtran.symbolics import ceil, log2


def test_bloq_examples(bloq_autotester):
    bloq_autotester(_qroam_clean_multi_data)
    bloq_autotester(_qroam_clean_multi_dim)


@pytest.mark.parametrize(
    "reg, reg_type",
    [
        (None, Text),
        (Register("selection", QAny(5)), TextBox),
        (Register("selection0", QAny(5)), TextBox),
        (Register("target0_", QAny(5)), RarrowTextBox),
        (Register("junk_target0_", QAny(5)), RarrowTextBox),
        (Register("control", QAny(5)), Circle),
    ],
)
def test_wire_symbol(reg, reg_type):
    bloq = _qroam_clean_multi_dim.make()
    assert isinstance(bloq.wire_symbol(reg, ()), reg_type)
    assert isinstance(bloq.adjoint().wire_symbol(reg, ()), reg_type)


@pytest.mark.parametrize(
    "reg, reg_type",
    [
        (None, Text),
        (Register("selection", QAny(5)), TextBox),
        (Register("selection0", QAny(5)), TextBox),
        (Register("target0_", QAny(5)), LarrowTextBox),
        (Register("control", QAny(5)), Circle),
    ],
)
def test_adjoint_wire_symbol(reg, reg_type):
    data1 = np.arange(25, dtype=int).reshape((5, 5))
    data2 = (np.arange(25, dtype=int) + 1).reshape((5, 5))
    adjoint_bloq = QROAMCleanAdjoint.build_from_data(data1, data2, log_block_sizes=(1, 1))
    assert isinstance(adjoint_bloq.wire_symbol(reg, ()), reg_type)


def test_qroam_clean_qubit_counts():
    bloq = _qroam_clean_multi_data.make()
    assert get_cost_value(bloq, QubitCount()) == get_cost_value(bloq.decompose_bloq(), QubitCount())
    bloq = _qroam_clean_multi_dim.make()
    assert get_cost_value(bloq, QubitCount()) == get_cost_value(bloq.decompose_bloq(), QubitCount())
    # Symbolic
    N, b, k = sympy.symbols('N b k', positive=True, integer=True)
    bloq = QROAMClean.build_from_bitsize((N,), (b,), log_block_sizes=(k,))
    K = 2**k
    # log(N) - k ancilla are required for the nested unary iteration.
    expected_qubits = K * b + 2 * ceil(log2(N)) - k - 1
    assert sympy.simplify(get_cost_value(bloq, QubitCount()) - expected_qubits) == 0


def test_t_complexity_1d_data_symbolic():
    # 1D data, 1 dataset
    N, b, k = sympy.symbols('N b k')
    bloq = QROAMClean.build_from_bitsize((N,), (b,), log_block_sizes=(k,))
    K = 2**k
    expected_toffoli = ceil(N / K) + (K - 1) * b - 2
    assert bloq.t_complexity().t == 4 * expected_toffoli
    bloq_inv = bloq.adjoint()
    assert isinstance(bloq_inv, QROAMCleanAdjointWrapper)
    inv_k = sympy.symbols('kinv')
    inv_K = 2**inv_k
    bloq_inv = bloq_inv.with_log_block_sizes(log_block_sizes=(inv_k,))
    expected_toffoli_inv = ceil(N / inv_K) + inv_K - 4
    assert bloq_inv.t_complexity().t == 4 * expected_toffoli_inv


def test_t_complexity_2d_data_symbolic():
    # 2D data, 1 dataset
    N1, N2, b, k1, k2 = sympy.symbols('N1 N2 b k1, k2')
    bloq = QROAMClean.build_from_bitsize((N1, N2), (b,), log_block_sizes=(k1, k2))
    K1, K2 = 2**k1, 2**k2
    expected_toffoli = ceil(N1 / K1) * ceil(N2 / K2) + (K1 * K2 - 1) * b - 2
    assert bloq.t_complexity().t == 4 * expected_toffoli
    bloq_inv = bloq.adjoint()
    assert isinstance(bloq_inv, QROAMCleanAdjointWrapper)
    inv_k1, inv_k2 = sympy.symbols('kinv1, kinv2')
    inv_K1, inv_K2 = 2**inv_k1, 2**inv_k2
    bloq_inv = bloq_inv.with_log_block_sizes(log_block_sizes=(inv_k1, inv_k2))
    expected_toffoli_inv = ceil(N1 * N2 / (inv_K1 * inv_K2)) + inv_K1 * inv_K2 - 4
    assert bloq_inv.t_complexity().t == 4 * expected_toffoli_inv


@pytest.mark.parametrize('n', range(3, 8))
def test_qroam_default_log_block_sizes(n: int):
    data = np.arange(2**n)
    bloq = QROAMClean.build_from_data(data, data, target_bitsizes=(n.bit_length(), n.bit_length()))
    bs = get_optimal_log_block_size_clean_ancilla(len(data), sum(bloq.target_bitsizes))
    assert bs == bloq.log_block_sizes[0]
    bloq = bloq.adjoint().qroam_clean_adjoint_bloq
    bs = get_optimal_log_block_size_clean_ancilla(
        len(data), sum(bloq.target_bitsizes), adjoint=True
    )
    assert bs == bloq.log_block_sizes[0]


def test_qroam_clean_classical_sim():
    rng = np.random.default_rng(42)
    # 1D data, 1 dataset
    N, max_N, log_block_sizes = 25, 2**10, 3
    data = rng.integers(max_N, size=N)
    bloq = QROAMClean.build_from_data(data, log_block_sizes=log_block_sizes, num_controls=1)
    cbloq = bloq.decompose_bloq()
    bloq_inv = bloq.adjoint()
    assert isinstance(bloq_inv, QROAMCleanAdjointWrapper)
    for x in range(N):
        vals = bloq.call_classically(selection=x, control=1)
        cvals = cbloq.call_classically(selection=x, control=1)
        assert vals[0:3] == cvals[0:3] == (1, x, data[x])
        assert np.array_equal(vals[3], cvals[3])
        assert bloq_inv.call_classically(
            control=vals[0], selection=vals[1], target0_=vals[2], junk_target0_=vals[3]
        ) == (1, x)

    # 2D data, 1 datasets
    N, M, max_N, log_block_sizes = 7, 11, 2**5, (2, 3)
    data = rng.integers(max_N, size=N * M).reshape(N, M)
    bloq = QROAMClean.build_from_data(data, log_block_sizes=log_block_sizes)
    cbloq = bloq.decompose_bloq()
    bloq_inv = bloq.adjoint()
    assert isinstance(bloq_inv, QROAMCleanAdjointWrapper)
    for x in range(N):
        for y in range(M):
            vals = bloq.call_classically(selection0=x, selection1=y)
            cvals = cbloq.call_classically(selection0=x, selection1=y)
            assert vals[0:3] == cvals[0:3] == (x, y, data[x][y])
            assert np.array_equal(vals[3], cvals[3])
            assert bloq_inv.call_classically(
                selection0=x, selection1=y, target0_=vals[2], junk_target0_=vals[3]
            ) == (x, y)


@pytest.mark.slow
def test_qroam_clean_classical_sim_multi_dataset():
    rng = np.random.default_rng(42)
    # 1D data, 2 datasets
    N, max_N, log_block_sizes = 25, 2**20, 3
    data = [rng.integers(max_N, size=N), rng.integers(max_N, size=N)]
    bloq = QROAMClean.build_from_data(*data, log_block_sizes=log_block_sizes)
    cbloq = bloq.decompose_bloq()
    bloq_inv = bloq.adjoint()
    assert isinstance(bloq_inv, QROAMCleanAdjointWrapper)
    for x in range(N):
        vals = bloq.call_classically(selection=x)
        cvals = cbloq.call_classically(selection=x)
        assert vals[0:3] == cvals[0:3] == (x, data[0][x], data[1][x])
        assert np.array_equal(vals[3], cvals[3]) and np.array_equal(vals[4], cvals[4])
        assert bloq_inv.call_classically(
            selection=vals[0],
            target0_=vals[1],
            target1_=vals[2],
            junk_target0_=vals[3],
            junk_target1_=vals[4],
        ) == (x,)

    # 2D data, 2 datasets
    N, M, max_N, log_block_sizes = 7, 11, 2**5, np.array([2, 3])  # type: ignore[misc]
    data = [
        rng.integers(max_N, size=N * M).reshape(N, M),
        rng.integers(max_N, size=N * M).reshape(N, M),
    ]
    bloq = QROAMClean.build_from_data(*data, log_block_sizes=tuple(log_block_sizes.tolist()))
    cbloq = bloq.decompose_bloq()
    bloq_inv = bloq.adjoint()
    assert isinstance(bloq_inv, QROAMCleanAdjointWrapper)
    for x in range(N):
        for y in range(M):
            vals = bloq.call_classically(selection0=x, selection1=y)
            cvals = cbloq.call_classically(selection0=x, selection1=y)
            assert vals[0:4] == cvals[0:4] == (x, y, data[0][x][y], data[1][x][y])
            assert np.array_equal(vals[4], cvals[4]) and np.array_equal(vals[5], cvals[5])
            assert bloq_inv.call_classically(
                selection0=x,
                selection1=y,
                target0_=vals[2],
                junk_target0_=vals[4],
                target1_=vals[3],
                junk_target1_=vals[5],
            ) == (x, y)


def test_qroam_clean_small_bloq_counts():
    qroam_clean = QROAMClean(
        data_or_shape=(np.array([0, 7]),),
        selection_bitsizes=(1,),
        target_bitsizes=(6,),
        target_shapes=((),),
        num_controls=0,
        log_block_sizes=(0,),
    )
    assert qroam_clean.t_complexity().t == 0
    qroam_clean_adj_wrapper = QROAMCleanAdjointWrapper(
        qroam_clean=qroam_clean, log_block_sizes=(0,)
    )
    assert qroam_clean_adj_wrapper.t_complexity().t == 0
