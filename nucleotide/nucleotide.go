package nucleotide

type BaseType uint8

const (
	A = 1 << iota
	C
	G
	T
	R = A | G         // Purine (A or G)
	Y = C | T         // Pyrimidine (C or T)
	K = G | T         // Keto (G or T)
	M = A | C         // Amino (A or C)
	S = C | G         // Strong (C or G)
	W = A | T         // Weak (A or T)
	B = C | G | T     // Not A (C or G or T)
	D = A | G | T     // Not C (A or G or T)
	H = A | C | T     // Not G (A or C or T)
	V = A | C | G     // Not T (A or C or G)
	N = A | C | G | T // Any base (A or C or G or T)
)

type Nucleotide struct {
	base BaseType
}

// NewNucleotide Creates a new Nucleotide from a rune
func NewNucleotide(c rune) Nucleotide {
	// The rune could include all the symbols.
	// We need to check if the rune is a valid nucleotide
	// and return the corresponding Nucleotide.
	switch c {
	case 'A':
		return Nucleotide{A}
	case 'C':
		return Nucleotide{C}
	case 'G':
		return Nucleotide{G}
	case 'T':
		return Nucleotide{T}
	case 'R':
		return Nucleotide{R}
	case 'Y':
		return Nucleotide{Y}
	case 'K':
		return Nucleotide{K}
	case 'M':
		return Nucleotide{M}
	case 'S':
		return Nucleotide{S}
	case 'W':
		return Nucleotide{W}
	case 'B':
		return Nucleotide{B}
	case 'D':
		return Nucleotide{D}
	case 'H':
		return Nucleotide{H}
	case 'V':
		return Nucleotide{V}
	default:
		return Nucleotide{N}
	}
}

// Is checks if the Nucleotide is of a certain type
func (n Nucleotide) Is(b BaseType) bool {
	return n.base&b != 0
}

// Complement returns the complement of the Nucleotide
func (n Nucleotide) Complement() Nucleotide {
	switch n.base {
	case A:
		return Nucleotide{T}
	case C:
		return Nucleotide{G}
	case G:
		return Nucleotide{C}
	case T:
		return Nucleotide{A}
	case R:
		return Nucleotide{Y}
	case Y:
		return Nucleotide{R}
	case K:
		return Nucleotide{M}
	case M:
		return Nucleotide{K}
	case S:
		return Nucleotide{S}
	case W:
		return Nucleotide{W}
	case B:
		return Nucleotide{V}
	case D:
		return Nucleotide{H}
	case H:
		return Nucleotide{D}
	case V:
		return Nucleotide{B}
	default:
		return Nucleotide{N}
	}
}

// String returns the string representation of the Nucleotide
func (n Nucleotide) String() string {
	switch n.base {
	case A:
		return "A"
	case C:
		return "C"
	case G:
		return "G"
	case T:
		return "T"
	case R:
		return "A/G"
	case Y:
		return "C/T"
	case K:
		return "G/T"
	case M:
		return "A/C"
	case S:
		return "C/G"
	case W:
		return "A/T"
	case B:
		return "C/G/T"
	case D:
		return "A/G/T"
	case H:
		return "A/C/T"
	case V:
		return "A/C/G"
	default:
		return "A/C/G/T"
	}
}

// Equal checks if two Nucleotides are equal
func (n Nucleotide) Equal(n2 Nucleotide) bool {
	return n.base == n2.base
}
