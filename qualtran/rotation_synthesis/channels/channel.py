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

from __future__ import annotations

import abc
from typing import Optional, Sequence

import attrs

import qualtran.rotation_synthesis._typing as rst
import qualtran.rotation_synthesis.math_config as mc
import qualtran.rotation_synthesis.rings as rings
from qualtran.rotation_synthesis.matrix import su2_ct
from qualtran.rotation_synthesis.rings import zsqrt2


class Channel(abc.ABC):

    @abc.abstractmethod
    def expected_num_ts(self, config: mc.MathConfig) -> rst.Real: ...

    @abc.abstractmethod
    def diamond_norm_distance_to_rz(self, theta: rst.Real, config: mc.MathConfig) -> rst.Real:
        r"""Returns the diamond norm distance to $Rz(2\theta)$."""


@attrs.frozen
class UnitaryChannel(Channel):
    r"""A Unitary operation.

    The unitary matrix of an $SU(2)$ matrix is defined with two complex numbers $u, v$ as
    $$
    \begin{bmatrix}
    u & -v^*\\
    v & u^*
    \end{bmatrix}
    $$
    for clifford+T unitarys the matrix can be written as
    $$
    \frac{1}{\sqrt{2(2+\sqrt{2})^n}}
    \begin{bmatrix}
    p & -q^*\\
    q & p^*
    \end{bmatrix}
    $$
    where $n$ is the number of T gates and $p, q \in \mathbb{Z}[e^{i\pi/4}]$.


    Attributes:
        p: The upper left elemenet of the clifford+T matrix.
        q: The lower left elemenet of the clifford+T matrix.
        n: The number of T gates.
        twirl: If True, the unitary is twirled with gates equiprobable chosen
            from the gates $\{I, Z, S, S^\dagger\}$.
    """

    p: rings.ZW = attrs.field(validator=attrs.validators.instance_of(rings.ZW))
    q: rings.ZW = attrs.field(validator=attrs.validators.instance_of(rings.ZW))
    n: int = attrs.field(validator=attrs.validators.instance_of(int))
    twirl: bool = False

    def to_matrix(self) -> su2_ct.SU2CliffordT:
        return su2_ct.SU2CliffordT.from_pair(self.p, self.q, pick_phase=True)

    def expected_num_ts(self, config: Optional[mc.MathConfig] = None) -> rst.Real:
        return self.n

    def rotation_angle(self, config: mc.MathConfig) -> rst.Real:
        """Returns the rotation angle applied with diag(self)."""
        return self.p.polar(config)[1]

    def failure_angle(self, config: mc.MathConfig) -> rst.Real:
        """Returns the rotation angle applied with antidiag(self)."""
        return self.q.polar(config)[1]

    def diamond_norm_distance_to_rz(self, theta: rst.Real, config: mc.MathConfig) -> rst.Real:
        u = self.p.value(config.sqrt2)
        u = u / zsqrt2.radius_at_n(zsqrt2.LAMBDA_KLIUCHNIKOV, self.n, config)
        neg_rot = config.cos(theta) - config.sin(theta) * 1j
        real_squared = (u * neg_rot).real ** 2
        if self.twirl:
            return 2 * (1 - real_squared)
        return 2 * config.sqrt(1 - real_squared)

    @classmethod
    def from_sequence(cls, seq: Sequence[str], twirl: bool = False) -> UnitaryChannel:
        """Constructs a unitary channel from a sequence of gate names.

        Args:
            seq: A sequence of gate names in circuit order.
               Supported gate names are {Tx, Ty, Tz, H, S, X, Y, Z}.
            twirl: Whether the unitary is applied with a ZS twirling or not.

        Returns:
            A UnitaryChannel.
        """
        u = su2_ct.SU2CliffordT.from_sequence(seq)
        n = sum(g.startswith("T") for g in seq)
        return UnitaryChannel(u.matrix[0, 0], u.matrix[1, 0], n, twirl)


