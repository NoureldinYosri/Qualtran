# FastDataBlock
`qualtran.surface_code.FastDataBlock`


<table class="tfo-notebook-buttons tfo-api nocontent" align="left">
<td>
  <a target="_blank" href="https://github.com/quantumlib/Qualtran/blob/main/qualtran/surface_code/data_block.py#L148-L203">
    <img src="https://www.tensorflow.org/images/GitHub-Mark-32px.png" />
    View source on GitHub
  </a>
</td>
</table>



The fast data block uses a fixed code distance and a square layout.

Inherits From: [`DataBlock`](../../qualtran/surface_code/data_block/DataBlock.md)

<section class="expandable">
  <h4 class="showalways">View aliases</h4>
  <p>
<b>Main aliases</b>
<p>`qualtran.surface_code.data_block.FastDataBlock`</p>
</p>
</section>

<pre class="devsite-click-to-copy prettyprint lang-py tfo-signature-link">
<code>qualtran.surface_code.FastDataBlock(
    data_d,
    qec_scheme=<a href="../../qualtran/surface_code.html#FowlerSuperconductingQubits"><code>qualtran.surface_code.FowlerSuperconductingQubits</code></a>
)
</code></pre>



<!-- Placeholder for "Used in" -->

The fast data block lays $n$ qubit batches in a square grid of side length $1 + \sqrt{2n}$
where the bottom row is an ancilla region and the top $\sqrt{2n}x\sqrt{2n}$ region is divided
into alternating data and ancilla columns.
The increased footprint is to be able to consume magic states in a single timestep.

<h2 class="add-link">References</h2>






<h2 class="add-link">Attributes</h2>

`data_d`<a id="data_d"></a>
: The code distance `d` for protecting the qubits in the data block.

`qec_scheme`<a id="qec_scheme"></a>
: Underlying quantum error correction scheme.

`reference`<a id="reference"></a>
: A description of the source of the model.




## Methods

<h3 id="grid_size"><code>grid_size</code></h3>

<a target="_blank" class="external" href="https://github.com/quantumlib/Qualtran/blob/main/qualtran/surface_code/data_block.py#L173-L175">View source</a>

<pre class="devsite-click-to-copy prettyprint lang-py tfo-signature-link">
<code>@staticmethod</code>
<code>grid_size(
    n_algo_qubits: int
) -> int
</code></pre>




<h3 id="footprint"><code>footprint</code></h3>

<a target="_blank" class="external" href="https://github.com/quantumlib/Qualtran/blob/main/qualtran/surface_code/data_block.py#L177-L178">View source</a>

<pre class="devsite-click-to-copy prettyprint lang-py tfo-signature-link">
<code>footprint(
    n_algo_qubits: int
) -> int
</code></pre>

The number of physical qubits used by the data block.


Attributes

`n_algo_qubits`
: The number of algorithm qubits whose data must be stored and
  accessed.




<h3 id="data_error"><code>data_error</code></h3>

<a target="_blank" class="external" href="https://github.com/quantumlib/Qualtran/blob/main/qualtran/surface_code/data_block.py#L180-L186">View source</a>

<pre class="devsite-click-to-copy prettyprint lang-py tfo-signature-link">
<code>data_error(
    n_algo_qubits: int, n_cycles: int, phys_err: float
) -> float
</code></pre>

The error associated with storing data on `n_algo_qubits` for `n_cycles`.


<h3 id="n_logical_qubits"><code>n_logical_qubits</code></h3>

<a target="_blank" class="external" href="https://github.com/quantumlib/Qualtran/blob/main/qualtran/surface_code/data_block.py#L188-L189">View source</a>

<pre class="devsite-click-to-copy prettyprint lang-py tfo-signature-link">
<code>n_logical_qubits(
    n_algo_qubits: int
) -> int
</code></pre>




<h3 id="n_cycles_to_consume_a_magic_state"><code>n_cycles_to_consume_a_magic_state</code></h3>

<a target="_blank" class="external" href="https://github.com/quantumlib/Qualtran/blob/main/qualtran/surface_code/data_block.py#L191-L192">View source</a>

<pre class="devsite-click-to-copy prettyprint lang-py tfo-signature-link">
<code>n_cycles_to_consume_a_magic_state() -> int
</code></pre>

The worst case number of cycles needed to consume a magic state.


<h3 id="from_error_budget"><code>from_error_budget</code></h3>

<a target="_blank" class="external" href="https://github.com/quantumlib/Qualtran/blob/main/qualtran/surface_code/data_block.py#L194-L203">View source</a>

<pre class="devsite-click-to-copy prettyprint lang-py tfo-signature-link">
<code>@staticmethod</code>
<code>from_error_budget(
    error_budget: float,
    n_algo_qubits: int,
    qec_scheme: <a href="../../qualtran/surface_code/QuantumErrorCorrectionSchemeSummary.html"><code>qualtran.surface_code.QuantumErrorCorrectionSchemeSummary</code></a>,
    physical_error_rate: float
) -> 'FastDataBlock'
</code></pre>




<h3 id="__eq__"><code>__eq__</code></h3>

<pre class="devsite-click-to-copy prettyprint lang-py tfo-signature-link">
<code>__eq__(
    other
)
</code></pre>

Method generated by attrs for class FastDataBlock.


<h3 id="__ne__"><code>__ne__</code></h3>

<pre class="devsite-click-to-copy prettyprint lang-py tfo-signature-link">
<code>__ne__(
    other
)
</code></pre>

Method generated by attrs for class FastDataBlock.



