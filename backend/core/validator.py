from datetime import datetime
from typing import List, Dict
from .models import Domain, GlobalParams, ValidationResult, GeneratedStrand, DesignResult
from .repository import OrthogonalRepository
from .thermodynamics import ThermodynamicCalculator
from .models import ValidationCheck


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


class OligonucleotideDesigner:
    """Main designer class that orchestrates the design process"""

    def __init__(self):
        self.repository = OrthogonalRepository()
        self.thermo_calc = ThermodynamicCalculator()
        self.validator = SequenceValidator(self.thermo_calc)

    def design_strand(self, strand_name: str, domains: List[Dict],
                      global_params: Dict, validation_settings: Dict = None) -> DesignResult:
        """Design a complete oligonucleotide strand"""
        start_time = datetime.now()

        try:
            # Parse inputs
            params = GlobalParams(**global_params)
            domain_objects = []

            for domain_data in domains:
                domain = Domain(
                    name=domain_data['name'],
                    length=domain_data['length'],
                    fixed_sequence=domain_data.get('fixed_sequence'),
                    target_gc_content=domain_data.get('target_gc_content', 50.0)
                )
                domain_objects.append(domain)

            # Generate sequences for each domain
            all_sequences = []
            for domain in domain_objects:
                if domain.fixed_sequence:
                    domain.generated_sequence = domain.fixed_sequence.upper()
                else:
                    domain.generated_sequence = self.repository.get_orthogonal_sequence(
                        domain.length, domain.target_gc_content, all_sequences
                    )
                all_sequences.append(domain.generated_sequence)

            # Concatenate final sequence
            final_sequence = ''.join(d.generated_sequence for d in domain_objects)

            # Validate strand with frontend settings
            validation_results = self._validate_strand(
                final_sequence, all_sequences, params, validation_settings or {}
            )

            # Check individual domain validation
            for domain in domain_objects:
                domain_checks = self._validate_domain(domain.generated_sequence, params, validation_settings or {})
                domain.validation_passed = all(check.pass_check for check in domain_checks.values())

            # Create result
            strand = GeneratedStrand(
                name=strand_name,
                total_length=len(final_sequence),
                sequence=final_sequence,
                domains=domain_objects
            )

            end_time = datetime.now()
            generation_time = (end_time - start_time).total_seconds()

            return DesignResult(
                success=True,
                strand=strand,
                validation=validation_results,
                generation_time=generation_time,
                generated_at=end_time.isoformat()
            )

        except Exception as e:
            end_time = datetime.now()
            generation_time = (end_time - start_time).total_seconds()

            return DesignResult(
                success=False,
                generation_time=generation_time,
                generated_at=end_time.isoformat(),
                error_message=str(e)
            )

    def _validate_strand(self, sequence: str, all_sequences: List[str],
                         params: GlobalParams, validation_settings: Dict) -> ValidationResult:
        """Validate the complete strand using frontend settings"""
        checks = {}

        # Melting temperature (uses frontend settings)
        if validation_settings.get('melting_temp', {}).get('enabled', True):
            melting_settings = validation_settings.get('melting_temp', {})
            checks['melting_temperature'] = self.validator.validate_melting_temperature(
                sequence, params,
                min_offset=melting_settings.get('min_offset', 5.0),
                max_offset=melting_settings.get('max_offset', 25.0)
            )

        # Hairpin formation (uses frontend settings)
        if validation_settings.get('hairpin', {}).get('enabled', True):
            hairpin_settings = validation_settings.get('hairpin', {})
            checks['hairpin_formation'] = self.validator.validate_hairpin_formation(
                sequence, params,
                max_dg=hairpin_settings.get('max_dg', -3.0)
            )

        # Self-dimerization (uses frontend settings)
        if validation_settings.get('self_dimer', {}).get('enabled', True):
            self_dimer_settings = validation_settings.get('self_dimer', {})
            checks['self_dimerization'] = self.validator.validate_self_dimerization(
                sequence, params,
                max_dg=self_dimer_settings.get('max_dg', -6.0)
            )

        # Cross-dimerization (uses frontend settings)
        if validation_settings.get('cross_dimer', {}).get('enabled', True):
            cross_dimer_settings = validation_settings.get('cross_dimer', {})
            other_sequences = [seq for seq in all_sequences if seq != sequence]
            checks['cross_dimerization'] = self.validator.validate_cross_dimerization(
                sequence, other_sequences, params,
                max_dg=cross_dimer_settings.get('max_dg', -6.0)
            )

        # GC content (uses frontend settings)
        if validation_settings.get('gc_content', {}).get('enabled', True):
            gc_settings = validation_settings.get('gc_content', {})
            checks['gc_content'] = self.validator.validate_gc_content(
                sequence,
                min_gc=gc_settings.get('min_percent', 40.0),
                max_gc=gc_settings.get('max_percent', 60.0)
            )

        # Overall pass/fail
        overall_pass = all(check.pass_check for check in checks.values())

        return ValidationResult(
            overall_pass=overall_pass,
            checks=checks
        )

    def _validate_domain(self, sequence: str, params: GlobalParams, validation_settings: Dict) -> Dict:
        """Validate individual domain using frontend settings"""
        domain_checks = {}

        # GC content check
        if validation_settings.get('gc_content', {}).get('enabled', True):
            gc_settings = validation_settings.get('gc_content', {})
            domain_checks['gc_content'] = self.validator.validate_gc_content(
                sequence,
                min_gc=gc_settings.get('min_percent', 40.0),
                max_gc=gc_settings.get('max_percent', 60.0)
            )

        # Hairpin check
        if validation_settings.get('hairpin', {}).get('enabled', True):
            hairpin_settings = validation_settings.get('hairpin', {})
            domain_checks['hairpin'] = self.validator.validate_hairpin_formation(
                sequence, params,
                max_dg=hairpin_settings.get('max_dg', -3.0)
            )

        return domain_checks