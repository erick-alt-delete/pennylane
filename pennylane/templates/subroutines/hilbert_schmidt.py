# Copyright 2022 Xanadu Quantum Technologies Inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
This submodule contains the templates for Hilbert Schmidt tests.
"""

import pennylane as qml
from pennylane.operation import AnyWires, Operation


class HilbertSchmidt(Operation):
    r"""HilbertSchmidt(wires)"""
    num_wires = AnyWires
    grad_method = None

    def __init__(self, *params, v_function, v_wires, u_tape, do_queue=True, id=None):

        u_wires = u_tape.wires
        self.hyperparameters["u_tape"] = u_tape

        if not callable(v_function):
            raise qml.QuantumFunctionError("The argument v_function must be a callable quantum function.")

        self.hyperparameters["v_function"] = v_function

        v_tape = qml.transforms.make_tape(v_function)(params[0], v_wires)
        self.hyperparameters["v_tape"] = v_tape
        self.hyperparameters["v_wires"] = v_tape.wires

        if len(u_wires) != len(v_wires):
            raise qml.QuantumFunctionError("U and V must have the same number of wires.")

        if not isinstance(u_tape, qml.tape.QuantumTape):
            raise qml.QuantumFunctionError("The argument u_tape must be a QuantumTape.")

        if not qml.wires.Wires(v_wires).contains_wires(v_tape.wires):
            raise qml.QuantumFunctionError("All wires in v_tape must be in v_wires.")

        # Intersection of wires
        if len(qml.wires.Wires.shared_wires([u_tape.wires, v_tape.wires])) != 0:
            raise qml.QuantumFunctionError("u_tape and v_tape must act on distinct wires.")

        wires = qml.wires.Wires(u_wires + v_wires)

        super().__init__(*params, wires=wires, do_queue=do_queue, id=id)

    @property
    def num_params(self):
        return 1

    @staticmethod
    def compute_decomposition(
            params, wires, u_tape, v_tape, v_function=None, v_wires=None
    ):  # pylint: disable=arguments-differ,unused-argument
        r"""Representation of the operator as a product of other operators (static method)."""
        n_wires = len(u_tape.wires + v_tape.wires)
        decomp_ops = []

        first_range = range(0, int(n_wires / 2))
        second_range = range(int(n_wires / 2), n_wires)

        # Hadamard first layer
        for i, wire in enumerate(wires):
            if i in first_range:
                decomp_ops.append(qml.Hadamard(wire))

        # CNOT first layer
        for i, j in zip(first_range, second_range):
            decomp_ops.append(qml.CNOT(wires=[i, j]))

        # Unitary U
        for op_u in u_tape.operations:
            # Define outside this function, it needs to be applied.
            qml.apply(op_u)
            decomp_ops.append(op_u)

        # Unitary V conjugate
        for op_v in v_tape.operations:
            decomp_ops.append(op_v.adjoint())

        # CNOT second layer
        for i, j in zip(reversed(first_range), reversed(second_range)):
            decomp_ops.append(qml.CNOT(wires=[i, j]))

        # Hadamard second layer
        for i, wire in enumerate(wires):
            if i in first_range:
                decomp_ops.append(qml.Hadamard(wire))
        return decomp_ops

    def adjoint(self):
        adjoint_op = HilbertSchmidt(
            *self.parameters,
            u_tape=self.hyperparameters["u_tape"],
            v_function=self.hyperparameters["v_function"],
            v_wires=self.hyperparameters["v_wires"],
        )
        adjoint_op.inverse = not self.inverse
        return adjoint_op


class HilbertSchmidtLocal(HilbertSchmidt):
    r"""HilbertSchmidt(wires)"""

    @staticmethod
    def compute_decomposition(
            params, wires, u_tape, v_tape, v_function=None, v_wires=None
    ):  # pylint: disable=arguments-differ,unused-argument
        r"""Representation of the operator as a product of other operators (static method)."""
        decomp_ops = []
        n_wires = len(u_tape.wires + v_tape.wires)
        first_range = range(0, int(n_wires / 2))
        second_range = range(int(n_wires / 2), n_wires)

        # Hadamard first layer
        for i, wire in enumerate(wires):
            if i in first_range:
                decomp_ops.append(qml.Hadamard(wire))

        # CNOT first layer
        for i, j in zip(first_range, second_range):
            decomp_ops.append(qml.CNOT(wires=[wires[i], wires[j]]))

        # Unitary U
        for op_u in u_tape.operations:
            qml.apply(op_u)
            decomp_ops.append(op_u)

        # Unitary V conjugate
        for op_v in v_tape.operations:
            decomp_ops.append(op_v.adjoint())

        # Only one CNOT
        decomp_ops.append(qml.CNOT(wires=[wires[0], wires[int(n_wires / 2)]]))

        # Only one Hadamard
        decomp_ops.append(qml.Hadamard(wires[0]))

        return decomp_ops

    def adjoint(self):
        adjoint_op = HilbertSchmidtLocal(
            *self.parameters,
            u_circuit=self.hyperparameters["u_tape"],
            v_circuit=self.hyperparameters["v_function"],
            v_wires=self.hyperparameters["v_wires"],
        )
        adjoint_op.inverse = not self.inverse
        return adjoint_op
