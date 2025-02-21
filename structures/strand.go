package structures

type Strand struct {
	domains []Domain
}

func NewStrand(domains []Domain) *Strand {
	return &Strand{domains: domains}
}
