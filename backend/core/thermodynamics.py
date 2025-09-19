import math
import primer3
from .models import GlobalParams


class ThermodynamicCalculator:
    """Thermodynamic calculations using primer3 with temperature corrections"""

    def __init__(self):
        self.R = 1.987  # cal/mol·K

    def calculate_melting_temp(self, sequence: str, params: GlobalParams) -> float:
        """Calculate melting temperature using primer3"""
        if len(sequence) < 2:
            return 0.0

        tm = primer3.calc_tm(
            sequence,
            mv_conc=params.salt_conc,
            dv_conc=params.mg_conc,
            dntp_conc=0.0,  # Assuming no dNTPs in hybridization
            dna_conc=params.oligo_conc
        )
        return round(tm, 2)

    def calculate_hairpin_dg(self, sequence: str, temp: float = 37.0) -> float:
        """Calculate hairpin formation energy using primer3 with temperature correction"""
        # Calculate at 37°C using primer3
        result_37 = primer3.calc_hairpin(
            sequence,
            mv_conc=50.0,  # Default conditions
            dv_conc=0.0,
            dntp_conc=0.0,
            temp_c=37.0
        )
        dg_37 = result_37.dg / 1000.0  # Convert cal/mol to kcal/mol

        # Apply temperature correction if not 37°C
        if temp != 37.0:
            # Temperature dependence: ΔG = ΔH - T*ΔS
            # Approximate correction based on typical ΔH and ΔS values
            # For hairpins: ΔH ≈ -30 kcal/mol, ΔS ≈ -80 cal/mol·K (typical values)
            temp_k_37 = 310.15  # 37°C in Kelvin
            temp_k = temp + 273.15

            # Approximate temperature correction
            # ΔG(T) = ΔG(37°C) + ΔS * (T - 37°C)
            # Using estimated entropy change for hairpin formation
            estimated_ds = -0.08  # kcal/mol·K (typical for hairpin)
            temp_correction = estimated_ds * (temp_k - temp_k_37)
            dg_corrected = dg_37 + temp_correction
            return round(dg_corrected, 2)

        return round(dg_37, 2)

    def calculate_dimer_dg(self, seq1: str, seq2: str, temp: float = 37.0) -> float:
        """Calculate dimerization energy using primer3 with temperature correction"""
        # Use homodimer if sequences are the same, heterodimer otherwise
        if seq1 == seq2:
            result_37 = primer3.calc_homodimer(
                seq1,
                mv_conc=50.0,
                dv_conc=0.0,
                dntp_conc=0.0,
                temp_c=37.0
            )
        else:
            result_37 = primer3.calc_heterodimer(
                seq1, seq2,
                mv_conc=50.0,
                dv_conc=0.0,
                dntp_conc=0.0,
                temp_c=37.0
            )

        dg_37 = result_37.dg / 1000.0  # Convert cal/mol to kcal/mol

        # Apply temperature correction if not 37°C
        if temp != 37.0:
            # Temperature dependence for dimer formation
            # Using estimated entropy change for dimer formation
            temp_k_37 = 310.15  # 37°C in Kelvin
            temp_k = temp + 273.15

            # Estimated entropy change for dimer formation
            estimated_ds = -0.06  # kcal/mol·K (typical for dimer)
            temp_correction = estimated_ds * (temp_k - temp_k_37)
            dg_corrected = dg_37 + temp_correction
            return round(dg_corrected, 2)

        return round(dg_37, 2)

    def calculate_gc_content(self, sequence: str) -> float:
        """Calculate GC content percentage"""
        gc_count = sequence.count('G') + sequence.count('C')
        return (gc_count / len(sequence)) * 100 if sequence else 0.0

    def _are_complementary(self, base1: str, base2: str) -> bool:
        """Check if two bases are complementary"""
        complements = {'A': 'T', 'T': 'A', 'G': 'C', 'C': 'G'}
        return complements.get(base1) == base2