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
import abc
from collections import Counter
from functools import cached_property
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    TYPE_CHECKING,
    TypeAlias,
    Union,
)

import attrs
import numpy as np
from numpy.typing import NDArray

from ..symbolics import is_symbolic, prod, Shaped, SymbolicInt
from .bloq import Bloq, DecomposeNotImplementedError, DecomposeTypeError
from .data_types import CDType, QBit, QCDType, QDType
from .gate_with_registers import GateWithRegisters
from .registers import Register, Side, Signature

if TYPE_CHECKING:
    import cirq
    import quimb.tensor as qtn

    from qualtran import Bloq, BloqBuilder, CompositeBloq, ConnectionT, SoquetT
    from qualtran.cirq_interop import CirqQuregT
    from qualtran.drawing import WireSymbol
    from qualtran.resource_counting import BloqCountDictT, SympySymbolAllocator
    from qualtran.simulation.classical_sim import ClassicalValRetT, ClassicalValT

ControlBit: TypeAlias = int
"""A control bit, either 0 or 1."""


def _cvs_convert(
    cvs: Union[
        int,
        np.integer,
        NDArray[np.integer],
        Shaped,
        Sequence[Union[int, np.integer]],
        Sequence[Sequence[Union[int, np.integer]]],
        Sequence[Union[NDArray[np.integer], Shaped]],
    ]
) -> Tuple[Union[NDArray[np.integer], Shaped], ...]:
    if isinstance(cvs, Shaped):
        return (cvs,)
    if isinstance(cvs, (int, np.integer)):
        return (np.array(cvs),)
    if isinstance(cvs, np.ndarray):
        return (cvs,)
    if all(isinstance(cv, (int, np.integer)) for cv in cvs):
        return (np.asarray(cvs),)
    return tuple(cv if isinstance(cv, Shaped) else np.asarray(cv) for cv in cvs)


