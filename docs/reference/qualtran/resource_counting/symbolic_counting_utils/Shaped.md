# Shaped
`qualtran.resource_counting.symbolic_counting_utils.Shaped`


<table class="tfo-notebook-buttons tfo-api nocontent" align="left">
<td>
  <a target="_blank" href="https://github.com/quantumlib/Qualtran/blob/main/qualtran/resource_counting/symbolic_counting_utils.py#L31-L47">
    <img src="https://www.tensorflow.org/images/GitHub-Mark-32px.png" />
    View source on GitHub
  </a>
</td>
</table>



Symbolic value for an object that has a shape.

<pre class="devsite-click-to-copy prettyprint lang-py tfo-signature-link">
<code>qualtran.resource_counting.symbolic_counting_utils.Shaped(
    shape
)
</code></pre>



<!-- Placeholder for "Used in" -->

A Shaped object can be used as a symbolic replacement for any object that has an attribute `shape`,
for example numpy NDArrays.
Each dimension can be either an positive integer value or a sympy expression.

This is useful to do symbolic analysis of Bloqs whose call graph only depends on the shape of the input,
but not on the actual values.
For example, T-cost of the `QROM` Bloq depends only on the iteration length (shape) and not on actual data values.



<h2 class="add-link">Attributes</h2>

`shape`<a id="shape"></a>
: &nbsp;




## Methods

<h3 id="is_symbolic"><code>is_symbolic</code></h3>

<a target="_blank" class="external" href="https://github.com/quantumlib/Qualtran/blob/main/qualtran/resource_counting/symbolic_counting_utils.py#L46-L47">View source</a>

<pre class="devsite-click-to-copy prettyprint lang-py tfo-signature-link">
<code>is_symbolic()
</code></pre>




<h3 id="__eq__"><code>__eq__</code></h3>

<pre class="devsite-click-to-copy prettyprint lang-py tfo-signature-link">
<code>__eq__(
    other
)
</code></pre>

Method generated by attrs for class Shaped.


<h3 id="__ne__"><code>__ne__</code></h3>

<pre class="devsite-click-to-copy prettyprint lang-py tfo-signature-link">
<code>__ne__(
    other
)
</code></pre>

Method generated by attrs for class Shaped.



