import math
from .models import GlobalParams


class ThermodynamicCalculator:
    """Simplified thermodynamic calculations for oligonucleotides"""

    def __init__(self):
        # Simplified nearest neighbor parameters (kcal/mol, cal/mol·K)
        self.nn_params = {
            'AA': {'dH': -7.9, 'dS': -22.2}, 'AT': {'dH': -7.2, 'dS': -20.4},
            'AG': {'dH': -7.8, 'dS': -21.0}, 'AC': {'dH': -8.4, 'dS': -22.4},
            'TA': {'dH': -7.2, 'dS': -21.3}, 'TT': {'dH': -7.9, 'dS': -22.2},
            'TG': {'dH': -8.5, 'dS': -22.7}, 'TC': {'dH': -8.2, 'dS': -22.2},
            'GA': {'dH': -8.2, 'dS': -22.2}, 'GT': {'dH': -8.4, 'dS': -22.4},
            'GG': {'dH': -8.0, 'dS': -19.9}, 'GC': {'dH': -9.8, 'dS': -24.4},
            'CA': {'dH': -8.5, 'dS': -22.7}, 'CT': {'dH': -7.8, 'dS': -21.0},
            'CG': {'dH': -10.6, 'dS': -27.2}, 'CC': {'dH': -8.0, 'dS': -19.9}
        }
        self.R = 1.987  # cal/mol·K

    def calculate_melting_temp(self, sequence: str, params: GlobalParams) -> float:
        """Calculate melting temperature using nearest neighbor method"""
        if len(sequence) < 2:
            return 0.0

        dH = 0.0  # Enthalpy
        dS = 0.0  # Entropy

        # Sum nearest neighbor contributions
        for i in range(len(sequence) - 1):
            dinuc = sequence[i:i + 2]
            if dinuc in self.nn_params:
                dH += self.nn_params[dinuc]['dH']
                dS += self.nn_params[dinuc]['dS']

        # Terminal corrections (simplified)
        if sequence[0] in 'AT':
            dH += 2.3
            dS += 4.1
        if sequence[-1] in 'AT':
            dH += 2.3
            dS += 4.1

        # Salt correction
        dS += 0.368 * len(sequence) * math.log(params.salt_conc / 1000.0)

        # Calculate Tm
        if dS != 0:
            tm = (dH * 1000) / (dS + self.R * math.log(params.oligo_conc / 4e9)) - 273.15
            return max(0, tm)
        return 0.0

    def calculate_hairpin_dg(self, sequence: str, temp: float = 37.0) -> float:
        """Simplified hairpin formation energy calculation"""
        min_stem = 3
        min_loop = 3
        best_dg = 0.0

        for i in range(len(sequence) - min_stem - min_loop):
            for j in range(i + min_stem + min_loop, len(sequence)):
                stem_length = min(j - i - min_loop, len(sequence) - j)
                if stem_length >= min_stem:
                    matches = 0
                    for k in range(stem_length):
                        if self._are_complementary(sequence[i + k], sequence[j + stem_length - 1 - k]):
                            matches += 1

                    if matches >= min_stem:
                        # Temperature-dependent dG calculation
                        dg_37 = -1.5 * matches + 4.0  # Base calculation at 37°C
                        # Simple temperature correction (more negative at lower temps)
                        temp_correction = (temp - 37.0) * 0.02
                        dg = dg_37 + temp_correction
                        if dg < best_dg:
                            best_dg = dg

        return best_dg

    def calculate_dimer_dg(self, seq1: str, seq2: str, temp: float = 37.0) -> float:
        """Simplified dimerization energy calculation"""
        best_dg = 0.0

        for offset in range(-len(seq2), len(seq1)):
            matches = 0
            overlap = 0

            for i in range(len(seq1)):
                j = i - offset
                if 0 <= j < len(seq2):
                    overlap += 1
                    if self._are_complementary(seq1[i], seq2[j]):
                        matches += 1

            if overlap >= 3 and matches >= 3:
                # Temperature-dependent dG calculation
                dg_37 = -1.2 * matches + 2.0  # Base calculation at 37°C
                # Simple temperature correction
                temp_correction = (temp - 37.0) * 0.015
                dg = dg_37 + temp_correction
                if dg < best_dg:
                    best_dg = dg

        return best_dg

    def calculate_gc_content(self, sequence: str) -> float:
        """Calculate GC content percentage"""
        gc_count = sequence.count('G') + sequence.count('C')
        return (gc_count / len(sequence)) * 100 if sequence else 0.0

    def _are_complementary(self, base1: str, base2: str) -> bool:
        """Check if two bases are complementary"""
        complements = {'A': 'T', 'T': 'A', 'G': 'C', 'C': 'G'}
        return complements.get(base1) == base2