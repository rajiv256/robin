# oligonucleotide_designer.py
import numpy as np
import random
import json
import math
import itertools
import re
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Domain:
    """Domain specification for oligonucleotide design"""
    name: str
    length: int
    fixed_sequence: Optional[str] = None
    target_gc_content: float = 50.0
    generated_sequence: Optional[str] = None
    validation_passed: bool = False


@dataclass
class GlobalParams:
    """Global reaction parameters"""
    reaction_temp: float = 37.0  # °C
    salt_conc: float = 50.0  # mM
    mg_conc: float = 2.0  # mM
    oligo_conc: float = 250.0  # nM


@dataclass
class ValidationCheck:
    """Individual validation check result"""
    pass_check: bool
    value: Optional[float] = None
    delta_g: Optional[float] = None
    threshold: Optional[float] = None
    target_range: Optional[List[float]] = None
    message: str = ""


@dataclass
class ValidationResult:
    """Complete validation result for a strand"""
    overall_pass: bool
    checks: Dict[str, ValidationCheck]


@dataclass
class GeneratedStrand:
    """Final generated strand with all information"""
    name: str
    total_length: int
    sequence: str
    domains: List[Domain]


@dataclass
class DesignResult:
    """Complete design result"""
    success: bool
    strand: Optional[GeneratedStrand] = None
    validation: Optional[ValidationResult] = None
    generation_time: float = 0.0
    generated_at: str = ""
    error_message: str = ""


class OrthogonalRepository:
    """Repository of pre-validated orthogonal sequences"""

    def __init__(self):
        # Initialize with some example orthogonal sequences
        # In practice, this would be loaded from a database or file
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
        """Get an orthogonal sequence of specified length and GC content"""
        exclude_sequences = exclude_sequences or []

        # Find sequences of exact length or generate new ones
        candidates = self.sequences_by_length.get(length, [])

        # Filter by GC content and exclusions
        suitable_candidates = []
        for seq in candidates:
            if seq not in exclude_sequences:
                gc_content = self._calculate_gc_content(seq)
                if abs(gc_content - gc_target) <= 10:  # Within 10% tolerance
                    suitable_candidates.append(seq)

        if suitable_candidates:
            return random.choice(suitable_candidates)
        else:
            # Generate new sequence if no suitable candidates
            return self._generate_sequence(length, gc_target, exclude_sequences)

    def _generate_sequence(self, length: int, gc_target: float,
                           exclude_sequences: List[str]) -> str:
        """Generate a new sequence with target GC content"""
        max_attempts = 1000
        for _ in range(max_attempts):
            sequence = self._create_random_sequence(length, gc_target)
            if sequence not in exclude_sequences:
                return sequence

        # Fallback: return best attempt
        return self._create_random_sequence(length, gc_target)

    def _create_random_sequence(self, length: int, gc_target: float) -> str:
        """Create a random sequence with target GC content"""
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