@attrs.frozen(eq=False)
class CtrlSpec:
    """A specification for how to control a bloq.

    This class can be used by controlled bloqs to specify the condition under which the bloq
    is active.

    In the simplest form, a controlled gate is active when the control input is one qubit of data,
    and it's in the |1> state. Otherwise, the gate is not performed. This corresponds to the
    following two equivalent CtrlSpecs:

        CtrlSpec()
        CtrlSpec(qdtypes=QBit(), cvs=1)

    This class supports additional control specifications:
     1. 'negative' controls where the bloq is active if the input is |0>.
     2. integer-equality controls where a QInt input must match an integer control value.
     3. ndarrays of control values, where the bloq is active if **all** inputs are active.
     4. Multiple control registers, control values for each of which can be specified
        using 1-3 above.

    For example:
    1. `CtrlSpec(qdtypes=QUInt(4), cvs=0b0110)`:
            Ctrl for a single register, of type `QUInt(4)` and shape `()`, is active when the
            soquet of the input register takes value 6.
    2. `CtrlSpec(cvs=[0, 1, 1, 0])`:
            Ctrl for a single register, of type `QBit()` and shape `(4,)`, is active when soquets
            of input register take values `[0, 1, 1, 0]`.
    3. `CtrlSpec(qdtypes=[QBit(), QBit()], cvs=[[0, 1], [1, 0]]).is_active([0, 1], [1, 0])`:
            Ctrl for 2 registers, each of type `QBit()` and shape `(2,)`, is active when the
            soquet for each register takes values `[0, 1]` and  `[1, 0]` respectively.

    CtrlSpec uses logical AND among all control register clauses. If you need a different boolean
    function, open a GitHub issue.

    Args:
        qdtypes: A tuple of quantum data types, one per ctrl register.
        cvs: A tuple of control value(s), one per ctrl register. For each element in the tuple,
            if more than one ctrl value is provided, they must all be compatible with `qdtype`
            and the bloq is implied to be active if **all** inputs are active (i.e. the "shape"
            of the ctrl register is implied to be `cv.shape`).
    """

    qdtypes: Tuple[QCDType, ...] = attrs.field(
        default=QBit(), converter=lambda qt: (qt,) if isinstance(qt, QCDType) else tuple(qt)
    )
    cvs: Tuple[Union[NDArray[np.integer], Shaped], ...] = attrs.field(
        default=1, converter=_cvs_convert
    )

    def __attrs_post_init__(self):
        assert len(self.qdtypes) == len(self.cvs)

    @cached_property
    def num_ctrl_reg(self) -> int:
        return len(self.qdtypes)

    @cached_property
    def shapes(self) -> Tuple[Tuple[SymbolicInt, ...], ...]:
        """Tuple of shapes of control registers represented by this CtrlSpec."""
        return tuple(cv.shape for cv in self.cvs)

    @cached_property
    def concrete_shapes(self) -> tuple[tuple[int, ...], ...]:
        """Tuple of shapes of control registers represented by this CtrlSpec."""
        shapes = self.shapes
        if is_symbolic(*shapes):
            raise ValueError(f"cannot get concrete shapes: found symbolic {self.shapes}")
        return shapes  # type: ignore

    @cached_property
    def num_bits(self) -> SymbolicInt:
        """Total number of bits required for control registers represented by this CtrlSpec."""
        return sum(dtype.num_bits * prod(shape) for dtype, shape in zip(self.qdtypes, self.shapes))

    @cached_property
    def num_qubits(self) -> SymbolicInt:
        """Total number of qubits required for control registers represented by this CtrlSpec."""
        return sum(
            dtype.num_qubits * prod(shape) for dtype, shape in zip(self.qdtypes, self.shapes)
        )

    @cached_property
    def num_cbits(self) -> SymbolicInt:
        """Total number of classical bits required for control registers represented by this CtrlSpec."""
        return sum(dtype.num_cbits * prod(shape) for dtype, shape in zip(self.qdtypes, self.shapes))

    def is_symbolic(self):
        return is_symbolic(*self.qdtypes) or is_symbolic(*self.cvs)

    def activation_function_dtypes(self) -> Sequence[Tuple[QCDType, Tuple[SymbolicInt, ...]]]:
        """The data types that serve as input to the 'activation function'.

        The activation function takes in (quantum) inputs of these types and shapes and determines
        whether the bloq should be active. This method is useful for setting up appropriate
        control registers for a ControlledBloq.

        Returns:
            A sequence of (type, shape) tuples analogous to the arguments to `Register`.
        """
        return [(qdtype, cv.shape) for qdtype, cv in zip(self.qdtypes, self.cvs)]

    def is_active(self, *vals: 'ClassicalValT') -> bool:
        """A classical implementation of the 'activation function'.

        The activation function takes in (quantum) data and determines whether
        the bloq should be active. This method captures the same behavior on specific classical
        values representing computational basis states.

        This implementation evaluates to `True` if all the values match `self.cvs`.

        Args:
            *vals: The classical values (that fit within the types given by
                `activation_function_dtypes`) on which we evaluate whether the spec is active.

        Returns:
            True if the specific input values evaluate to `True` for this CtrlSpec.
        """
        if self.is_symbolic():
            raise ValueError(f"Cannot compute activation for symbolic {self}")
        if len(vals) != self.num_ctrl_reg:
            raise ValueError(f"Incorrect number of inputs for {self}: {len(vals)}.")

        for val, cv in zip(vals, self.cvs):
            if isinstance(val, (int, np.integer)):
                val = np.array(val)
            else:
                val = np.asarray(val)
            if val.shape != cv.shape:
                raise ValueError(f"Incorrect input shape for {self}: {val.shape} != {cv.shape}.")
            if np.any(val != cv):
                return False
        return True

    def wire_symbol(self, i: int, reg: Register, idx: Tuple[int, ...] = tuple()) -> 'WireSymbol':
        from qualtran.drawing import Circle, TextBox

        cvs = self.cvs[i]

        if is_symbolic(cvs):
            # control value is not given
            return TextBox('ctrl')

        # Return a circle for bits; a box otherwise.
        cv = cvs[idx]
        if reg.bitsize == 1:
            return Circle(filled=(cv == 1))
        else:
            return TextBox(f'{cv}')

    @cached_property
    def __cvs_tuple(self) -> Tuple[Union[tuple[int, ...], Shaped], ...]:
        """Serialize the control values for hashing and equality checking."""

        def _serialize(cvs) -> Union[tuple[int, ...], Shaped]:
            if isinstance(cvs, Shaped):
                return cvs
            return tuple(cvs.reshape(-1))

        return tuple(_serialize(cvs) for cvs in self.cvs)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, CtrlSpec):
            return False

        return (
            other.qdtypes == self.qdtypes
            and other.shapes == self.shapes
            and other.__cvs_tuple == self.__cvs_tuple
        )

    def __hash__(self):
        return hash((self.qdtypes, self.shapes, self.__cvs_tuple))

    def to_cirq_cv(self) -> 'cirq.SumOfProducts':
        """Convert CtrlSpec to cirq.SumOfProducts representation of control values."""
        import cirq

        if self.is_symbolic():
            raise ValueError(f"Cannot convert symbolic {self} to Cirq control values.")
        if self.num_cbits > 0:
            raise ValueError(
                f"Cannot convert classical control spec {self} to Cirq control values."
            )

        cirq_cv = []
        for dtype, cv in zip(self.qdtypes, self.cvs):
            assert isinstance(cv, np.ndarray)
            for idx in Register('', dtype, cv.shape).all_idxs():
                cirq_cv += [*dtype.to_bits(cv[idx])]
        return cirq.SumOfProducts([tuple(cirq_cv)])

    @classmethod
    def from_cirq_cv(
        cls,
        cirq_cv: 'cirq.ops.AbstractControlValues',
        *,
        qdtypes: Optional[Sequence[QCDType]] = None,
        shapes: Optional[Sequence[Tuple[int, ...]]] = None,
    ) -> 'CtrlSpec':
        """Construct a CtrlSpec from cirq.SumOfProducts representation of control values."""
        conjunctions = [*cirq_cv.expand()]
        if len(conjunctions) > 1:
            raise ValueError(
                "CtrlSpec currently only supports converting SumOfProduct representation with a single AND clause."
            )

        cv = conjunctions[0]
        # Use a single ctrl register with flat list of qubits if nothing specified.
        qdtypes = qdtypes if qdtypes is not None else [QBit()]
        shapes = shapes if shapes is not None else [(len(cv),) if len(cv) > 1 else ()]

        # Verify that the given values for qdtypes and shapes are compatible with cv.
        if sum(dt.num_qubits * np.prod(sh) for dt, sh in zip(qdtypes, shapes)) != len(cv):
            raise ValueError(f"Sum of bits across {qdtypes=} and {shapes=} should match {len(cv)=}")

        # Convert the AND clause to a CtrlSpec.
        idx = 0
        bloq_cvs = []

        for dtype, shape in zip(qdtypes, shapes):
            full_shape = shape + (dtype.num_bits,)
            curr_cvs_bits = np.array(cv[idx : idx + int(np.prod(full_shape))]).reshape(full_shape)
            curr_cvs = np.apply_along_axis(dtype.from_bits, -1, curr_cvs_bits)  # type: ignore
            bloq_cvs.append(curr_cvs)
        return CtrlSpec(tuple(qdtypes), tuple(bloq_cvs))

    def get_single_ctrl_val(self) -> ControlBit:
        """If controlled by a single qubit, return the control bit, otherwise raise"""
        if self.is_symbolic():
            raise ValueError(f"cannot get ctrl bit for symbolic {self}")
        if self.num_bits != 1:
            raise ValueError(f"expected a single qubit control, got {self.num_qubits}")

        (dtype,) = self.qdtypes
        (cv,) = self.cvs
        assert isinstance(cv, np.ndarray)
        (idx,) = Register('', dtype, cv.shape).all_idxs()
        (control_bit,) = dtype.to_bits(cv[idx])

        return int(control_bit)


