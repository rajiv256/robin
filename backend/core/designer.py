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
                      global_params: Dict) -> DesignResult:
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

            # Validate strand
            validation_results = self._validate_strand(final_sequence, all_sequences, params)

            # Check individual domain validation
            for domain in domain_objects:
                domain_checks = self._validate_domain(domain.generated_sequence, params)
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
                         params: GlobalParams) -> ValidationResult:
        """Validate the complete strand"""
        checks = {}

        # Melting temperature (uses reaction_temp from frontend)
        checks['melting_temperature'] = self.validator.validate_melting_temperature(
            sequence, params
        )

        # Hairpin formation (uses reaction_temp from frontend)
        checks['hairpin_formation'] = self.validator.validate_hairpin_formation(
            sequence, params
        )

        # Self-dimerization (uses reaction_temp from frontend)
        checks['self_dimerization'] = self.validator.validate_self_dimerization(
            sequence, params
        )

        # Cross-dimerization (uses reaction_temp from frontend)
        other_sequences = [seq for seq in all_sequences if seq != sequence]
        checks['cross_dimerization'] = self.validator.validate_cross_dimerization(
            sequence, other_sequences, params
        )

        # GC content (temperature independent)
        checks['gc_content'] = self.validator.validate_gc_content(sequence)

        # Overall pass/fail
        overall_pass = all(check.pass_check for check in checks.values())

        return ValidationResult(
            overall_pass=overall_pass,
            checks=checks
        )

    def _validate_domain(self, sequence: str, params: GlobalParams) -> Dict:
        """Validate individual domain"""
        return {
            'gc_content': self.validator.validate_gc_content(sequence),
            'hairpin': self.validator.validate_hairpin_formation(sequence, params)
        }