class ThermodynamicCalculator:
    """Handles all thermodynamic calculations"""

    def __init__(self):
        # Nearest neighbor parameters (SantaLucia 1998)
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

        # Terminal corrections
        self.terminal_at = {'dH': 2.3, 'dS': 4.1}
        self.terminal_gc = {'dH': 0.1, 'dS': -2.8}

        # Salt correction parameters
        self.salt_correction = 0.368

        # Gas constant
        self.R = 1.987  # cal/mol·K

    def calculate_melting_temp(self, sequence: str, params: GlobalParams) -> float:
        """Calculate melting temperature using nearest neighbor method"""
        if len(sequence) < 2:
            return 0.0

        dH = 0.0  # Enthalpy (kcal/mol)
        dS = 0.0  # Entropy (cal/mol·K)

        # Add nearest neighbor contributions
        for i in range(len(sequence) - 1):
            dinuc = sequence[i:i + 2]
            if dinuc in self.nn_params:
                dH += self.nn_params[dinuc]['dH']
                dS += self.nn_params[dinuc]['dS']

        # Terminal corrections
        if sequence[0] in 'AT':
            dH += self.terminal_at['dH']
            dS += self.terminal_at['dS']
        else:
            dH += self.terminal_gc['dH']
            dS += self.terminal_gc['dS']

        if sequence[-1] in 'AT':
            dH += self.terminal_at['dH']
            dS += self.terminal_at['dS']
        else:
            dH += self.terminal_gc['dH']
            dS += self.terminal_gc['dS']

        # Salt correction
        dS += self.salt_correction * len(sequence) * math.log(params.salt_conc / 1000.0)

        # Calculate Tm
        if dS != 0:
            tm = (dH * 1000) / (dS + self.R * math.log(params.oligo_conc / 4e9)) - 273.15
            return max(0, tm)
        return 0.0

    def calculate_hairpin_dg(self, sequence: str, temp: float = 37.0) -> float:
        """Calculate hairpin formation free energy"""
        min_stem = 3
        min_loop = 3
        best_dg = 0.0

        for i in range(len(sequence) - min_stem - min_loop):
            for loop_size in range(min_loop, len(sequence) - i - min_stem + 1):
                j = i + min_stem + loop_size
                if j + min_stem > len(sequence):
                    break

                # Check stem complementarity
                stem_length = min(min_stem, (len(sequence) - j))
                matches = 0

                for k in range(stem_length):
                    if i + k < len(sequence) and j + stem_length - 1 - k < len(sequence):
                        if self._are_complementary(sequence[i + k], sequence[j + stem_length - 1 - k]):
                            matches += 1

                if matches >= min_stem:
                    # Simplified hairpin dG calculation
                    dg_stem = -1.5 * matches  # Approximate stem stability
                    dg_loop = 3.0 + 0.5 * loop_size  # Loop penalty
                    dg_total = dg_stem + dg_loop

                    if dg_total < best_dg:
                        best_dg = dg_total

        return best_dg

    def calculate_dimer_dg(self, seq1: str, seq2: str, temp: float = 37.0) -> float:
        """Calculate dimerization free energy between two sequences"""
        best_dg = 0.0
        min_overlap = 3

        # Check all possible alignments
        for offset in range(-len(seq2) + min_overlap, len(seq1) - min_overlap + 1):
            matches = 0
            overlap = 0

            for i in range(len(seq1)):
                j = i - offset
                if 0 <= j < len(seq2):
                    overlap += 1
                    if self._are_complementary(seq1[i], seq2[j]):
                        matches += 1

            if overlap >= min_overlap and matches >= min_overlap:
                # Simplified dimer dG calculation
                dg = -1.2 * matches + 0.5 * overlap + 2.0
                if dg < best_dg:
                    best_dg = dg

        return best_dg

    def calculate_3prime_stability(self, sequence: str, length: int = 5) -> float:
        """Calculate 3' end stability"""
        if len(sequence) < length:
            length = len(sequence)

        end_seq = sequence[-length:]
        gc_count = end_seq.count('G') + end_seq.count('C')
        gc_content = (gc_count / length) * 100

        # Higher GC at 3' end = more stable = more negative dG
        stability_dg = -0.05 * gc_content - 1.0
        return stability_dg

    def _are_complementary(self, base1: str, base2: str) -> bool:
        """Check if two bases are complementary"""
        complements = {'A': 'T', 'T': 'A', 'G': 'C', 'C': 'G'}
        return complements.get(base1) == base2


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

    def validate_hairpin_formation(self, sequence: str, max_dg: float = -3.0,
                                   temp: float = 37.0) -> ValidationCheck:
        """Validate hairpin formation energy"""
        dg = self.thermo_calc.calculate_hairpin_dg(sequence, temp)
        pass_check = dg >= max_dg

        if dg >= -1.0:
            message = "No significant hairpin structures detected"
        elif pass_check:
            message = f"Hairpin formation within acceptable limits"
        else:
            message = f"Strong hairpin formation detected (ΔG = {dg:.1f} kcal/mol)"

        return ValidationCheck(
            pass_check=pass_check,
            delta_g=dg,
            threshold=max_dg,
            message=message
        )

    def validate_self_dimerization(self, sequence: str, max_dg: float = -6.0,
                                   temp: float = 37.0) -> ValidationCheck:
        """Validate self-dimerization energy"""
        dg = self.thermo_calc.calculate_dimer_dg(sequence, sequence, temp)
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
                                    max_dg: float = -6.0, temp: float = 37.0) -> ValidationCheck:
        """Validate cross-dimerization with other sequences"""
        worst_dg = 0.0

        for other_seq in other_sequences:
            if other_seq != sequence:
                dg = self.thermo_calc.calculate_dimer_dg(sequence, other_seq, temp)
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
        gc_count = sequence.count('G') + sequence.count('C')
        gc_content = (gc_count / len(sequence)) * 100 if sequence else 0.0

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

    def validate_primer_3_end(self, sequence: str, max_dg: float = -3.0) -> ValidationCheck:
        """Validate 3' end stability"""
        dg = self.thermo_calc.calculate_3prime_stability(sequence)
        pass_check = dg >= max_dg

        if pass_check:
            message = "Appropriate 3' end stability"
        else:
            message = f"3' end too stable (ΔG = {dg:.1f} kcal/mol)"

        return ValidationCheck(
            pass_check=pass_check,
            delta_g=dg,
            threshold=max_dg,
            message=message
        )

    def validate_repeats(self, sequence: str, max_repeat: int = 4) -> ValidationCheck:
        """Validate sequence doesn't contain excessive repeats"""
        # Check for homopolymer runs
        for base in 'ATGC':
            pattern = base * (max_repeat + 1)
            if pattern in sequence:
                return ValidationCheck(
                    pass_check=False,
                    message=f"Homopolymer run of {base} detected (>{max_repeat})"
                )

        # Check for dinucleotide repeats
        for i in range(len(sequence) - 1):
            dinuc = sequence[i:i + 2]
            count = 1
            j = i + 2
            while j + 1 < len(sequence) and sequence[j:j + 2] == dinuc:
                count += 1
                j += 2
                if count > max_repeat // 2:
                    return ValidationCheck(
                        pass_check=False,
                        message=f"Dinucleotide repeat {dinuc} detected"
                    )

        return ValidationCheck(
            pass_check=True,
            message="No excessive repeats detected"
        )


