# QDType
`qualtran.QDType`


<table class="tfo-notebook-buttons tfo-api nocontent" align="left">
<td>
  <a target="_blank" href="https://github.com/quantumlib/Qualtran/blob/main/qualtran/_infra/data_types.py#L63-L120">
    <img src="https://www.tensorflow.org/images/GitHub-Mark-32px.png" />
    View source on GitHub
  </a>
</td>
</table>



This defines the abstract interface for quantum data types.

<!-- Placeholder for "Used in" -->




<h2 class="add-link">Attributes</h2>

`num_qubits`<a id="num_qubits"></a>
: Number of qubits required to represent a single instance of this data type.




## Methods

<h3 id="get_classical_domain"><code>get_classical_domain</code></h3>

<a target="_blank" class="external" href="https://github.com/quantumlib/Qualtran/blob/main/qualtran/_infra/data_types.py#L71-L74">View source</a>

<pre class="devsite-click-to-copy prettyprint lang-py tfo-signature-link">
<code>@abc.abstractmethod</code>
<code>get_classical_domain() -> Iterable[Any]
</code></pre>

Yields all possible classical (computational basis state) values representable by this type.


<h3 id="to_bits"><code>to_bits</code></h3>

<a target="_blank" class="external" href="https://github.com/quantumlib/Qualtran/blob/main/qualtran/_infra/data_types.py#L76-L78">View source</a>

<pre class="devsite-click-to-copy prettyprint lang-py tfo-signature-link">
<code>@abc.abstractmethod</code>
<code>to_bits(
    x
) -> List[int]
</code></pre>

Yields individual bits corresponding to binary representation of x


<h3 id="from_bits"><code>from_bits</code></h3>

<a target="_blank" class="external" href="https://github.com/quantumlib/Qualtran/blob/main/qualtran/_infra/data_types.py#L80-L82">View source</a>

<pre class="devsite-click-to-copy prettyprint lang-py tfo-signature-link">
<code>@abc.abstractmethod</code>
<code>from_bits(
    bits: Sequence[int]
)
</code></pre>

Combine individual bits to form x


<h3 id="assert_valid_classical_val"><code>assert_valid_classical_val</code></h3>

<a target="_blank" class="external" href="https://github.com/quantumlib/Qualtran/blob/main/qualtran/_infra/data_types.py#L84-L91">View source</a>

<pre class="devsite-click-to-copy prettyprint lang-py tfo-signature-link">
<code>@abc.abstractmethod</code>
<code>assert_valid_classical_val(
    val: Any, debug_str: str = &#x27;val&#x27;
)
</code></pre>

Raises an exception if `val` is not a valid classical value for this type.


Args

`val`
: A classical value that should be in the domain of this QDType.

`debug_str`
: Optional debugging information to use in exception messages.




<h3 id="is_symbolic"><code>is_symbolic</code></h3>

<a target="_blank" class="external" href="https://github.com/quantumlib/Qualtran/blob/main/qualtran/_infra/data_types.py#L93-L95">View source</a>

<pre class="devsite-click-to-copy prettyprint lang-py tfo-signature-link">
<code>@abc.abstractmethod</code>
<code>is_symbolic() -> bool
</code></pre>

Returns True if this qdtype is parameterized with symbolic objects.


<h3 id="iteration_length_or_zero"><code>iteration_length_or_zero</code></h3>

<a target="_blank" class="external" href="https://github.com/quantumlib/Qualtran/blob/main/qualtran/_infra/data_types.py#L97-L102">View source</a>

<pre class="devsite-click-to-copy prettyprint lang-py tfo-signature-link">
<code>iteration_length_or_zero() -> <a href="../qualtran/symbolics/SymbolicInt.html"><code>qualtran.symbolics.SymbolicInt</code></a>
</code></pre>

Safe version of iteration length.

Returns the iteration_length if the type has it or else zero.

<h3 id="assert_valid_classical_val_array"><code>assert_valid_classical_val_array</code></h3>

<a target="_blank" class="external" href="https://github.com/quantumlib/Qualtran/blob/main/qualtran/_infra/data_types.py#L104-L117">View source</a>

<pre class="devsite-click-to-copy prettyprint lang-py tfo-signature-link">
<code>assert_valid_classical_val_array(
    val_array: NDArray[Any], debug_str: str = &#x27;val&#x27;
)
</code></pre>

Raises an exception if `val_array` is not a valid array of classical values for this type.

Often, validation on an array can be performed faster than validating each element
individually.

Args

`val_array`
: A numpy array of classical values. Each value should be in the domain
  of this QDType.

`debug_str`
: Optional debugging information to use in exception messages.






