The `Nucleotide` type must have the ability to represent a base as well as 
its modifications. 

We represent the `Nucleotide` type as a bitstring using `unit8` type. 
Possiblities are marked by `0` and `1` and `Any` is marked by `0b00001111`.

Accordingly, the `Strand` type is represented as a slice of `Nucleotide` type. 

In `nucleotide.BaseType` is only used for interpreting. We will do all the 
computations using the `nucleotide.PatternType`. Converters are provided 
from each type to the other. 