class OligonucleotideDesigner:
    """Main designer class that orchestrates the design process"""

    def __init__(self):
        self.repository = OrthogonalRepository()
        self.thermo_calc = ThermodynamicCalculator()
        self.validator = SequenceValidator(self.thermo_calc)

    def design_strand(self, strand_name: str, domains: List[Dict],
                      global_params: Dict, validation_config: Dict = None) -> DesignResult:
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

            # Validate each domain and overall strand
            validation_results = self._validate_strand(
                final_sequence, all_sequences, params, validation_config or {}
            )

            # Check individual domain validation
            for domain in domain_objects:
                domain_validation = self._validate_domain(domain.generated_sequence, params)
                domain.validation_passed = all(check.pass_check for check in domain_validation.values())

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
            logger.error(f"Design failed: {str(e)}")
            end_time = datetime.now()
            generation_time = (end_time - start_time).total_seconds()

            return DesignResult(
                success=False,
                generation_time=generation_time,
                generated_at=end_time.isoformat(),
                error_message=str(e)
            )

    def _validate_strand(self, sequence: str, all_sequences: List[str],
                         params: GlobalParams, config: Dict) -> ValidationResult:
        """Validate the complete strand"""
        checks = {}

        # Melting temperature
        checks['melting_temperature'] = self.validator.validate_melting_temperature(
            sequence, params,
            config.get('tm_min_offset', 5.0),
            config.get('tm_max_offset', 25.0)
        )

        # Hairpin formation
        checks['hairpin_formation'] = self.validator.validate_hairpin_formation(
            sequence, config.get('hairpin_max_dg', -3.0)
        )

        # Self-dimerization
        checks['self_dimerization'] = self.validator.validate_self_dimerization(
            sequence, config.get('self_dimer_max_dg', -6.0)
        )

        # Cross-dimerization
        other_sequences = [seq for seq in all_sequences if seq != sequence]
        checks['cross_dimerization'] = self.validator.validate_cross_dimerization(
            sequence, other_sequences, config.get('cross_dimer_max_dg', -6.0)
        )

        # GC content
        checks['gc_content'] = self.validator.validate_gc_content(
            sequence,
            config.get('gc_min', 40.0),
            config.get('gc_max', 60.0)
        )

        # 3' end stability
        checks['primer_3_end'] = self.validator.validate_primer_3_end(
            sequence, config.get('primer_3_end_max_dg', -3.0)
        )

        # Overall pass/fail
        overall_pass = all(check.pass_check for check in checks.values())

        return ValidationResult(
            overall_pass=overall_pass,
            checks=checks
        )

    def _validate_domain(self, sequence: str, params: GlobalParams) -> Dict[str, ValidationCheck]:
        """Validate individual domain"""
        return {
            'gc_content': self.validator.validate_gc_content(sequence),
            'repeats': self.validator.validate_repeats(sequence),
            'hairpin': self.validator.validate_hairpin_formation(sequence)
        }


# Flask API endpoints (example)
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend integration

designer = OligonucleotideDesigner()


@app.route('/api/generate-oligonucleotide', methods=['POST'])
def generate_oligonucleotide():
    """API endpoint for oligonucleotide generation"""
    try:
        data = request.get_json()

        result = designer.design_strand(
            strand_name=data['strand_name'],
            domains=data['domains'],
            global_params=data['global_params'],
            validation_config=data.get('validation_config', {})
        )

        # Convert to JSON-serializable format
        if result.success:
            response_data = {
                'success': True,
                'strand': {
                    'name': result.strand.name,
                    'total_length': result.strand.total_length,
                    'sequence': result.strand.sequence,
                    'domains': [asdict(domain) for domain in result.strand.domains]
                },
                'validation': {
                    'overall_pass': result.validation.overall_pass,
                    'checks': {name: asdict(check) for name, check in result.validation.checks.items()}
                },
                'generation_time': result.generation_time,
                'generated_at': result.generated_at
            }
        else:
            response_data = {
                'success': False,
                'error_message': result.error_message,
                'generation_time': result.generation_time,
                'generated_at': result.generated_at
            }

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"API error: {str(e)}")
        return jsonify({
            'success': False,
            'error_message': str(e)
        }), 500


@app.route('/api/repository/sequences', methods=['GET'])
def get_repository_sequences():
    """Get available sequences from repository"""
    length = request.args.get('length', type=int)
    if length:
        sequences = designer.repository.sequences_by_length.get(length, [])
    else:
        sequences = designer.repository.sequences_by_length

    return jsonify({
        'success': True,
        'sequences': sequences
    })


@app.route('/api/validate-sequence', methods=['POST'])
def validate_sequence():
    """Validate a single sequence"""
    try:
        data = request.get_json()
        sequence = data['sequence']
        params = GlobalParams(**data.get('global_params', {}))

        validation = designer._validate_domain(sequence, params)

        return jsonify({
            'success': True,
            'validation': {name: asdict(check) for name, check in validation.items()}
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error_message': str(e)
        }), 400


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)