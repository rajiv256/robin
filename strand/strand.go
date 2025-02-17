package strand

import "robin/nucleotide"

type Strand struct {
	pattern []nucleotide.Nucleotide
}

func NewStrand(seq string) *Strand {
	s := new(Strand)
	for _, c := range seq {
		s.pattern = append(s.pattern, nucleotide.NewNucleotide(c))
	}
	return s
}

func Length(s *Strand) int {
	return len(s.pattern)
}