class AddControlledT(Protocol):
    """The signature for the `add_controlled` callback part of `ctrl_system`.

    See `Bloq.get_ctrl_system` for details.

    Args:
        bb: A bloq builder to use for adding.
        ctrl_soqs: The soquets that represent the control lines. These must be compatible with
            the ControlSpec; specifically with the control registers implied
            by `activation_function_dtypes`.
        in_soqs: The soquets that plug in to the normal, uncontrolled bloq.

    Returns:
        ctrl_soqs: The output control soquets.
        out_soqs: The output soquets from the uncontrolled bloq.
    """

    def __call__(
        self, bb: 'BloqBuilder', ctrl_soqs: Sequence['SoquetT'], in_soqs: Dict[str, 'SoquetT']
    ) -> Tuple[Iterable['SoquetT'], Iterable['SoquetT']]: ...


def _get_nice_ctrl_reg_names(reg_names: List[str], n: int) -> Tuple[str, ...]:
    """Get `n` names for the ctrl registers that don't overlap with (existing) `reg_names`."""
    if n == 1 and 'ctrl' not in reg_names:
        # Special case for nicer register name if we just have one control register
        # and can safely name it 'ctrl'.
        return ('ctrl',)

    if 'ctrl' in reg_names:
        i = 1
    else:
        i = 0
    names: List[str] = []
    while len(names) < n:
        while True:
            i += 1
            candidate = f'ctrl{i}'
            if candidate not in reg_names:
                names.append(candidate)
                break
    return tuple(names)


