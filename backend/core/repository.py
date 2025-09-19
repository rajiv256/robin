import random
from typing import List


class OrthogonalRepository:
    """Simple repository of orthogonal sequences"""

    def __init__(self):
        # Sample orthogonal sequences by length
        self.sequences_by_length = {
            10: [
                "ATCGATCGAT", "GCTAGCTAGT", "TACGTACGTA", "CGATCGATCG",
                "AGTCAGTCAG", "TCGATCGATC", "GTACGTACGT", "CATGCATGCA"
            ],
            15: [
                "ATCGATCGATCGATC", "GCTAGCTAGCTAGCT", "TACGTACGTACGTAC",
                "CGATCGATCGATCGA", "AGTCAGTCAGTCAGT", "TCGATCGATCGATCG"
            ],
            20: [
                "ATCGATCGATCGATCGATCG", "GCTAGCTAGCTAGCTAGCTA",
                "TACGTACGTACGTACGTACG", "CGATCGATCGATCGATCGAT",
                "AGTCAGTCAGTCAGTCAGTC", "TCGATCGATCGATCGATCGA"
            ],
            25: [
                "ATCGATCGATCGATCGATCGATCG", "GCTAGCTAGCTAGCTAGCTAGCTA",
                "TACGTACGTACGTACGTACGTACG", "CGATCGATCGATCGATCGATCGAT"
            ]
        }

    def get_orthogonal_sequence(self, length: int, gc_target: float = 50.0,
                                exclude_sequences: List[str] = None) -> str:
        """Get an orthogonal sequence of specified length"""
        exclude_sequences = exclude_sequences or []

        # Find sequences of exact length
        candidates = self.sequences_by_length.get(length, [])

        # Filter by exclusions and GC content
        suitable_candidates = []
        for seq in candidates:
            if seq not in exclude_sequences:
                gc_content = self._calculate_gc_content(seq)
                if abs(gc_content - gc_target) <= 15:  # Within 15% tolerance
                    suitable_candidates.append(seq)

        if suitable_candidates:
            return random.choice(suitable_candidates)
        else:
            # Generate new sequence if no suitable candidates
            return self._generate_sequence(length, gc_target)

    def _generate_sequence(self, length: int, gc_target: float) -> str:
        """Generate a new sequence with target GC content"""
        gc_bases = ['G', 'C']
        at_bases = ['A', 'T']
        gc_count = round((gc_target / 100) * length)
        at_count = length - gc_count

        bases = (['G'] * (gc_count // 2) + ['C'] * (gc_count - gc_count // 2) +
                 ['A'] * (at_count // 2) + ['T'] * (at_count - at_count // 2))

        # Ensure exact length
        while len(bases) < length:
            bases.append(random.choice(['A', 'T']))
        bases = bases[:length]

        random.shuffle(bases)
        return ''.join(bases)

    def _calculate_gc_content(self, sequence: str) -> float:
        """Calculate GC content percentage"""
        gc_count = sequence.count('G') + sequence.count('C')
        return (gc_count / len(sequence)) * 100 if sequence else 0.0