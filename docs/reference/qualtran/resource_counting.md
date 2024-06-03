# Module: resource_counting


Counting resource usage (bloqs, qubits)



isort:skip_file
## Modules

[`generalizers`](../qualtran/resource_counting/generalizers.md): Bloq counting generalizers.

[`symbolic_counting_utils`](../qualtran/resource_counting/symbolic_counting_utils.md) module

[`t_counts_from_sigma`](../qualtran/resource_counting/t_counts_from_sigma.md) module

## Classes

[`class SympySymbolAllocator`](../qualtran/resource_counting/SympySymbolAllocator.md): A class that allocates unique sympy symbols for integrating out bloq attributes.

## Functions

[`big_O(...)`](../qualtran/resource_counting/big_O.md): Helper to deal with CS-style big-O notation that takes the infinite limit by default.

[`build_cbloq_call_graph(...)`](../qualtran/resource_counting/build_cbloq_call_graph.md): Count all the subbloqs in a composite bloq.

[`get_bloq_call_graph(...)`](../qualtran/resource_counting/get_bloq_call_graph.md): Recursively build the bloq call graph and call totals.

[`get_bloq_callee_counts(...)`](../qualtran/resource_counting/get_bloq_callee_counts.md): Get the direct callees of a bloq and the number of times they are called.

[`print_counts_graph(...)`](../qualtran/resource_counting/print_counts_graph.md): Print the graph returned from `get_bloq_counts_graph`.

## Type Aliases

[`BloqCountT`](../qualtran/resource_counting/BloqCountT.md)

[`GeneralizerT`](../qualtran/resource_counting/GeneralizerT.md)