class _ControlledBase(GateWithRegisters, metaclass=abc.ABCMeta):
    """Base class for representing the controlled version of an arbitrary bloq.

    This meta-bloq interface is part of the 'controlled' protocol.
    """

    @property
    @abc.abstractmethod
    def subbloq(self) -> 'Bloq':
        """The bloq being controlled."""

    @property
    @abc.abstractmethod
    def ctrl_spec(self) -> 'CtrlSpec':
        """The specification of how the `subbloq` is controlled."""

    @cached_property
    def _thru_registers_only(self) -> bool:
        for reg in self.subbloq.signature:
            if reg.side != Side.THRU:
                return False
        return True

    @staticmethod
    def _make_ctrl_system(cb: '_ControlledBase') -> Tuple['_ControlledBase', 'AddControlledT']:
        """A static method to create the adder function from an implementation of this class.

        Classes implementing this interface can use this static method to create a factory
        class method to construct both the controlled bloq and its adder function.

        See `Bloq.get_ctrl_system`.
        """
        ctrl_reg_names = cb.ctrl_reg_names

        def add_controlled(
            bb: 'BloqBuilder', ctrl_soqs: Sequence['SoquetT'], in_soqs: Dict[str, 'SoquetT']
        ) -> Tuple[Iterable['SoquetT'], Iterable['SoquetT']]:
            in_soqs |= dict(zip(ctrl_reg_names, ctrl_soqs))
            new_out_d = bb.add_d(cb, **in_soqs)

            # We need to pluck out the `ctrl_soq` from the new out_soqs
            # dictionary, so we can correspond it to `old_out_soqs`.
            ctrl_soqs = tuple(new_out_d.pop(creg_name) for creg_name in ctrl_reg_names)
            return ctrl_soqs, new_out_d.values()

        return cb, add_controlled

    @cached_property
    def ctrl_reg_names(self) -> Sequence[str]:
        """The name of the control registers.

        This is generated on-the-fly to avoid conflicts with existing register
        names. Users should not rely on the absolute value of this property staying constant.
        """
        reg_names = [reg.name for reg in self.subbloq.signature]
        n = len(self.ctrl_spec.activation_function_dtypes())
        return _get_nice_ctrl_reg_names(reg_names, n)

    @cached_property
    def ctrl_regs(self) -> Tuple[Register, ...]:
        return tuple(
            Register(name=self.ctrl_reg_names[i], dtype=qdtype, shape=shape, side=Side.THRU)
            for i, (qdtype, shape) in enumerate(self.ctrl_spec.activation_function_dtypes())
        )

    @cached_property
    def signature(self) -> 'Signature':
        # Prepend register(s) corresponding to `ctrl_spec`.
        return Signature(self.ctrl_regs + tuple(self.subbloq.signature))

    def on_classical_vals(self, **vals: 'ClassicalValT') -> Mapping[str, 'ClassicalValRetT']:
        """Classical action of controlled bloqs.

        This involves conditionally doing the classical action of `subbloq`. All implementers
        of `_ControlledBase` should provide a decomposition that satisfies this classical action.
        """
        if not self._thru_registers_only:
            raise ValueError(f"Cannot handle non-thru registers in {self}.")
        ctrl_vals = [vals[reg_name] for reg_name in self.ctrl_reg_names]
        other_vals = {reg.name: vals[reg.name] for reg in self.subbloq.signature}
        if self.ctrl_spec.is_active(*ctrl_vals):
            rets = {
                **self.subbloq.on_classical_vals(**other_vals),
                **{
                    reg_name: ctrl_val for reg_name, ctrl_val in zip(self.ctrl_reg_names, ctrl_vals)
                },
            }
            return rets

        return vals

    def basis_state_phase(self, **vals: 'ClassicalValT') -> Union[complex, None]:
        """Phasing action of controlled bloqs.

        This involves conditionally doing the phasing action of `subbloq`. All implementers
        of `_ControlledBase` should provide a decomposition that satisfies this phase funciton.
        """
        ctrl_vals = [vals[reg_name] for reg_name in self.ctrl_reg_names]
        other_vals = {reg.name: vals[reg.name] for reg in self.subbloq.signature}
        if self.ctrl_spec.is_active(*ctrl_vals):
            return self.subbloq.basis_state_phase(**other_vals)
        return None

    def _tensor_data(self):
        """Dense tensor encoding a controlled unitary.

        This is used by Bloq.my_tensors and cirq.Gate._unitary_ to support tensor simulation.
        """
        if not self._thru_registers_only:
            raise ValueError(f"Cannot handle non-thru registers in {self}.")
        from qualtran.simulation.tensor._tensor_data_manipulation import (
            active_space_for_ctrl_spec,
            eye_tensor_for_signature,
            tensor_shape_from_signature,
        )

        # Create an identity tensor corresponding to the signature of current Bloq
        data = eye_tensor_for_signature(self.signature)
        # Figure out the ctrl indexes for which the ctrl is "active"
        subbloq_shape = tensor_shape_from_signature(self.subbloq.signature)
        subbloq_tensor = self.subbloq.tensor_contract()
        if subbloq_shape:
            subbloq_tensor = subbloq_tensor.reshape(subbloq_shape)
        # Put the subbloq tensor at indices where ctrl is active.
        active_idx = active_space_for_ctrl_spec(self.signature, self.ctrl_spec)
        data[active_idx] = subbloq_tensor
        return data

    def _unitary_(self):
        """Cirq-style unitary protocol."""
        if isinstance(self.subbloq, GateWithRegisters):
            # subbloq is a cirq gate, use the cirq-style API to derive a unitary.
            import cirq

            # TODO It would be ideal to use `tensor_contract` always,
            #      but at the moment it's about 5-10x slower than `cirq.unitary`.
            #      So we default to `cirq.unitary`, and only use `tensor_contract` if it fails.
            #      https://github.com/quantumlib/Qualtran/issues/1336
            # TODO `cirq.ControlledGate` fails to correctly verify `subbloq` using
            #      a compute-uncompute `And` pair is unitary.
            #      https://github.com/quantumlib/Qualtran/issues/1488
            try:
                return cirq.unitary(
                    cirq.ControlledGate(self.subbloq, control_values=self.ctrl_spec.to_cirq_cv())
                )
            except ValueError:
                pass  # use the tensor contraction instead
        if all(reg.side == Side.THRU for reg in self.subbloq.signature):
            # subbloq has only THRU registers, so the tensor contraction corresponds
            # to a unitary matrix.
            return self.tensor_contract()
        # Unable to determine the unitary effect.
        raise ValueError(f"Cannot handle non-thru registers in {self}.")

    def my_tensors(
        self, incoming: Dict[str, 'ConnectionT'], outgoing: Dict[str, 'ConnectionT']
    ) -> List['qtn.Tensor']:
        import quimb.tensor as qtn

        from qualtran.simulation.tensor._dense import _order_incoming_outgoing_indices

        inds = _order_incoming_outgoing_indices(
            self.signature, incoming=incoming, outgoing=outgoing
        )
        data = self._tensor_data().reshape((2,) * len(inds))
        return [qtn.Tensor(data=data, inds=inds, tags=[str(self)])]

    def wire_symbol(self, reg: Optional[Register], idx: Tuple[int, ...] = tuple()) -> 'WireSymbol':
        from qualtran.drawing import Text

        if reg is None:
            return Text(f'C[{self.subbloq}]')
        if reg.name not in self.ctrl_reg_names:
            # Delegate to subbloq
            return self.subbloq.wire_symbol(reg, idx)

        # Otherwise, it's part of the control register.
        i = self.ctrl_reg_names.index(reg.name)
        return self.ctrl_spec.wire_symbol(i, reg, idx)

    def __str__(self) -> str:
        num_ctrls = self.ctrl_spec.num_bits
        ctrl_string = 'C' if num_ctrls == 1 else f'C[{num_ctrls}]'
        return f'{ctrl_string}[{self.subbloq}]'

    def as_cirq_op(
        self, qubit_manager: 'cirq.QubitManager', **cirq_quregs: 'CirqQuregT'
    ) -> Tuple[Union['cirq.Operation', None], Dict[str, 'CirqQuregT']]:
        ctrl_regs = {reg_name: cirq_quregs.pop(reg_name) for reg_name in self.ctrl_reg_names}
        ctrl_qubits = [q for reg in ctrl_regs.values() for q in reg.reshape(-1)]
        sub_op, cirq_quregs = self.subbloq.as_cirq_op(qubit_manager, **cirq_quregs)
        assert sub_op is not None
        return (
            sub_op.controlled_by(*ctrl_qubits, control_values=self.ctrl_spec.to_cirq_cv()),
            cirq_quregs | ctrl_regs,
        )

    def _circuit_diagram_info_(
        self, args: 'cirq.CircuitDiagramInfoArgs'
    ) -> 'cirq.CircuitDiagramInfo':
        import cirq

        from qualtran.cirq_interop._bloq_to_cirq import _wire_symbol_to_cirq_diagram_info

        if isinstance(self.subbloq, cirq.Gate):
            sub_info = cirq.circuit_diagram_info(self.subbloq, args, None)
            if sub_info is not None:
                cv_info = cirq.circuit_diagram_info(self.ctrl_spec.to_cirq_cv())

                return cirq.CircuitDiagramInfo(
                    wire_symbols=(*cv_info.wire_symbols, *sub_info.wire_symbols),
                    exponent=sub_info.exponent,
                )

        return _wire_symbol_to_cirq_diagram_info(self, args)


