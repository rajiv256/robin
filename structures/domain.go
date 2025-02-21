package structures

// Domain Represents a domain of a DNA strand
type Domain struct {
	sequence []Nucleotide
}

func NewDomain(sequence []Nucleotide) *Domain {
	return &Domain{sequence: sequence}
}
