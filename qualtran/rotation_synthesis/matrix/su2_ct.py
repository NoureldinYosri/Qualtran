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

import functools
import itertools
from typing import cast, Optional, Sequence, Union

import attrs
import numpy as np

from qualtran.rotation_synthesis.rings import zsqrt2, zw


@attrs.frozen(eq=False)
class SU2CliffordT:
    r"""A scaled $SU(2)$ unitary exactly synthesizable with Clifford+T gateset.

    An $SU(2)$ matrix that can be synthetized exactly with Clifford+T gates can be written as
    $$
        \frac{1}{\sqrt{2(2+\sqrt{2})^n}} \begin{bmatrix}
        u & -v^*\\
        v & u^*\\
        \end{bmatrix}
    $$
    Where $u, v \in \mathbb{Z}[e^{i \pi/4}]$ and $n$ is the needed number of $T$ gates with a
    determinant $\frac{1}{2(2+\sqrt{2})^n} (|u|^2 + |v|^2) = 1$.

    Instances of this class represent the matrix [[u, -v^*], [v, u^*]] with the scaling factor
    being implicit.

    Attributes:
        matrix: The scaled version of the $SU(2)$ unitary.
        gates: A tuple of strings representing the Clifford+T gates whose action gives this unitary
            The gates are given in circuit order and the property is present only if the object is
            constructed through multiplication.
    """

    matrix: np.ndarray = attrs.field(converter=np.asarray)
    gates: Optional[tuple[str, ...]] = None

    def __mul__(self, other):
        assert not isinstance(other, SU2CliffordT)
        return SU2CliffordT(self.matrix * other, self.gates)

    def __matmul__(self, other: "SU2CliffordT") -> "SU2CliffordT":
        res = self.matrix @ other.matrix
        for v in res.flat:
            assert v.is_divisible_by(zw.SQRT_2)
        gates: Optional[tuple[str, ...]] = None
        if self.gates is not None and other.gates is not None:
            gates = other.gates + self.gates
        return SU2CliffordT([[v // zw.SQRT_2 for v in r] for r in res], gates)

    def __rmul__(self, other):
        assert not isinstance(other, SU2CliffordT)
        return self * other

    def __neg__(self):
        return SU2CliffordT(-self.matrix)

    def __add__(self, other):
        return SU2CliffordT(self.matrix + other.matrix)

    def __sub__(self, other):
        return SU2CliffordT(self.matrix - other.matrix)

    def __hash__(self):
        return hash(tuple(map(tuple, self.matrix)))

    def __eq__(self, other):
        return np.all(self.matrix == other.matrix)

    def numpy(self) -> np.ndarray:
        return self.matrix.astype(complex)

    def adjoint(self) -> "SU2CliffordT":
        return SU2CliffordT(self.matrix.T.conj())

    def scale_down(self) -> Union["SU2CliffordT", None]:
        for v in self.matrix.flat:
            if not v.is_divisible_by(zw.LAMBDA_KLIUCHNIKOV):
                return None
        return SU2CliffordT(
            [[v // zw.LAMBDA_KLIUCHNIKOV for v in r] for r in self.matrix], self.gates
        )

    def det(self) -> zsqrt2.ZSqrt2:
        a, b, c, d = self.matrix.reshape(-1)
        res = a * d - b * c
        real, imag, need_w = res.to_zsqrt2()
        assert not need_w
        assert imag == zsqrt2.Zero
        return real

    @staticmethod
    def from_sequence(seq: Sequence[str]) -> "SU2CliffordT":
        """Creates an SU2CliffordT from a Clifford+T gate sequence."""
        u = ISqrt2
        for g in seq:
            u = GATE_MAP[g] @ u
        return u

    def parametric_form(self) -> tuple[zsqrt2.ZSqrt2, zsqrt2.ZSqrt2, zsqrt2.ZSqrt2, zsqrt2.ZSqrt2]:
        real0, imag0, n0 = self.matrix[0, 0].to_zsqrt2()
        d = imag0 * zsqrt2.SQRT_2 + n0
        real1, imag1, n1 = self.matrix[1, 0].to_zsqrt2()
        if n1:
            b = imag1 + (zsqrt2.One - d).divide_by_sqrt2()
        else:
            b = imag1 - imag0

        c = -real1 - (zsqrt2.ZSqrt2(n1, 0) + d).divide_by_sqrt2()
        a = (real0 - b - c + (zsqrt2.ZSqrt2(n0, 0) - d).divide_by_sqrt2()).divide_by_sqrt2()
        return a, b, c, d

    @staticmethod
    def from_parametric_form(
        pf: tuple[zsqrt2.ZSqrt2, zsqrt2.ZSqrt2, zsqrt2.ZSqrt2, zsqrt2.ZSqrt2]
    ) -> "SU2CliffordT":
        res = np.array([zw.Zero] * 4).reshape((2, 2))
        for a, m in zip(pf, PARAMETRIC_FORM_BASES):
            res += m * zw.ZW.from_pair(a, zsqrt2.Zero, False)
        return SU2CliffordT(res)

    @functools.cached_property
    def _key(self) -> tuple[int, int, int, int]:
        pf = self.parametric_form()
        # the gate choice depends on the parametric form mod 2 + sqrt(2)
        # for elements of Z[sqrt(2)] this is equivalent ot taking the mod with sqrt(2)
        # which is the same as the parity of the integer part.
        return cast(tuple[int, int, int, int], tuple(v.a % 2 for v in pf))

    def to_sequence(self) -> tuple[str, ...]:
        if self.det() == 2:
            cliffords = generate_cliffords()
            if self in cliffords:
                return cliffords[self]
            return ("Z", "X", "Z", "X") + cliffords[-self]

        t = _key_map()[self._key]
        nxt = (GATE_MAP[t].adjoint() @ self).scale_down()
        assert nxt.det() < self.det()
        return nxt.to_sequence() + (t,)

    @classmethod
    def from_pair(
        cls: type["SU2CliffordT"], p: zw.ZW, q: zw.ZW, pick_phase: bool = False
    ) -> "SU2CliffordT":
        """Creates an SU2CliffordT instance from a pair of ZW rst.

        The matrix is constructed as [[p, -q.conj()], [q, p.conj()]].
        If pick_phase is True, it tries different phases for q to find a valid SU2CliffordT.

        Args:
            p: The top-left element of the matrix.
            q: The bottom-left element of the matrix.
            pick_phase: Whether to try different phases for q to ensure validity.

        Returns:
            An instance of SU2CliffordT.

        Raises:
            ValueError: If a valid SU(2) matrix can't be construct from the give pair.
        """
        if pick_phase:
            for exponent in range(8):
                phase = zw.Omega**exponent
                nq = q * phase
        if pick_phase:
            for exponent in range(8):
                phase = zw.Omega**exponent
                nq = q * phase
                res = SU2CliffordT([[p, -nq.conj()], [nq, p.conj()]])
                if res.is_valid():
                    return res
            raise ValueError(f"can't construct a valid SU(2) matrix from the given pair {p=} {q=}")
        else:
            res = cls([[p, -q.conj()], [q, p.conj()]])
            if not res.is_valid():
                raise ValueError(
                    f"can't construct a valid SU(2) matrix from the given pair {p=} {q=}"
                )
            return res

    def is_valid(self) -> bool:
        det = self.det()
        l_v = zsqrt2.ZSqrt2(2, 1)
        two = zsqrt2.ZSqrt2(2, 0)
        while det > two and det.is_divisible_by(l_v):
            det = det // l_v
        if det != two:
            return False

        _, _, n0 = self.matrix[0, 0].to_zsqrt2()
        _, _, n1 = self.matrix[1, 0].to_zsqrt2()
        return n0 == n1


_KEY_MAP = {
    (0, 0, 0, 0): "Tx",
    (0, 0, 1, 0): "Tz",
    (0, 1, 0, 0): "Ty",
    (0, 1, 1, 0): "Tx",
    (1, 0, 1, 0): "Tx",
    (1, 1, 0, 0): "Tx",
    (1, 1, 1, 0): "Tz",
}


@functools.cache
def _key_map():
    Ts = {"Tx": Tx, "Ty": Ty, "Tz": Tz}
    ret = {}
    for vec in itertools.product(range(2), repeat=4):
        if np.all(np.array(vec) == 0):
            pf = (zsqrt2.ZSqrt2(2, 0),) * 4
        else:
            pf = cast(
                tuple[zsqrt2.ZSqrt2, zsqrt2.ZSqrt2, zsqrt2.ZSqrt2, zsqrt2.ZSqrt2],
                tuple(zsqrt2.ZSqrt2(v, 0) for v in vec),
            )
        g = SU2CliffordT.from_parametric_form(pf)
        best = (g.det(), "")
        for name, t in Ts.items():
            ng = (t.adjoint() @ g).scale_down()
            if ng is None:
                continue
            best = min(best, (ng.det(), name))
        if best[0] >= g.det():
            continue
        ret[vec] = best[1]
    return ret


# H gate scaled by sqrt(2) to make its elements belong to Z[w] and 1j to make its determinant = 2
HSqrt2 = zw.J * SU2CliffordT(np.array([[zw.One, zw.One], [zw.One, -zw.One]]), ("H",))

# S gate scaled by sqrt(2) to make its elements belong to Z[w] and w^* to make its determinant = 2
SSqrt2 = (
    zw.SQRT_2
    * zw.Omega.conj()
    * SU2CliffordT(np.array([[zw.One, zw.Zero], [zw.Zero, zw.J]]), ("S",))
)

# Paulis
ISqrt2: SU2CliffordT = zw.SQRT_2 * SU2CliffordT(
    np.array([[zw.One, zw.Zero], [zw.Zero, zw.One]]), ()
)

ZSqrt2: SU2CliffordT = -SSqrt2 @ SSqrt2
XSqrt2: SU2CliffordT = HSqrt2 @ ZSqrt2 @ HSqrt2.adjoint()
YSqrt2: SU2CliffordT = ZSqrt2 @ XSqrt2

_X = np.array([[zw.Zero, zw.One], [zw.One, zw.Zero]])
_Y = np.array([[zw.Zero, -zw.J], [zw.J, zw.Zero]])
_Z = np.array([[zw.One, zw.Zero], [zw.Zero, -zw.One]])
_I = np.array([[zw.One, zw.Zero], [zw.Zero, zw.One]])

# Tx, Ty, Tz scaled by sqrt(2*(2+sqrt(2)))
Tx = SU2CliffordT(_I * zw.SQRT_2 + _I - _X * zw.J, ("Tx",))
Ty = SU2CliffordT(_I * zw.SQRT_2 + _I - _Y * zw.J, ("Ty",))
Tz = SU2CliffordT(_I * zw.SQRT_2 + _I - _Z * zw.J, ("Tz",))
Ts = [Tx, Ty, Tz]


GATE_MAP = {
    "I": ISqrt2,
    "S": SSqrt2,
    "H": HSqrt2,
    "Tx": Tx,
    "Ty": Ty,
    "Tz": Tz,
    "X": XSqrt2,
    "Y": YSqrt2,
    "Z": ZSqrt2,
}

PARAMETRIC_FORM_BASES = [
    _I * zw.SQRT_2,
    _I + _X * zw.J,
    _I + _Y * zw.J,
    np.array([[zw.Omega, zw.Omega], [-zw.Omega.conj(), zw.Omega.conj()]]),
]


@functools.cache
def generate_cliffords() -> dict[SU2CliffordT, tuple[str, ...]]:
    ret = []
    st = [ISqrt2]
    seen = set(st)
    while st:
        c = st.pop()
        ret.append(c)
        assert len(ret) <= 24
        for p in SSqrt2, HSqrt2:
            nc = c @ p
            if not any(u in seen for u in [nc, -nc]):
                st.append(nc)
                seen.add(nc)
    assert len(ret) == 24
    return cast(dict[SU2CliffordT, tuple[str, ...]], {v: v.gates for v in ret})