@attrs.frozen
class Controlled(_ControlledBase):
    """A controlled version of `subbloq`.

    This bloq represents a "total control" strategy of controlling `subbloq`: the decomposition
    of `Controlled(b)` uses the decomposition of `b` and controls each subbloq in that
    decomposition.

    Users should likely not use this class directly. Prefer using `bloq.controlled(ctrl_spec)`,
    which may return a natively-controlled Bloq or a more intelligent construction for
    complex control specs.

    Args:
        subbloq: The bloq we are controlling.
        ctrl_spec: The specification for how to control the bloq.
    """

    subbloq: 'Bloq'
    ctrl_spec: 'CtrlSpec'

    def __attrs_post_init__(self):
        for qdtype in self.ctrl_spec.qdtypes:
            if not isinstance(qdtype, QCDType):
                raise ValueError(f"Invalid type found in `ctrl_spec`: {qdtype}")
            if not isinstance(qdtype, QDType):
                raise ValueError(
                    f"`qualtran.Controlled` requires a purely-quantum control spec for accurate resource estimation. Found {qdtype}. Consider using TODO"
                )

    @classmethod
    def make_ctrl_system(
        cls, bloq: 'Bloq', ctrl_spec: 'CtrlSpec'
    ) -> Tuple['_ControlledBase', 'AddControlledT']:
        """A factory method for creating both the Controlled and the adder function.

        See `Bloq.get_ctrl_system`.
        """
        cb = cls(subbloq=bloq, ctrl_spec=ctrl_spec)
        return cls._make_ctrl_system(cb)

    def decompose_bloq(self) -> 'CompositeBloq':
        return Bloq.decompose_bloq(self)

    def build_composite_bloq(
        self, bb: 'BloqBuilder', **initial_soqs: 'SoquetT'
    ) -> Dict[str, 'SoquetT']:
        if not self._thru_registers_only:
            raise DecomposeTypeError(f"Cannot handle non-thru registers in {self.subbloq}")

        # Use subbloq's decomposition but wire up the additional ctrl_soqs.
        from qualtran import CompositeBloq

        if isinstance(self.subbloq, CompositeBloq):
            cbloq = self.subbloq
        else:
            cbloq = self.subbloq.decompose_bloq()

        ctrl_soqs: List['SoquetT'] = [initial_soqs[creg_name] for creg_name in self.ctrl_reg_names]

        soq_map: List[Tuple[SoquetT, SoquetT]] = []
        for binst, in_soqs, old_out_soqs in cbloq.iter_bloqsoqs():
            in_soqs = bb.map_soqs(in_soqs, soq_map)
            new_bloq, adder = binst.bloq.get_ctrl_system(self.ctrl_spec)
            adder_output = adder(bb, ctrl_soqs=ctrl_soqs, in_soqs=in_soqs)
            ctrl_soqs = list(adder_output[0])
            new_out_soqs = adder_output[1]
            soq_map.extend(zip(old_out_soqs, new_out_soqs))

        fsoqs = bb.map_soqs(cbloq.final_soqs(), soq_map)
        fsoqs |= dict(zip(self.ctrl_reg_names, ctrl_soqs))
        return fsoqs

    def build_call_graph(self, ssa: 'SympySymbolAllocator') -> 'BloqCountDictT':
        try:
            sub_cg = self.subbloq.build_call_graph(ssa=ssa)
        except DecomposeTypeError as e1:
            raise DecomposeTypeError(f"Could not build call graph for {self}: {e1}") from e1
        except DecomposeNotImplementedError as e2:
            raise DecomposeNotImplementedError(
                f"Could not build call graph for {self}: {e2}"
            ) from e2

        counts = Counter['Bloq']()
        if isinstance(sub_cg, set):
            for bloq, n in sub_cg:
                counts[bloq.controlled(self.ctrl_spec)] += n
        else:
            for bloq, n in sub_cg.items():
                counts[bloq.controlled(self.ctrl_spec)] += n
        return counts

    def adjoint(self) -> 'Bloq':
        return self.subbloq.adjoint().controlled(ctrl_spec=self.ctrl_spec)