@attrs.frozen
class ProjectiveChannel(Channel):
    """A fallback (a.k.a RUS channel).

    This channel applies the following circuit where $V$ is the `rotation` channel and $C$ is the
    correction channel.

    q: ─────────@───V───@───────Y───C───
                │       │       ║   ║
    ancilla: ───X───────X───M───╫───╫───
                            ║   ║   ║
    m: ═════════════════════@═══^═══^═══

    Attributes:
        rotation: This first half of the channel (i.e. $V$).
        correction: The correction channel, this is applied only when the measurement result is one
    """

    rotation: UnitaryChannel
    correction: Channel

    def success_probability(self, config: mc.MathConfig) -> rst.Real:
        """Constructs a probablity of a zero measurement."""
        v = self.rotation.q.polar(config)[0] / zsqrt2.radius_at_n(
            zsqrt2.LAMBDA_KLIUCHNIKOV, self.rotation.n, config
        )
        return 1 - v * v

    def rotation_angle(self, config: mc.MathConfig) -> rst.Real:
        """Returns the rotation angle applied with when the measurement result is zero."""
        return self.rotation.rotation_angle(config)

    def failure_angle(self, config: mc.MathConfig) -> rst.Real:
        """Returns the rotation angle applied with when the measurement result is one."""
        return self.rotation.failure_angle(config)

    def expected_num_ts(self, config: mc.MathConfig) -> rst.Real:
        v = self.rotation.q.value(config.sqrt2)
        fail_prob = (v * v.conjugate()).real / zsqrt2.radius2_at_n(
            zsqrt2.LAMBDA_KLIUCHNIKOV, self.rotation.n, config
        )
        return self.rotation.expected_num_ts(config) + fail_prob * self.correction.expected_num_ts(
            config
        )

    @staticmethod
    def diamond_distance_to_rz_on_measurement_success(
        p: rings.ZW, theta: rst.Real, config: mc.MathConfig
    ) -> rst.Real:
        """Returns the diamond norm distance when the measurement result is zero."""
        u = p.value(config.sqrt2)
        arg_u = config.arctan2(u.imag, u.real)
        return 2 * abs(config.sin(arg_u - theta))

    def diamond_norm_distance_to_rz(self, theta: rst.Real, config: mc.MathConfig) -> rst.Real:
        p = self.success_probability(config)
        return p * ProjectiveChannel.diamond_distance_to_rz_on_measurement_success(
            self.rotation.p, theta, config
        ) + (1 - p) * self.correction.diamond_norm_distance_to_rz(
            theta - self.failure_angle(config), config
        )


@attrs.frozen
class ProbabilisticChannel(Channel):
    """A Channel that randomly applies one of two channels.

    Attributes:
        c1: The first channel.
        c2: The second channel.
        probability: The probablility of applying the first channel.
    """

    c1: Channel
    c2: Channel
    probability: rst.Real = attrs.field(default=1, converter=lambda x: max(min(x, 1), 0))

    def expected_num_ts(self, config: mc.MathConfig) -> rst.Real:
        return self.probability * self.c1.expected_num_ts(config) + (
            1 - self.probability
        ) * self.c2.expected_num_ts(config)

    def diamond_norm_distance_to_rz(self, theta: rst.Real, config: mc.MathConfig) -> rst.Real:
        if isinstance(self.c1, UnitaryChannel) and isinstance(self.c2, UnitaryChannel):
            return self.probability * self.c1.diamond_norm_distance_to_rz(theta, config) + (
                1 - self.probability
            ) * self.c2.diamond_norm_distance_to_rz(theta, config)
        elif isinstance(self.c1, ProjectiveChannel) and isinstance(self.c2, ProjectiveChannel):
            under = self.c1
            over = self.c2
            q1 = under.success_probability(config)
            q2 = over.success_probability(config)
            delta1 = under.rotation_angle(config) - theta
            delta2 = over.rotation_angle(config) - theta
            under_err = q1 * 2 * config.sin(delta1) ** 2 + (
                1 - q1
            ) * under.correction.diamond_norm_distance_to_rz(
                theta - under.failure_angle(config), config
            )
            over_err = q2 * 2 * config.sin(delta2) ** 2 + (
                1 - q2
            ) * over.correction.diamond_norm_distance_to_rz(
                theta - over.failure_angle(config), config
            )
            return self.probability * under_err + (1 - self.probability) * over_err
        else:
            raise NotImplementedError()

    @classmethod
    def from_unitary_channels(
        cls, u1: UnitaryChannel, u2: UnitaryChannel, target_theta: rst.Real, config: mc.MathConfig
    ) -> ProbabilisticChannel:
        r1, phi1 = u1.p.polar(config)
        r2, phi2 = u2.p.polar(config)
        delta1 = phi1 - target_theta
        delta2 = phi2 - target_theta
        r1 /= zsqrt2.radius_at_n(zsqrt2.LAMBDA_KLIUCHNIKOV, u1.n, config)
        r2 /= zsqrt2.radius_at_n(zsqrt2.LAMBDA_KLIUCHNIKOV, u2.n, config)
        prob = (
            r2**2
            * config.sin(2 * delta2)
            / (r2**2 * config.sin(2 * delta2) - r1**2 * config.sin(2 * delta1))
        )
        return ProbabilisticChannel(u1, u2, prob)

    @classmethod
    def from_projective_channels(
        cls,
        under_channel: ProjectiveChannel,
        over_channel: ProjectiveChannel,
        target_theta: rst.Real,
        config: mc.MathConfig,
    ) -> ProbabilisticChannel:
        q1 = under_channel.success_probability(config)
        q2 = over_channel.success_probability(config)
        term1 = q1 * config.sin(2 * (under_channel.rotation_angle(config) - target_theta))
        term2 = q2 * config.sin(2 * (over_channel.rotation_angle(config) - target_theta))
        assert term1 <= 0
        assert term2 >= 0
        prob = term2 / (term2 - term1)
        return ProbabilisticChannel(under_channel, over_channel, prob)
