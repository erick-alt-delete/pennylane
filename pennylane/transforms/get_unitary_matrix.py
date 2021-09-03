# Copyright 2018-2021 Xanadu Quantum Technologies Inc.

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
A transform to obtain the matrix representation of a circuit.
"""
from functools import wraps
import numpy as np
from pennylane.wires import Wires
import pennylane as qml


def get_unitary_matrix(fn, wire_order):
    """Given a QNode, tape, or quantum function along with a list of the wire order, construct the matrix representation"""
    n_wires = len(wire_order)
    wire_order = Wires(wire_order)

    @wraps(fn)
    def wrapper(*args, **kwargs):

        if isinstance(fn, qml.QNode):
            # user passed a QNode, get the tape
            fn.construct(args, kwargs)
            tape = fn.qtape

        elif isinstance(fn, qml.tape.QuantumTape):
            # user passed a tape
            tape = fn

        elif callable(fn):
            # user passed something that is callable but not a tape or qnode.
            # we'll assume it is a qfunc!
            tape = qml.transforms.make_tape(fn)(*args, **kwargs)

        # else:
        # raise some exception

        # initialize the unitary matrix
        unitary_matrix = np.eye(2 ** n_wires)

        for op in tape.operations:

            # operator wire position relative to wire ordering
            op_wire_pos = wire_order.indices(op.wires)

            I = np.reshape(np.eye(2 ** n_wires), [2] * n_wires * 2)
            axes = (np.arange(len(op.wires), 2 * len(op.wires)), op_wire_pos)
            # reshape op.matrix
            U_op_reshaped = np.reshape(op.matrix, [2] * len(op.wires) * 2)
            U_tensordot = np.tensordot(U_op_reshaped, I, axes=axes)

            unused_idxs = [idx for idx in range(n_wires) if idx not in op_wire_pos]
            # permute matrix axes to match wire ordering
            perm = op_wire_pos + unused_idxs
            U = np.moveaxis(U_tensordot, wire_order.indices(wire_order), perm)

            U = np.reshape(U, ((2 ** n_wires, 2 ** n_wires)))

            # add to total matrix if there are multiple ops
            unitary_matrix = np.dot(U, unitary_matrix)
        return unitary_matrix

    return wrapper