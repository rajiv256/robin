from datetime import datetime
from typing import List, Dict
from .models import Domain, GlobalParams, ValidationResult, GeneratedStrand, DesignResult
from .repository import OrthogonalRepository
from .thermodynamics import ThermodynamicCalculator
from .validator import SequenceValidator


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