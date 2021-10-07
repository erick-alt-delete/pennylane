:orphan:

# Release 0.9.0

<h3>New features since last release</h3>

<h4>New machine learning integrations</h4>

* PennyLane QNodes can now be converted into Keras layers, allowing for creation of quantum and
  hybrid models using the Keras API.
  [(#529)](https://github.com/XanaduAI/pennylane/pull/529)

  A PennyLane QNode can be converted into a Keras layer using the `KerasLayer` class:

  ```python
  from pennylane.qnn import KerasLayer

  @qml.qnode(dev)
  def circuit(inputs, weights_0, weight_1):
     # define the circuit
     # ...

  weight_shapes = {"weights_0": 3, "weight_1": 1}
  qlayer = qml.qnn.KerasLayer(circuit, weight_shapes, output_dim=2)
  ```

  A hybrid model can then be easily constructed:

  ```python
  model = tf.keras.models.Sequential([qlayer, tf.keras.layers.Dense(2)])
  ```

* Added a new type of QNode, `qml.qnodes.PassthruQNode`. For simulators which are coded in an
  external library which supports automatic differentiation, PennyLane will treat a PassthruQNode as
  a "white box", and rely on the external library to directly provide gradients via backpropagation.
  This can be more efficient than the using parameter-shift rule for a large number of parameters.
  [(#488)](https://github.com/XanaduAI/pennylane/pull/488)

  Currently this behaviour is supported by PennyLane's `default.tensor.tf` device backend,
  compatible with the `'tf'` interface using TensorFlow 2:

  ```python
  dev = qml.device('default.tensor.tf', wires=2)

  @qml.qnode(dev, diff_method="backprop")
  def circuit(params):
      qml.RX(params[0], wires=0)
      qml.RX(params[1], wires=1)
      qml.CNOT(wires=[0, 1])
      return qml.expval(qml.PauliZ(0))

  qnode = PassthruQNode(circuit, dev)
  params = tf.Variable([0.3, 0.1])

  with tf.GradientTape() as tape:
      tape.watch(params)
      res = qnode(params)

  grad = tape.gradient(res, params)
  ```

<h4>New optimizers</h4>

* Added the `qml.RotosolveOptimizer`, a gradient-free optimizer
  that minimizes the quantum function by updating each parameter,
  one-by-one, via a closed-form expression while keeping other parameters
  fixed.
  [(#636)](https://github.com/XanaduAI/pennylane/pull/636)
  [(#539)](https://github.com/XanaduAI/pennylane/pull/539)

* Added the `qml.RotoselectOptimizer`, which uses Rotosolve to
  minimizes a quantum function with respect to both the
  rotation operations applied and the rotation parameters.
  [(#636)](https://github.com/XanaduAI/pennylane/pull/636)
  [(#539)](https://github.com/XanaduAI/pennylane/pull/539)

  For example, given a quantum function `f` that accepts parameters `x`
  and a list of corresponding rotation operations `generators`,
  the Rotoselect optimizer will, at each step, update both the parameter
  values and the list of rotation gates to minimize the loss:

  ```pycon
  >>> opt = qml.optimize.RotoselectOptimizer()
  >>> x = [0.3, 0.7]
  >>> generators = [qml.RX, qml.RY]
  >>> for _ in range(100):
  ...     x, generators = opt.step(f, x, generators)
  ```


<h4>New operations</h4>

* Added the `PauliRot` gate, which performs an arbitrary
  Pauli rotation on multiple qubits, and the `MultiRZ` gate,
  which performs a rotation generated by a tensor product
  of Pauli Z operators.
  [(#559)](https://github.com/XanaduAI/pennylane/pull/559)

  ```python
  dev = qml.device('default.qubit', wires=4)

  @qml.qnode(dev)
  def circuit(angle):
      qml.PauliRot(angle, "IXYZ", wires=[0, 1, 2, 3])
      return [qml.expval(qml.PauliZ(wire)) for wire in [0, 1, 2, 3]]
  ```

  ```pycon
  >>> circuit(0.4)
  [1.         0.92106099 0.92106099 1.        ]
  >>> print(circuit.draw())
   0: ──╭RI(0.4)──┤ ⟨Z⟩
   1: ──├RX(0.4)──┤ ⟨Z⟩
   2: ──├RY(0.4)──┤ ⟨Z⟩
   3: ──╰RZ(0.4)──┤ ⟨Z⟩
  ```

  If the `PauliRot` gate is not supported on the target device, it will
  be decomposed into `Hadamard`, `RX` and `MultiRZ` gates. Note that
  identity gates in the Pauli word result in untouched wires:

  ```pycon
  >>> print(circuit.draw())
   0: ───────────────────────────────────┤ ⟨Z⟩
   1: ──H──────────╭RZ(0.4)──H───────────┤ ⟨Z⟩
   2: ──RX(1.571)──├RZ(0.4)──RX(-1.571)──┤ ⟨Z⟩
   3: ─────────────╰RZ(0.4)──────────────┤ ⟨Z⟩
  ```

  If the `MultiRZ` gate is not supported, it will be decomposed into
  `CNOT` and `RZ` gates:

  ```pycon
  >>> print(circuit.draw())
   0: ──────────────────────────────────────────────────┤ ⟨Z⟩
   1: ──H──────────────╭X──RZ(0.4)──╭X──────H───────────┤ ⟨Z⟩
   2: ──RX(1.571)──╭X──╰C───────────╰C──╭X──RX(-1.571)──┤ ⟨Z⟩
   3: ─────────────╰C───────────────────╰C──────────────┤ ⟨Z⟩
  ```

* PennyLane now provides `DiagonalQubitUnitary` for diagonal gates, that are e.g.,
  encountered in IQP circuits. These kinds of gates can be evaluated much faster on
  a simulator device.
  [(#567)](https://github.com/XanaduAI/pennylane/pull/567)

  The gate can be used, for example, to efficiently simulate oracles:

  ```python
  dev = qml.device('default.qubit', wires=3)

  # Function as a bitstring
  f = np.array([1, 0, 0, 1, 1, 0, 1, 0])

  @qml.qnode(dev)
  def circuit(weights1, weights2):
      qml.templates.StronglyEntanglingLayers(weights1, wires=[0, 1, 2])

      # Implements the function as a phase-kickback oracle
      qml.DiagonalQubitUnitary((-1)**f, wires=[0, 1, 2])

      qml.templates.StronglyEntanglingLayers(weights2, wires=[0, 1, 2])
      return [qml.expval(qml.PauliZ(w)) for w in range(3)]
  ```

* Added the `TensorN` CVObservable that can represent the tensor product of the
  `NumberOperator` on photonic backends.
  [(#608)](https://github.com/XanaduAI/pennylane/pull/608)

<h4>New templates</h4>

* Added the `ArbitraryUnitary` and `ArbitraryStatePreparation` templates, which use
  `PauliRot` gates to perform an arbitrary unitary and prepare an arbitrary basis
  state with the minimal number of parameters.
  [(#590)](https://github.com/XanaduAI/pennylane/pull/590)

  ```python
  dev = qml.device('default.qubit', wires=3)

  @qml.qnode(dev)
  def circuit(weights1, weights2):
        qml.templates.ArbitraryStatePreparation(weights1, wires=[0, 1, 2])
        qml.templates.ArbitraryUnitary(weights2, wires=[0, 1, 2])
        return qml.probs(wires=[0, 1, 2])
  ```

* Added the `IQPEmbedding` template, which encodes inputs into the diagonal gates of an
  IQP circuit.
  [(#605)](https://github.com/XanaduAI/pennylane/pull/605)

  <img src="https://pennylane.readthedocs.io/en/latest/_images/iqp.png"
  width=50%></img>

* Added the `SimplifiedTwoDesign` template, which implements the circuit
  design of [Cerezo et al. (2020)](<https://arxiv.org/abs/2001.00550>).
  [(#556)](https://github.com/XanaduAI/pennylane/pull/556)

  <img src="https://pennylane.readthedocs.io/en/latest/_images/simplified_two_design.png"
  width=50%></img>

* Added the `BasicEntanglerLayers` template, which is a simple layer architecture
  of rotations and CNOT nearest-neighbour entanglers.
  [(#555)](https://github.com/XanaduAI/pennylane/pull/555)

  <img src="https://pennylane.readthedocs.io/en/latest/_images/basic_entangler.png"
  width=50%></img>

* PennyLane now offers a broadcasting function to easily construct templates:
  `qml.broadcast()` takes single quantum operations or other templates and applies
  them to wires in a specific pattern.
  [(#515)](https://github.com/XanaduAI/pennylane/pull/515)
  [(#522)](https://github.com/XanaduAI/pennylane/pull/522)
  [(#526)](https://github.com/XanaduAI/pennylane/pull/526)
  [(#603)](https://github.com/XanaduAI/pennylane/pull/603)

  For example, we can use broadcast to repeat a custom template
  across multiple wires:

  ```python
  from pennylane.templates import template

  @template
  def mytemplate(pars, wires):
      qml.Hadamard(wires=wires)
      qml.RY(pars, wires=wires)

  dev = qml.device('default.qubit', wires=3)

  @qml.qnode(dev)
  def circuit(pars):
      qml.broadcast(mytemplate, pattern="single", wires=[0,1,2], parameters=pars)
      return qml.expval(qml.PauliZ(0))
  ```

  ```pycon
  >>> circuit([1, 1, 0.1])
  -0.841470984807896
  >>> print(circuit.draw())
   0: ──H──RY(1.0)──┤ ⟨Z⟩
   1: ──H──RY(1.0)──┤
   2: ──H──RY(0.1)──┤
  ```

  For other available patterns, see the
  [broadcast function documentation](https://pennylane.readthedocs.io/en/latest/code/api/pennylane.broadcast.html).

<h3>Breaking changes</h3>

* The `QAOAEmbedding` now uses the new `MultiRZ` gate as a `ZZ` entangler,
  which changes the convention. While
  previously, the `ZZ` gate in the embedding was implemented as

  ```python
  CNOT(wires=[wires[0], wires[1]])
  RZ(2 * parameter, wires=wires[0])
  CNOT(wires=[wires[0], wires[1]])
  ```

  the `MultiRZ` corresponds to

  ```python
  CNOT(wires=[wires[1], wires[0]])
  RZ(parameter, wires=wires[0])
  CNOT(wires=[wires[1], wires[0]])
  ```

  which differs in the factor of `2`, and fixes a bug in the
  wires that the `CNOT` was applied to.
  [(#609)](https://github.com/XanaduAI/pennylane/pull/609)

* Probability methods are handled by `QubitDevice` and device method
  requirements are modified to simplify plugin development.
  [(#573)](https://github.com/XanaduAI/pennylane/pull/573)

* The internal variables `All` and `Any` to mark an `Operation` as acting on all or any
  wires have been renamed to `AllWires` and `AnyWires`.
  [(#614)](https://github.com/XanaduAI/pennylane/pull/614)

<h3>Improvements</h3>

* A new `Wires` class was introduced for the internal
  bookkeeping of wire indices.
  [(#615)](https://github.com/XanaduAI/pennylane/pull/615)

* Improvements to the speed/performance of the `default.qubit` device.
  [(#567)](https://github.com/XanaduAI/pennylane/pull/567)
  [(#559)](https://github.com/XanaduAI/pennylane/pull/559)

* Added the `"backprop"` and `"device"` differentiation methods to the `qnode`
  decorator.
  [(#552)](https://github.com/XanaduAI/pennylane/pull/552)

  - `"backprop"`: Use classical backpropagation. Default on simulator
    devices that are classically end-to-end differentiable.
    The returned QNode can only be used with the same machine learning
    framework (e.g., `default.tensor.tf` simulator with the `tensorflow` interface).

  - `"device"`: Queries the device directly for the gradient.

  Using the `"backprop"` differentiation method with the `default.tensor.tf`
  device, the created QNode is a 'white-box', and is tightly integrated with
  the overall TensorFlow computation:

  ```python
  >>> dev = qml.device("default.tensor.tf", wires=1)
  >>> @qml.qnode(dev, interface="tf", diff_method="backprop")
  >>> def circuit(x):
  ...     qml.RX(x[1], wires=0)
  ...     qml.Rot(x[0], x[1], x[2], wires=0)
  ...     return qml.expval(qml.PauliZ(0))
  >>> vars = tf.Variable([0.2, 0.5, 0.1])
  >>> with tf.GradientTape() as tape:
  ...     res = circuit(vars)
  >>> tape.gradient(res, vars)
  <tf.Tensor: shape=(3,), dtype=float32, numpy=array([-2.2526717e-01, -1.0086454e+00,  1.3877788e-17], dtype=float32)>
  ```

* The circuit drawer now displays inverted operations, as well as wires
  where probabilities are returned from the device:
  [(#540)](https://github.com/XanaduAI/pennylane/pull/540)

  ```python
  >>> @qml.qnode(dev)
  ... def circuit(theta):
  ...     qml.RX(theta, wires=0)
  ...     qml.CNOT(wires=[0, 1])
  ...     qml.S(wires=1).inv()
  ...     return qml.probs(wires=[0, 1])
  >>> circuit(0.2)
  array([0.99003329, 0.        , 0.        , 0.00996671])
  >>> print(circuit.draw())
  0: ──RX(0.2)──╭C───────╭┤ Probs
  1: ───────────╰X──S⁻¹──╰┤ Probs
  ```

* You can now evaluate the metric tensor of a VQE Hamiltonian via the new
  `VQECost.metric_tensor` method. This allows `VQECost` objects to be directly
  optimized by the quantum natural gradient optimizer (`qml.QNGOptimizer`).
  [(#618)](https://github.com/XanaduAI/pennylane/pull/618)

* The input check functions in `pennylane.templates.utils` are now public
  and visible in the API documentation.
  [(#566)](https://github.com/XanaduAI/pennylane/pull/566)

* Added keyword arguments for step size and order to the `qnode` decorator, as well as
  the `QNode` and `JacobianQNode` classes. This enables the user to set the step size
  and order when using finite difference methods. These options are also exposed when
  creating QNode collections.
  [(#530)](https://github.com/XanaduAI/pennylane/pull/530)
  [(#585)](https://github.com/XanaduAI/pennylane/pull/585)
  [(#587)](https://github.com/XanaduAI/pennylane/pull/587)

* The decomposition for the `CRY` gate now uses the simpler form `RY @ CNOT @ RY @ CNOT`
  [(#547)](https://github.com/XanaduAI/pennylane/pull/547)

* The underlying queuing system was refactored, removing the `qml._current_context`
  property that held the currently active `QNode` or `OperationRecorder`. Now, all
  objects that expose a queue for operations inherit from `QueuingContext` and
  register their queue globally.
  [(#548)](https://github.com/XanaduAI/pennylane/pull/548)

* The PennyLane repository has a new benchmarking tool which supports the comparison of different git revisions.
  [(#568)](https://github.com/XanaduAI/pennylane/pull/568)
  [(#560)](https://github.com/XanaduAI/pennylane/pull/560)
  [(#516)](https://github.com/XanaduAI/pennylane/pull/516)

<h3>Documentation</h3>

* Updated the development section by creating a landing page with links to sub-pages
  containing specific guides.
  [(#596)](https://github.com/XanaduAI/pennylane/pull/596)

* Extended the developer's guide by a section explaining how to add new templates.
  [(#564)](https://github.com/XanaduAI/pennylane/pull/564)

<h3>Bug fixes</h3>

* `tf.GradientTape().jacobian()` can now be evaluated on QNodes using the TensorFlow interface.
  [(#626)](https://github.com/XanaduAI/pennylane/pull/626)

* `RandomLayers()` is now compatible with the qiskit devices.
  [(#597)](https://github.com/XanaduAI/pennylane/pull/597)

* `DefaultQubit.probability()` now returns the correct probability when called with
  `device.analytic=False`.
  [(#563)](https://github.com/XanaduAI/pennylane/pull/563)

* Fixed a bug in the `StronglyEntanglingLayers` template, allowing it to
  work correctly when applied to a single wire.
  [(544)](https://github.com/XanaduAI/pennylane/pull/544)

* Fixed a bug when inverting operations with decompositions; operations marked as inverted
  are now correctly inverted when the fallback decomposition is called.
  [(#543)](https://github.com/XanaduAI/pennylane/pull/543)

* The `QNode.print_applied()` method now correctly displays wires where
  `qml.prob()` is being returned.
  [#542](https://github.com/XanaduAI/pennylane/pull/542)

<h3>Contributors</h3>

This release contains contributions from (in alphabetical order):

Ville Bergholm, Lana Bozanic, Thomas Bromley, Theodor Isacsson, Josh Izaac, Nathan Killoran,
Maggie Li, Johannes Jakob Meyer, Maria Schuld, Sukin Sim, Antal Száva.