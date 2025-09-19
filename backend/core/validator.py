from typing import List
from .models import ValidationCheck, GlobalParams
from .thermodynamics import ThermodynamicCalculator


class SequenceValidator:
    """Validates sequences against various criteria"""

    def __init__(self, thermo_calc: ThermodynamicCalculator):
        self.thermo_calc = thermo_calc

    def validate_melting_temperature(self, sequence: str, params: GlobalParams,
                                     min_offset: float = 5.0, max_offset: float = 25.0) -> ValidationCheck:
        """Validate melting temperature is within acceptable range"""
        tm = self.thermo_calc.calculate_melting_temp(sequence, params)
        target_min = params.reaction_temp + min_offset
        target_max = params.reaction_temp + max_offset

        pass_check = target_min <= tm <= target_max
        message = f"Tm = {tm:.1f}°C (target: {target_min:.1f}-{target_max:.1f}°C)"

        return ValidationCheck(
            pass_check=pass_check,
            value=tm,
            target_range=[target_min, target_max],
            message=message
        )

    def validate_hairpin_formation(self, sequence: str, max_dg: float = -3.0) -> ValidationCheck:
        """Validate hairpin formation energy"""
        dg = self.thermo_calc.calculate_hairpin_dg(sequence)
        pass_check = dg >= max_dg

        if dg >= -1.0:
            message = "No significant hairpin structures detected"
        elif pass_check:
            message = "Hairpin formation within acceptable limits"
        else:
            message = f"Strong hairpin formation detected (ΔG = {dg:.1f} kcal/mol)"

        return ValidationCheck(
            pass_check=pass_check,
            delta_g=dg,
            threshold=max_dg,
            message=message
        )

    def validate_self_dimerization(self, sequence: str, max_dg: float = -6.0) -> ValidationCheck:
        """Validate self-dimerization energy"""
        dg = self.thermo_calc.calculate_dimer_dg(sequence, sequence)
        pass_check = dg >= max_dg

        if dg >= -3.0:
            message = "Low self-dimerization risk"
        elif pass_check:
            message = "Self-dimerization within acceptable limits"
        else:
            message = f"High self-dimerization risk (ΔG = {dg:.1f} kcal/mol)"

        return ValidationCheck(
            pass_check=pass_check,
            delta_g=dg,
            threshold=max_dg,
            message=message
        )

    def validate_cross_dimerization(self, sequence: str, other_sequences: List[str],
                                    max_dg: float = -6.0) -> ValidationCheck:
        """Validate cross-dimerization with other sequences"""
        worst_dg = 0.0

        for other_seq in other_sequences:
            if other_seq != sequence:
                dg = self.thermo_calc.calculate_dimer_dg(sequence, other_seq)
                if dg < worst_dg:
                    worst_dg = dg

        pass_check = worst_dg >= max_dg

        if worst_dg >= -3.0:
            message = "Compatible with other sequences"
        elif pass_check:
            message = "Cross-dimerization within acceptable limits"
        else:
            message = f"Cross-dimerization risk detected (ΔG = {worst_dg:.1f} kcal/mol)"

        return ValidationCheck(
            pass_check=pass_check,
            delta_g=worst_dg,
            threshold=max_dg,
            message=message
        )

    def validate_gc_content(self, sequence: str, min_gc: float = 40.0,
                            max_gc: float = 60.0) -> ValidationCheck:
        """Validate GC content is within acceptable range"""
        gc_content = self.thermo_calc.calculate_gc_content(sequence)
        pass_check = min_gc <= gc_content <= max_gc

        if pass_check:
            message = "Optimal GC content"
        elif gc_content < min_gc:
            message = f"GC content too low ({gc_content:.1f}%)"
        else:
            message = f"GC content too high ({gc_content:.1f}%)"

        return ValidationCheck(
            pass_check=pass_check,
            value=gc_content,
            target_range=[min_gc, max_gc],
            message=message
        )