# QpicCircuit
`qualtran.drawing.qpic_diagram.QpicCircuit`


<table class="tfo-notebook-buttons tfo-api nocontent" align="left">
<td>
  <a target="_blank" href="https://github.com/quantumlib/Qualtran/blob/main/qualtran/drawing/qpic_diagram.py#L135-L270">
    <img src="https://www.tensorflow.org/images/GitHub-Mark-32px.png" />
    View source on GitHub
  </a>
</td>
</table>



Builds data corresponding to the input specification of a QPIC diagram

<pre class="devsite-click-to-copy prettyprint lang-py tfo-signature-link">
<code>qualtran.drawing.qpic_diagram.QpicCircuit()
</code></pre>



<!-- Placeholder for "Used in" -->




<h2 class="add-link">Attributes</h2>

`data`<a id="data"></a>
: &nbsp;




## Methods

<h3 id="add_left_wires_for_signature"><code>add_left_wires_for_signature</code></h3>

<a target="_blank" class="external" href="https://github.com/quantumlib/Qualtran/blob/main/qualtran/drawing/qpic_diagram.py#L150-L156">View source</a>

<pre class="devsite-click-to-copy prettyprint lang-py tfo-signature-link">
<code>add_left_wires_for_signature(
    signature: 'Signature'
) -> None
</code></pre>




<h3 id="add_right_wires_for_signature"><code>add_right_wires_for_signature</code></h3>

<a target="_blank" class="external" href="https://github.com/quantumlib/Qualtran/blob/main/qualtran/drawing/qpic_diagram.py#L158-L169">View source</a>

<pre class="devsite-click-to-copy prettyprint lang-py tfo-signature-link">
<code>add_right_wires_for_signature(
    signature: 'Signature'
) -> None
</code></pre>




<h3 id="add_connection"><code>add_connection</code></h3>

<a target="_blank" class="external" href="https://github.com/quantumlib/Qualtran/blob/main/qualtran/drawing/qpic_diagram.py#L230-L233">View source</a>

<pre class="devsite-click-to-copy prettyprint lang-py tfo-signature-link">
<code>add_connection(
    cxn: 'Connection'
)
</code></pre>




<h3 id="add_bloq"><code>add_bloq</code></h3>

<a target="_blank" class="external" href="https://github.com/quantumlib/Qualtran/blob/main/qualtran/drawing/qpic_diagram.py#L244-L270">View source</a>

<pre class="devsite-click-to-copy prettyprint lang-py tfo-signature-link">
<code>add_bloq(
    bloq: 'Bloq', pred: List['Connection'], succ: List['Connection']
) -> None
</code></pre>






