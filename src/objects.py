from typing import List

from vars.gvars import ALPHABET, HYBRIDIZE, PUNCT
from utils import dna_utils


class Nucleotide:
    def __init__(self, symbol, type=None):
        self.symbol = symbol
        self.type = type

    def _complement(self):
        return Nucleotide(HYBRIDIZE[self.symbol])


class Domain:
    def __init__(self, name: str, seq: str):
        assert dna_utils.is_valid(seq)
        self.name = name
        self.seq = seq
        self.length = self.__len__()

    def base_percent(self, base) -> float:
        assert len(base) == 1
        assert base in ALPHABET
        return self.seq.count(base) / len(self.seq)

    def __len__(self):
        return len(self.seq)

    def __str__(self):
        return f"""{self.name} ({len(self.seq)})"""

    def is_palindrome(self):
        return dna_utils.is_palindrome(self.seq)

    def gc_content(self):
        return self.base_percent('G') + self.base_percent('C')

    def reverse_complement(self):
        revcompseq = PUNCT['EMPTYSTRING'].join([HYBRIDIZE[c] for c in self.seq])[::-1]
        return Domain(name=self.name+'*', seq=revcompseq)


class Strand:
    def __init__(self, name: str, domains: List[Domain]):
        self.name = name
        self.domains = domains  # 5'-3' end

    def __len__(self):
        return sum([len(d) for d in self.domains])

    def __str__(self):
        s = f"""ø"""
        for d in self.domains:
            s += f"""-{d}-"""
        s += f"""->"""
        return s

    def reverse_complement(self):
        name = self.name + '*'
        # reverse the domains.
        domains = reversed(self.domains)
        # create reverse complement of individual domains.
        domains = [d.reverse_complement() for d in domains]
        return  Strand(name=name, domains=domains)


if __name__ == "__main__":
    d1 = Domain('d1', seq='ATC')
    d2 = Domain('d2', seq='GCAT')
    s = Strand(name='s', domains=[d1, d2])
    sc = s.reverse_complement()
    print(d1, d2, s, sc)