# IntermediateDataBlock
`qualtran.surface_code.IntermediateDataBlock`


<table class="tfo-notebook-buttons tfo-api nocontent" align="left">
<td>
  <a target="_blank" href="https://github.com/quantumlib/Qualtran/blob/main/qualtran/surface_code/data_block.py#L122-L145">
    <img src="https://www.tensorflow.org/images/GitHub-Mark-32px.png" />
    View source on GitHub
  </a>
</td>
</table>



The intermediate data block uses a fixed code distance and routing overhead.

Inherits From: [`SimpleDataBlock`](../../qualtran/surface_code/SimpleDataBlock.md), [`DataBlock`](../../qualtran/surface_code/data_block/DataBlock.md)

<section class="expandable">
  <h4 class="showalways">View aliases</h4>
  <p>
<b>Main aliases</b>
<p>`qualtran.surface_code.data_block.IntermediateDataBlock`</p>
</p>
</section>

<pre class="devsite-click-to-copy prettyprint lang-py tfo-signature-link">
<code>qualtran.surface_code.IntermediateDataBlock(
    data_d,
    qec_scheme=<a href="../../qualtran/surface_code.html#FowlerSuperconductingQubits"><code>qualtran.surface_code.FowlerSuperconductingQubits</code></a>
)
</code></pre>



<!-- Placeholder for "Used in" -->

The intermediate data block lays $n$ qubit batches in grid of shape (2, $2n+2$) where
the data batches are lined in the first row with the second row being an ancilla region.

<h2 class="add-link">References</h2>






<h2 class="add-link">Attributes</h2>

`data_d`<a id="data_d"></a>
: The code distance `d` for protecting the qubits in the data block.

`qec_scheme`<a id="qec_scheme"></a>
: Underlying quantum error correction scheme.

`reference`<a id="reference"></a>
: A description of the source of the model.

`routing_overhead`<a id="routing_overhead"></a>
: &nbsp;




## Methods

<h3 id="n_cycles_to_consume_a_magic_state"><code>n_cycles_to_consume_a_magic_state</code></h3>

<a target="_blank" class="external" href="https://github.com/quantumlib/Qualtran/blob/main/qualtran/surface_code/data_block.py#L144-L145">View source</a>

<pre class="devsite-click-to-copy prettyprint lang-py tfo-signature-link">
<code>n_cycles_to_consume_a_magic_state() -> int
</code></pre>

The worst case number of cycles needed to consume a magic state.


<h3 id="__eq__"><code>__eq__</code></h3>

<pre class="devsite-click-to-copy prettyprint lang-py tfo-signature-link">
<code>__eq__(
    other
)
</code></pre>

Method generated by attrs for class IntermediateDataBlock.


<h3 id="__ne__"><code>__ne__</code></h3>

<pre class="devsite-click-to-copy prettyprint lang-py tfo-signature-link">
<code>__ne__(
    other
)
</code></pre>

Method generated by attrs for class IntermediateDataBlock.