def make_ctrl_system_with_correct_metabloq(
    bloq: 'Bloq', ctrl_spec: 'CtrlSpec'
) -> Tuple['_ControlledBase', 'AddControlledT']:
    """The default fallback for `Bloq.make_ctrl_system.

    This intelligently selects the correct implemetation of `_ControlledBase` based
    on the control spec.

     - A 1-qubit, positive control (i.e. `CtrlSpec()`) uses `Controlled`, which uses a
       "total control" decomposition.
     - Complex quantum controls (i.e. `CtrlSpec(...)` with quantum data types) uses
       `ControlledViaAnd`, which computes the activation function once and re-uses it
       for each subbloq in the decomposition of `bloq`.
    """
    from qualtran.bloqs.mcmt.controlled_via_and import ControlledViaAnd

    if ctrl_spec == CtrlSpec():
        return Controlled.make_ctrl_system(bloq, ctrl_spec=ctrl_spec)

    qdtypes = []
    cdtypes = []
    for qcdtype in ctrl_spec.qdtypes:
        if not isinstance(qcdtype, QCDType):
            raise ValueError(f"Invalid data type encountered in the control spec: {qcdtype}")
        if isinstance(qcdtype, QDType):
            qdtypes.append(qcdtype)
        if isinstance(qcdtype, CDType):
            cdtypes.append(qcdtype)

    if qdtypes and cdtypes:
        raise NotImplementedError(
            "At present, Qualtran does not support mixing quantum and classical controls within a single CtrlSpec. As an alternative, consider first getting a quantum controlled bloq and then classically controlling it."
        )
    if qdtypes:
        return ControlledViaAnd.make_ctrl_system(bloq, ctrl_spec=ctrl_spec)
    if cdtypes:
        raise NotImplementedError("Stay tuned...")

    raise ValueError(f"Invalid control spec: {ctrl_spec}")
