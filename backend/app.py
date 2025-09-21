from flask import Flask, request, jsonify
from flask_cors import CORS
import redis
import json
import random
import uuid
from typing import Dict, List, Optional
import primer3

app = Flask(__name__)
CORS(app)

# Redis connection
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# In-memory domain cache (not stored in Redis)
domain_cache = {}


class OligoDesigner:
    def __init__(self):
        self.bases = ['A', 'T', 'G', 'C']

    def reverse_complement(self, sequence: str) -> str:
        """Generate reverse complement of DNA sequence"""
        complement = {'A': 'T', 'T': 'A', 'G': 'C', 'C': 'G'}
        return ''.join(complement[base] for base in reversed(sequence))

    def gc_content(self, sequence: str) -> float:
        """Calculate GC content percentage"""
        if not sequence:
            return 0
        gc_count = sequence.count('G') + sequence.count('C')
        return (gc_count / len(sequence)) * 100

    def melting_temp(self, sequence: str) -> float:
        """Calculate melting temperature using simple formula"""
        if len(sequence) < 14:
            return 2 * (sequence.count('A') + sequence.count('T')) + 4 * (sequence.count('G') + sequence.count('C'))
        else:
            gc = self.gc_content(sequence)
            return 64.9 + 41 * (gc - 16.4) / 100

    def validate_sequence(self, sequence: str, settings: Dict) -> Dict:
        """Validate sequence against all criteria using primer3"""
        results = {
            'gc_content': {'valid': True, 'value': 0, 'message': ''},
            'melting_temp': {'valid': True, 'value': 0, 'message': ''},
            'hairpin_dg': {'valid': True, 'value': 0, 'message': ''},
            'self_dimer_dg': {'valid': True, 'value': 0, 'message': ''},
            'three_prime_hairpin': {'valid': True, 'value': 0, 'message': ''},
            'three_prime_self_dimer': {'valid': True, 'value': 0, 'message': ''},
            'overall_valid': True
        }

        # GC content check
        gc = self.gc_content(sequence)
        results['gc_content']['value'] = round(gc, 1)
        if not (settings['gc_min'] <= gc <= settings['gc_max']):
            results['gc_content']['valid'] = False
            results['gc_content'][
                'message'] = f"GC content {gc:.1f}% outside range {settings['gc_min']}-{settings['gc_max']}%"
            results['overall_valid'] = False

        # Melting temperature check
        tm = self.melting_temp(sequence)
        results['melting_temp']['value'] = round(tm, 1)
        if not (settings['tm_min'] <= tm <= settings['tm_max']):
            results['melting_temp']['valid'] = False
            results['melting_temp'][
                'message'] = f"Tm {tm:.1f}°C outside range {settings['tm_min']}-{settings['tm_max']}°C"
            results['overall_valid'] = False

        # Thermodynamic checks using primer3
        try:
            temp = settings.get('temp', 37)

            # Hairpin check
            try:
                hairpin_result = primer3.calc_hairpin(sequence, mv_conc=50, dv_conc=1.5,
                                                      dntp_conc=0.6, dna_conc=50, temp_c=temp)
                hairpin_dg = hairpin_result.dg / 1000.0  # Convert cal/mol to kcal/mol
                results['hairpin_dg']['value'] = round(hairpin_dg, 2)

                if hairpin_dg < settings['hairpin_dg']:
                    results['hairpin_dg']['valid'] = False
                    results['hairpin_dg'][
                        'message'] = f"Hairpin ΔG {hairpin_dg:.2f} kcal/mol below threshold {settings['hairpin_dg']}"
                    results['overall_valid'] = False
            except Exception:
                results['hairpin_dg']['value'] = -1.0

            # Self-dimer check
            try:
                homodimer_result = primer3.calc_homodimer(sequence, mv_conc=50, dv_conc=1.5,
                                                          dntp_conc=0.6, dna_conc=50, temp_c=temp)
                self_dimer_dg = homodimer_result.dg / 1000.0  # Convert cal/mol to kcal/mol
                results['self_dimer_dg']['value'] = round(self_dimer_dg, 2)

                if self_dimer_dg < settings['self_dimer_dg']:
                    results['self_dimer_dg']['valid'] = False
                    results['self_dimer_dg'][
                        'message'] = f"Self-dimer ΔG {self_dimer_dg:.2f} kcal/mol below threshold {settings['self_dimer_dg']}"
                    results['overall_valid'] = False
            except Exception:
                results['self_dimer_dg']['value'] = -3.0

            # 3' end specific checks
            three_prime_end = sequence[-5:]  # Last 5 nucleotides

            # 3' hairpin check
            try:
                three_prime_hairpin_result = primer3.calc_hairpin(three_prime_end, mv_conc=50, dv_conc=1.5,
                                                                  dntp_conc=0.6, dna_conc=50, temp_c=temp)
                three_prime_hairpin_dg = three_prime_hairpin_result.dg / 1000.0
                results['three_prime_hairpin']['value'] = round(three_prime_hairpin_dg, 2)

                if three_prime_hairpin_dg < settings.get('three_prime_hairpin_dg', -2.0):
                    results['three_prime_hairpin']['valid'] = False
                    results['three_prime_hairpin'][
                        'message'] = f"3' hairpin ΔG {three_prime_hairpin_dg:.2f} kcal/mol below threshold"
                    results['overall_valid'] = False
            except Exception:
                results['three_prime_hairpin']['value'] = 0.0

            # 3' self-dimer check (3' end vs full sequence)
            try:
                three_prime_self_dimer_result = primer3.calc_heterodimer(three_prime_end, sequence, mv_conc=50,
                                                                         dv_conc=1.5,
                                                                         dntp_conc=0.6, dna_conc=50, temp_c=temp)
                three_prime_self_dimer_dg = three_prime_self_dimer_result.dg / 1000.0
                results['three_prime_self_dimer']['value'] = round(three_prime_self_dimer_dg, 2)

                if three_prime_self_dimer_dg < settings.get('three_prime_self_dimer_dg', -5.0):
                    results['three_prime_self_dimer']['valid'] = False
                    results['three_prime_self_dimer'][
                        'message'] = f"3' self-dimer ΔG {three_prime_self_dimer_dg:.2f} kcal/mol below threshold"
                    results['overall_valid'] = False
            except Exception:
                results['three_prime_self_dimer']['value'] = 0.0

        except Exception:
            pass

        return results

    def calculate_cross_dimer_dg(self, seq1: str, seq2: str, temp: float = 37) -> float:
        """Calculate cross-dimer ΔG using primer3"""
        try:
            heterodimer_result = primer3.calc_heterodimer(seq1, seq2, mv_conc=50, dv_conc=1.5,
                                                          dntp_conc=0.6, dna_conc=50, temp_c=temp)
            return heterodimer_result.dg / 1000.0
        except Exception:
            return 0.0

    def calculate_three_prime_cross_dimer_dg(self, seq1: str, seq2: str, temp: float = 37) -> float:
        """Calculate 3' end cross-dimer ΔG: 3' end of seq1 vs full seq2"""
        try:
            three_prime_end = seq1[-5:]  # Last 5 nucleotides of seq1
            heterodimer_result = primer3.calc_heterodimer(three_prime_end, seq2, mv_conc=50, dv_conc=1.5,
                                                          dntp_conc=0.6, dna_conc=50, temp_c=temp)
            return heterodimer_result.dg / 1000.0
        except Exception:
            return 0.0


def get_validation_messages(validation_results: Dict) -> List[str]:
    """Extract human-readable validation failure messages"""
    messages = []

    if not validation_results.get('overall_valid', True):
        for check, result in validation_results.items():
            if check == 'overall_valid':
                continue

            if isinstance(result, dict) and not result.get('valid', True):
                message = result.get('message', '')
                if message:
                    messages.append(message)
                else:
                    # Fallback message if no specific message
                    if check == 'gc_content':
                        messages.append(f"GC content {result.get('value', 'N/A')}% out of range")
                    elif check == 'melting_temp':
                        messages.append(f"Melting temperature {result.get('value', 'N/A')}°C out of range")
                    elif check == 'hairpin_dg':
                        messages.append(f"Hairpin ΔG {result.get('value', 'N/A')} kcal/mol too low")
                    elif check == 'self_dimer_dg':
                        messages.append(f"Self-dimer ΔG {result.get('value', 'N/A')} kcal/mol too low")
                    elif check == 'three_prime_hairpin':
                        messages.append(f"3' hairpin ΔG {result.get('value', 'N/A')} kcal/mol too low")
                    elif check == 'three_prime_self_dimer':
                        messages.append(f"3' self-dimer ΔG {result.get('value', 'N/A')} kcal/mol too low")

    return messages


# Initialize designer
designer = OligoDesigner()


# Helper functions for Redis operations (oligo sequences)
def get_oligos_by_length(length: int) -> List[str]:
    """Get all oligo sequences of specific length from Redis"""
    try:
        # Get sequence IDs for this length
        seq_ids = r.smembers(f"oligo:length:{length}")

        # Get actual sequences from the oligo records
        sequences = []
        for seq_id in seq_ids:
            sequence = r.hget(f"oligo:{seq_id}", "sequence")
            if sequence:
                sequences.append(sequence)

        return sequences
    except Exception:
        return []


def get_all_oligo_lengths() -> List[int]:
    """Get all available oligo lengths from Redis"""
    try:
        keys = r.keys("oligo:length:*")
        lengths = [int(key.split(':')[2]) for key in keys if r.scard(key) > 0]
        return sorted(lengths)
    except Exception:
        return []


def get_random_oligo(length: int) -> Optional[str]:
    """Get random oligo sequence of specific length from Redis, with fallback strategies"""
    # First try exact length
    oligos = get_oligos_by_length(length)
    if oligos:
        return random.choice(oligos)

    # Fallback: construct from shorter oligos
    return construct_oligo_from_shorter(length)


def check_can_construct_length(target_length: int, available_lengths: List[int]) -> bool:
    """Check if we can construct an oligo of target length from available lengths"""
    if not available_lengths:
        return False

    # Can always construct if exact length exists
    if target_length in available_lengths:
        return True

    # Can construct by truncating longer oligos
    if any(length > target_length for length in available_lengths):
        return True

    # Can construct by joining shorter oligos (any shorter length works)
    if any(length < target_length for length in available_lengths):
        return True

    return False


def construct_oligo_from_shorter(target_length: int) -> Optional[str]:
    """Construct oligo of target length by joining shorter oligos and truncating"""
    available_lengths = get_all_oligo_lengths()

    if not available_lengths:
        return None

    # Find the best length(s) to use
    # Prefer longer oligos to minimize joins
    suitable_lengths = [l for l in available_lengths if l < target_length]

    if not suitable_lengths:
        # If no shorter oligos available, try using longer ones and truncate
        longer_lengths = [l for l in available_lengths if l > target_length]
        if longer_lengths:
            best_length = min(longer_lengths)  # Use shortest available longer oligo
            oligos = get_oligos_by_length(best_length)
            if oligos:
                selected_oligo = random.choice(oligos)
                return selected_oligo[:target_length]  # Truncate to target length
        return None

    # Use the longest available shorter oligo as primary building block
    primary_length = max(suitable_lengths)

    constructed_sequence = ""
    remaining_length = target_length

    while remaining_length > 0:
        # Choose the best length for remaining space
        best_length = None
        for length in sorted(suitable_lengths, reverse=True):
            if length <= remaining_length:
                best_length = length
                break

        if not best_length:
            # Fill remaining space with shortest available oligo and truncate
            best_length = min(suitable_lengths)

        # Get random oligo of chosen length
        oligos = get_oligos_by_length(best_length)
        if not oligos:
            return None

        selected_oligo = random.choice(oligos)

        # Add to sequence (truncate if needed)
        if remaining_length >= len(selected_oligo):
            constructed_sequence += selected_oligo
            remaining_length -= len(selected_oligo)
        else:
            constructed_sequence += selected_oligo[:remaining_length]
            remaining_length = 0

    return constructed_sequence


def get_oligo_with_properties(length: int) -> Optional[Dict]:
    """Get random oligo with its thermodynamic properties"""
    try:
        # Get sequence IDs for this length
        seq_ids = list(r.smembers(f"oligo:length:{length}"))
        if not seq_ids:
            return None

        # Pick random sequence ID
        seq_id = random.choice(seq_ids)

        # Get the full oligo data
        oligo_data = r.hget(f"oligo:{seq_id}", "data")
        if oligo_data:
            return json.loads(oligo_data)

        return None
    except Exception:
        return None


# In-memory strand storage
strands = {}


# API Routes
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        r.ping()
        available_lengths = get_all_oligo_lengths()

        # Get database statistics
        total_oligos = r.scard('oligo:all') if r.exists('oligo:all') else 0

        # Get metadata if available
        metadata = r.hgetall('oligo:metadata')

        # Calculate construction range
        construction_info = {}
        if available_lengths:
            min_available = min(available_lengths)
            max_available = max(available_lengths)
            construction_info = {
                'min_constructible': 1,  # Can construct any length >= 1
                'max_practical': max_available * 3,  # Practical upper limit
                'exact_lengths': available_lengths,
                'construction_note': f"Can construct any length by joining/truncating available oligos ({min_available}-{max_available}nt)"
            }

        return jsonify({
            'status': 'healthy',
            'redis': 'connected',
            'server': 'Flask server running',
            'database': {
                'total_oligos': total_oligos,
                'available_lengths': available_lengths,
                'construction_capabilities': construction_info,
                'metadata': metadata
            }
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@app.route('/api/domain-cache', methods=['GET'])
def get_cache():
    """Get in-memory domain cache"""
    cache_list = [{'name': name, 'length': length} for name, length in domain_cache.items()]
    return jsonify(cache_list)


@app.route('/api/domain-cache/<domain_name>', methods=['DELETE'])
def remove_cache_domain(domain_name):
    """Remove domain from in-memory cache"""
    try:
        if domain_name in domain_cache:
            del domain_cache[domain_name]
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/domains', methods=['GET'])
def get_domains():
    """Get domain cache as domain list for frontend compatibility"""
    # Return empty list since we don't store domain instances
    return jsonify([])


@app.route('/api/domains', methods=['POST'])
def add_domain():
    """Add domain to in-memory cache"""
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400

        if 'name' not in data or not data['name'].strip():
            return jsonify({'success': False, 'error': 'Domain name is required'}), 400

        if 'length' not in data:
            return jsonify({'success': False, 'error': 'Domain length is required'}), 400

        try:
            length = int(data['length'])
            if length < 1 or length > 100:
                return jsonify({'success': False, 'error': 'Domain length must be between 1 and 100'}), 400
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'Domain length must be a valid number'}), 400

        name = data['name'].strip().rstrip('*')

        # Check if domain already exists in cache
        if name in domain_cache:
            return jsonify({'success': False, 'error': f'Domain "{name}" already exists in cache'}), 400

        # Check if we have oligos in Redis database
        available_lengths = get_all_oligo_lengths()
        if not available_lengths:
            return jsonify({'success': False, 'error': 'No oligos found in Redis database. Load oligos first.'}), 400

        # Check if we can construct oligo of this length
        can_construct = check_can_construct_length(length, available_lengths)
        if not can_construct:
            return jsonify({
                'success': False,
                'error': f'Cannot construct oligo of length {length}nt. Available lengths: {available_lengths}'
            }), 400

        # Add to in-memory cache
        domain_cache[name] = length

        # Determine construction method for user info
        if length in available_lengths:
            method = f"exact match available"
        else:
            method = f"will construct from available lengths: {available_lengths}"

        return jsonify({
            'success': True,
            'message': f'Added domain "{name}" to cache with length {length}nt ({method})'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/strands', methods=['GET'])
def get_strands():
    """Get all strands from memory"""
    strand_list = []
    for strand_id, strand_data in strands.items():
        strand_list.append({
            'id': strand_id,
            'name': strand_data['name'],
            'domains': strand_data['domains'],
            'sequence': strand_data.get('sequence', ''),
            'validation_results': strand_data.get('validation_results', {})
        })
    return jsonify(sorted(strand_list, key=lambda x: x['name']))


@app.route('/api/strands', methods=['POST'])
def add_strand():
    """Add new strand"""
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400

        name = data.get('name', '').strip()
        domains = data.get('domains', [])

        if not name:
            return jsonify({'success': False, 'error': 'Strand name is required'}), 400

        if not domains:
            return jsonify({'success': False, 'error': 'At least one domain is required'}), 400

        # Validate that all domains exist in cache
        for domain_name in domains:
            base_name = domain_name.rstrip('*')
            if base_name not in domain_cache:
                return jsonify(
                    {'success': False, 'error': f'Domain "{base_name}" not found in cache. Add it first.'}), 400

        strand_id = str(uuid.uuid4())
        strands[strand_id] = {
            'name': name,
            'domains': domains
        }

        return jsonify({'success': True, 'id': strand_id})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/strands/<strand_id>', methods=['DELETE'])
def delete_strand(strand_id):
    """Delete strand"""
    try:
        if strand_id in strands:
            del strands[strand_id]
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/generate-strands', methods=['POST'])
def generate_strands():
    """Generate strand sequences by randomly selecting oligos from Redis"""
    data = request.json
    settings = data.get('settings', {})
    strand_ids = data.get('strand_ids', [])

    try:
        # Get target strands
        target_strands = [strands[sid] for sid in strand_ids if sid in strands]

        if not target_strands:
            return jsonify({'success': False, 'error': 'No strands selected'})

        # Collect all unique base domain names needed
        required_domains = set()
        for strand in target_strands:
            for domain_name in strand['domains']:
                base_name = domain_name.rstrip('*')
                required_domains.add(base_name)

        # Randomly select oligo sequences for each required domain
        domain_assignments = {}
        errors = []

        for base_name in required_domains:
            if base_name not in domain_cache:
                errors.append(f"Domain '{base_name}' not found in cache")
                continue

            length = domain_cache[base_name]

            # Get random oligo sequence of this length from Redis
            base_sequence = get_random_oligo(length)

            if base_sequence:
                domain_assignments[base_name] = base_sequence
                domain_assignments[base_name + '*'] = designer.reverse_complement(base_sequence)
            else:
                errors.append(f"No oligo sequences of length {length} found in Redis for domain '{base_name}'")

        # Build strand sequences using assigned domain sequences
        generated_strands = []
        for strand in target_strands:
            strand_seq = ""
            can_build = True

            for domain_name in strand['domains']:
                if domain_name in domain_assignments:
                    strand_seq += domain_assignments[domain_name]
                else:
                    can_build = False
                    break

            if can_build and strand_seq:
                # Validate the complete strand sequence
                strand_validation = designer.validate_sequence(strand_seq, settings)

                # Update strand with sequence and validation
                strand_id = next(sid for sid, s in strands.items() if s == strand)
                strands[strand_id]['sequence'] = strand_seq
                strands[strand_id]['validation_results'] = strand_validation

                generated_strands.append({
                    'name': strand['name'],
                    'sequence': strand_seq,
                    'length': len(strand_seq),
                    'valid': strand_validation['overall_valid'],
                    'validation_details': strand_validation,
                    'validation_messages': get_validation_messages(strand_validation)
                })
            else:
                errors.append(f"Could not build sequence for strand '{strand['name']}'")

        # Prepare response
        success = len(errors) == 0
        message = f"Built {len(generated_strands)} strands using random oligos from Redis"
        if errors:
            message += f" with {len(errors)} errors"

        return jsonify({
            'success': success,
            'message': message,
            'generated_strands': generated_strands,
            'errors': errors
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/check-cross-dimers', methods=['POST'])
def check_cross_dimers():
    """Check 3' end cross-dimer interactions between selected strands"""
    data = request.json
    settings = data.get('settings', {})
    strand_ids = data.get('strand_ids', [])

    try:
        # Get target strands with sequences
        target_strands = []
        for sid in strand_ids:
            if sid in strands and strands[sid].get('sequence'):
                target_strands.append({
                    'id': sid,
                    'name': strands[sid]['name'],
                    'sequence': strands[sid]['sequence']
                })

        if len(target_strands) < 2:
            return jsonify({
                'success': False,
                'error': 'Need at least 2 strands with sequences for cross-dimer analysis. Build strands first.'
            })

        # Run 3' end cross-dimer analysis - ALL PAIRWISE COMBINATIONS
        results = []
        for i, strand1 in enumerate(target_strands):
            for j, strand2 in enumerate(target_strands):
                if i == j:  # Skip self-interaction
                    continue

                # Calculate 3' end cross-dimer ΔG: 3' end of strand1 vs full strand2
                cross_dg = designer.calculate_three_prime_cross_dimer_dg(
                    strand1['sequence'],
                    strand2['sequence'],
                    settings.get('temp', 37)
                )

                # Check if problematic (ΔG below threshold)
                threshold = settings.get('cross_dimer_dg', -8.0)
                problematic = cross_dg < threshold

                # Generate reason message for problematic interactions
                reason = ""
                if problematic:
                    three_prime = strand1['sequence'][-5:]
                    reason = f"3' end of {strand1['name']} ({three_prime}) binding to full {strand2['name']}: ΔG ({cross_dg:.2f} kcal/mol) below threshold ({threshold:.1f} kcal/mol)"

                results.append({
                    'strand1': strand1['name'],
                    'strand2': strand2['name'],
                    'interaction_type': f"3'({strand1['name']}) → full({strand2['name']})",
                    'three_prime_sequence': strand1['sequence'][-5:],
                    'dg': cross_dg,
                    'problematic': problematic,
                    'reason': reason
                })

        # Count problematic interactions
        problematic_count = sum(1 for r in results if r['problematic'])

        return jsonify({
            'type': 'cross-dimer',
            'success': True,
            'cross_dimer_results': results,
            'message': f"Analyzed {len(results)} 3' end interactions ({len(target_strands)} strands, all pairs). Found {problematic_count} problematic interactions."
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/check-three-prime-analysis', methods=['POST'])
def check_three_prime_analysis():
    """Comprehensive 3' end analysis for selected strands"""
    data = request.json
    settings = data.get('settings', {})
    strand_ids = data.get('strand_ids', [])

    try:
        # Get target strands with sequences
        target_strands = []
        for sid in strand_ids:
            if sid in strands and strands[sid].get('sequence'):
                target_strands.append({
                    'id': sid,
                    'name': strands[sid]['name'],
                    'sequence': strands[sid]['sequence']
                })

        if not target_strands:
            return jsonify({
                'success': False,
                'error': 'Need at least 1 strand with sequence for 3\' analysis. Build strands first.'
            })

        results = []
        temp = settings.get('temp', 37)

        for strand in target_strands:
            sequence = strand['sequence']
            three_prime_end = sequence[-5:]

            strand_result = {
                'strand_name': strand['name'],
                'three_prime_sequence': three_prime_end,
                'checks': {}
            }

            # 1. 3' Hairpin formation
            try:
                hairpin_result = primer3.calc_hairpin(three_prime_end, mv_conc=50, dv_conc=1.5,
                                                      dntp_conc=0.6, dna_conc=50, temp_c=temp)
                hairpin_dg = hairpin_result.dg / 1000.0
                threshold = settings.get('three_prime_hairpin_dg', -2.0)
                strand_result['checks']['hairpin'] = {
                    'dg': round(hairpin_dg, 2),
                    'threshold': threshold,
                    'problematic': hairpin_dg < threshold,
                    'description': f"3' hairpin formation (last 5nt)"
                }
            except Exception:
                strand_result['checks']['hairpin'] = {
                    'dg': 0.0,
                    'threshold': threshold,
                    'problematic': False,
                    'description': "3' hairpin formation (calculation failed)"
                }

            # 2. 3' Self-dimer formation (3' end vs full sequence)
            try:
                self_dimer_result = primer3.calc_heterodimer(three_prime_end, sequence, mv_conc=50, dv_conc=1.5,
                                                             dntp_conc=0.6, dna_conc=50, temp_c=temp)
                self_dimer_dg = self_dimer_result.dg / 1000.0
                threshold = settings.get('three_prime_self_dimer_dg', -5.0)
                strand_result['checks']['self_dimer'] = {
                    'dg': round(self_dimer_dg, 2),
                    'threshold': threshold,
                    'problematic': self_dimer_dg < threshold,
                    'description': f"3' end binding to own full sequence"
                }
            except Exception:
                threshold = settings.get('three_prime_self_dimer_dg', -5.0)
                strand_result['checks']['self_dimer'] = {
                    'dg': 0.0,
                    'threshold': threshold,
                    'problematic': False,
                    'description': "3' self-dimer (calculation failed)"
                }

            # 3. 3' Cross-dimer formation with other strands
            cross_dimers = []
            for other_strand in target_strands:
                if other_strand['name'] != strand['name']:
                    try:
                        cross_dimer_result = primer3.calc_heterodimer(three_prime_end, other_strand['sequence'],
                                                                      mv_conc=50, dv_conc=1.5,
                                                                      dntp_conc=0.6, dna_conc=50, temp_c=temp)
                        cross_dimer_dg = cross_dimer_result.dg / 1000.0
                        threshold = settings.get('cross_dimer_dg', -8.0)
                        cross_dimers.append({
                            'target_strand': other_strand['name'],
                            'dg': round(cross_dimer_dg, 2),
                            'threshold': threshold,
                            'problematic': cross_dimer_dg < threshold
                        })
                    except Exception:
                        cross_dimers.append({
                            'target_strand': other_strand['name'],
                            'dg': 0.0,
                            'threshold': threshold,
                            'problematic': False
                        })

            strand_result['checks']['cross_dimers'] = cross_dimers
            results.append(strand_result)

        # Count total problematic interactions
        total_problematic = 0
        for strand_result in results:
            if strand_result['checks']['hairpin']['problematic']:
                total_problematic += 1
            if strand_result['checks']['self_dimer']['problematic']:
                total_problematic += 1
            total_problematic += sum(1 for cd in strand_result['checks']['cross_dimers'] if cd['problematic'])

        return jsonify({
            'type': 'three-prime-analysis',
            'success': True,
            'three_prime_results': results,
            'message': f"Analyzed 3' ends of {len(target_strands)} strands. Found {total_problematic} problematic interactions."
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/generate-optimized-strand-sets', methods=['POST'])
def generate_optimized_strand_sets():
    """Generate 100 different strand sets, validate all, return top ranked sets"""
    data = request.json
    settings = data.get('settings', {})
    strand_ids = data.get('strand_ids', [])
    num_generations = data.get('num_generations', 100)

    try:
        # Get target strands
        target_strands = [strands[sid] for sid in strand_ids if sid in strands]

        if not target_strands:
            return jsonify({'success': False, 'error': 'No strands selected'})

        # Collect all unique base domain names needed
        required_domains = set()
        for strand in target_strands:
            for domain_name in strand['domains']:
                base_name = domain_name.rstrip('*')
                required_domains.add(base_name)

        valid_strand_sets = []

        for generation in range(num_generations):
            # Generate random domain assignments for this iteration
            domain_assignments = {}
            generation_failed = False

            for base_name in required_domains:
                if base_name not in domain_cache:
                    generation_failed = True
                    break

                length = domain_cache[base_name]
                base_sequence = get_random_oligo(length)

                if base_sequence:
                    domain_assignments[base_name] = base_sequence
                    domain_assignments[base_name + '*'] = designer.reverse_complement(base_sequence)
                else:
                    generation_failed = True
                    break

            if generation_failed:
                continue

            # Build strand sequences for this generation
            generation_strands = []
            all_valid = True

            for strand in target_strands:
                strand_seq = ""
                for domain_name in strand['domains']:
                    if domain_name in domain_assignments:
                        strand_seq += domain_assignments[domain_name]
                    else:
                        all_valid = False
                        break

                if not all_valid:
                    break

                # Validate individual strand
                strand_validation = designer.validate_sequence(strand_seq, settings)
                if not strand_validation['overall_valid']:
                    all_valid = False
                    break

                generation_strands.append({
                    'name': strand['name'],
                    'sequence': strand_seq,
                    'validation': strand_validation
                })

            if not all_valid:
                continue

            # Check cross-dimer interactions for this generation
            cross_dimer_valid = True
            cross_dimer_results = []

            for i, strand1 in enumerate(generation_strands):
                for j, strand2 in enumerate(generation_strands):
                    if i == j:
                        continue

                    cross_dg = designer.calculate_three_prime_cross_dimer_dg(
                        strand1['sequence'],
                        strand2['sequence'],
                        settings.get('temp', 37)
                    )

                    cross_dimer_results.append({
                        'strand1': strand1['name'],
                        'strand2': strand2['name'],
                        'dg': cross_dg
                    })

                    if cross_dg < settings.get('cross_dimer_dg', -8.0):
                        cross_dimer_valid = False

            if cross_dimer_valid:
                # Calculate score for this valid set
                score = calculate_strand_set_score(generation_strands, cross_dimer_results, settings)

                valid_strand_sets.append({
                    'generation': generation + 1,
                    'strands': generation_strands,
                    'cross_dimer_results': cross_dimer_results,
                    'score': score,
                    'score_details': score  # Will contain breakdown
                })

        # Sort by score (highest first) and return top results
        valid_strand_sets.sort(key=lambda x: x['score']['total'], reverse=True)
        top_sets = valid_strand_sets[:10]  # Return top 10

        return jsonify({
            'success': True,
            'message': f"Generated {num_generations} strand sets. Found {len(valid_strand_sets)} valid sets.",
            'total_generated': num_generations,
            'total_valid': len(valid_strand_sets),
            'top_strand_sets': top_sets
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def calculate_strand_set_score(strands, cross_dimer_results, settings):
    """Penalty-based scoring: Start at 100, subtract penalties for violations and suboptimal conditions"""

    score = 100.0
    penalties = {
        'thermodynamic_violations': 0,
        'three_prime_imbalance': 0,
        'cross_dimer_risks': 0,
        'details': []
    }

    # 1. Thermodynamic Violation Penalties
    for strand in strands:
        validation = strand['validation']
        strand_name = strand['name']

        # Hairpin too stable: -5 points per kcal/mol below threshold
        hairpin_threshold = settings.get('hairpin_dg', -2.0)
        hairpin_actual = validation.get('hairpin_dg', {}).get('value', 0)
        if hairpin_actual < hairpin_threshold:
            penalty = abs(hairpin_actual - hairpin_threshold) * 5
            penalties['thermodynamic_violations'] += penalty
            penalties['details'].append(
                f"{strand_name}: Hairpin too stable ({hairpin_actual} < {hairpin_threshold}) - {penalty:.1f}pts")

        # Self-dimer too stable: -3 points per kcal/mol below threshold
        self_dimer_threshold = settings.get('self_dimer_dg', -5.0)
        self_dimer_actual = validation.get('self_dimer_dg', {}).get('value', 0)
        if self_dimer_actual < self_dimer_threshold:
            penalty = abs(self_dimer_actual - self_dimer_threshold) * 3
            penalties['thermodynamic_violations'] += penalty
            penalties['details'].append(
                f"{strand_name}: Self-dimer too stable ({self_dimer_actual} < {self_dimer_threshold}) - {penalty:.1f}pts")

        # 3' hairpin too stable: -6 points per kcal/mol below threshold
        three_prime_hairpin_threshold = settings.get('three_prime_hairpin_dg', -2.0)
        three_prime_hairpin_actual = validation.get('three_prime_hairpin', {}).get('value', 0)
        if three_prime_hairpin_actual < three_prime_hairpin_threshold:
            penalty = abs(three_prime_hairpin_actual - three_prime_hairpin_threshold) * 6
            penalties['thermodynamic_violations'] += penalty
            penalties['details'].append(
                f"{strand_name}: 3' hairpin too stable ({three_prime_hairpin_actual} < {three_prime_hairpin_threshold}) - {penalty:.1f}pts")

    # 2. 3' End Stability Imbalance Penalties
    ideal_range = (-6.0, -3.0)  # Ideal range for 3' self-dimer ΔG
    for strand in strands:
        strand_name = strand['name']
        three_prime_dg = strand['validation'].get('three_prime_self_dimer', {}).get('value', 0)

        if three_prime_dg > ideal_range[1]:  # Too weak (>-3.0)
            penalty = (three_prime_dg - ideal_range[1]) * 4
            penalties['three_prime_imbalance'] += penalty
            penalties['details'].append(
                f"{strand_name}: 3' end too weak ({three_prime_dg} > {ideal_range[1]}) - {penalty:.1f}pts")
        elif three_prime_dg < ideal_range[0]:  # Too strong (<-6.0)
            penalty = abs(three_prime_dg - ideal_range[0]) * 6
            penalties['three_prime_imbalance'] += penalty
            penalties['details'].append(
                f"{strand_name}: 3' end too strong ({three_prime_dg} < {ideal_range[0]}) - {penalty:.1f}pts")

    # 3. Cross-Dimer Risk Penalties
    cross_dimer_threshold = settings.get('cross_dimer_dg', -8.0)
    danger_zone = cross_dimer_threshold + 2.0  # -6.0 if threshold is -8.0

    for result in cross_dimer_results:
        interaction = f"{result['strand1']} → {result['strand2']}"

        if result['dg'] < cross_dimer_threshold:
            # CRITICAL: Below threshold - severe penalty
            penalty = abs(result['dg'] - cross_dimer_threshold) * 15
            penalties['cross_dimer_risks'] += penalty
            penalties['details'].append(
                f"{interaction}: Cross-dimer violation ({result['dg']:.2f} < {cross_dimer_threshold}) - {penalty:.1f}pts")
        elif result['dg'] < danger_zone:
            # WARNING: Close to threshold - moderate penalty
            penalty = abs(result['dg'] - danger_zone) * 3
            penalties['cross_dimer_risks'] += penalty
            penalties['details'].append(
                f"{interaction}: Cross-dimer risk ({result['dg']:.2f} near threshold) - {penalty:.1f}pts")

    # Calculate final score and totals
    total_penalty = penalties['thermodynamic_violations'] + penalties['three_prime_imbalance'] + penalties[
        'cross_dimer_risks']
    final_score = max(0, score - total_penalty)

    return {
        'total': round(final_score, 2),
        'penalties': {
            'thermodynamic_violations': round(penalties['thermodynamic_violations'], 2),
            'three_prime_imbalance': round(penalties['three_prime_imbalance'], 2),
            'cross_dimer_risks': round(penalties['cross_dimer_risks'], 2),
            'total_penalty': round(total_penalty, 2)
        },
        'penalty_details': penalties['details']
    }


# @app.route('/api/generate-optimized-strand-sets', methods=['POST'])
# def generate_optimized_strand_sets():
#     """Generate 100 different strand sets, validate all, return top ranked sets"""
#     data = request.json
#     settings = data.get('settings', {})
#     strand_ids = data.get('strand_ids', [])
#     num_generations = data.get('num_generations', 100)
#
#     try:
#         # Get target strands
#         target_strands = [strands[sid] for sid in strand_ids if sid in strands]
#
#         if not target_strands:
#             return jsonify({'success': False, 'error': 'No strands selected'})
#
#         # Collect all unique base domain names needed
#         required_domains = set()
#         for strand in target_strands:
#             for domain_name in strand['domains']:
#                 base_name = domain_name.rstrip('*')
#                 required_domains.add(base_name)
#
#         valid_strand_sets = []
#
#         for generation in range(num_generations):
#             # Generate random domain assignments for this iteration
#             domain_assignments = {}
#             generation_failed = False
#
#             for base_name in required_domains:
#                 if base_name not in domain_cache:
#                     generation_failed = True
#                     break
#
#                 length = domain_cache[base_name]
#                 base_sequence = get_random_oligo(length)
#
#                 if base_sequence:
#                     domain_assignments[base_name] = base_sequence
#                     domain_assignments[base_name + '*'] = designer.reverse_complement(base_sequence)
#                 else:
#                     generation_failed = True
#                     break
#
#             if generation_failed:
#                 continue
#
#             # Build strand sequences for this generation
#             generation_strands = []
#             all_valid = True
#
#             for strand in target_strands:
#                 strand_seq = ""
#                 for domain_name in strand['domains']:
#                     if domain_name in domain_assignments:
#                         strand_seq += domain_assignments[domain_name]
#                     else:
#                         all_valid = False
#                         break
#
#                 if not all_valid:
#                     break
#
#                 # Validate individual strand
#                 strand_validation = designer.validate_sequence(strand_seq, settings)
#                 if not strand_validation['overall_valid']:
#                     all_valid = False
#                     break
#
#                 generation_strands.append({
#                     'name': strand['name'],
#                     'sequence': strand_seq,
#                     'validation': strand_validation
#                 })
#
#             if not all_valid:
#                 continue
#
#             # Check cross-dimer interactions for this generation
#             cross_dimer_valid = True
#             cross_dimer_results = []
#
#             for i, strand1 in enumerate(generation_strands):
#                 for j, strand2 in enumerate(generation_strands):
#                     if i == j:
#                         continue
#
#                     cross_dg = designer.calculate_three_prime_cross_dimer_dg(
#                         strand1['sequence'],
#                         strand2['sequence'],
#                         settings.get('temp', 37)
#                     )
#
#                     cross_dimer_results.append({
#                         'strand1': strand1['name'],
#                         'strand2': strand2['name'],
#                         'dg': cross_dg
#                     })
#
#                     if cross_dg < settings.get('cross_dimer_dg', -8.0):
#                         cross_dimer_valid = False
#
#             if cross_dimer_valid:
#                 # Calculate score for this valid set
#                 score = calculate_strand_set_score(generation_strands, cross_dimer_results, settings)
#
#                 valid_strand_sets.append({
#                     'generation': generation + 1,
#                     'strands': generation_strands,
#                     'cross_dimer_results': cross_dimer_results,
#                     'score': score
#                 })
#
#         # Sort by score (highest first) and return top results
#         valid_strand_sets.sort(key=lambda x: x['score']['total'], reverse=True)
#         top_sets = valid_strand_sets[:10]  # Return top 10
#
#         return jsonify({
#             'success': True,
#             'message': f"Generated {num_generations} strand sets. Found {len(valid_strand_sets)} valid sets.",
#             'total_generated': num_generations,
#             'total_valid': len(valid_strand_sets),
#             'top_strand_sets': top_sets
#         })
#
#     except Exception as e:
#         return jsonify({'success': False, 'error': str(e)}), 500
#

def calculate_strand_set_score(strands, cross_dimer_results, settings):
    """Penalty-based scoring: Start at 100, subtract penalties for violations and suboptimal conditions"""

    score = 100.0
    penalties = {
        'thermodynamic_violations': 0,
        'three_prime_imbalance': 0,
        'cross_dimer_risks': 0,
        'details': []
    }

    # 1. Thermodynamic Violation Penalties
    for strand in strands:
        validation = strand['validation']
        strand_name = strand['name']

        # Hairpin too stable: -5 points per kcal/mol below threshold
        hairpin_threshold = settings.get('hairpin_dg', -2.0)
        hairpin_actual = validation.get('hairpin_dg', {}).get('value', 0)
        if hairpin_actual < hairpin_threshold:
            penalty = abs(hairpin_actual - hairpin_threshold) * 5
            penalties['thermodynamic_violations'] += penalty
            penalties['details'].append(
                f"{strand_name}: Hairpin too stable ({hairpin_actual} < {hairpin_threshold}) - {penalty:.1f}pts")

        # Self-dimer too stable: -3 points per kcal/mol below threshold
        self_dimer_threshold = settings.get('self_dimer_dg', -5.0)
        self_dimer_actual = validation.get('self_dimer_dg', {}).get('value', 0)
        if self_dimer_actual < self_dimer_threshold:
            penalty = abs(self_dimer_actual - self_dimer_threshold) * 3
            penalties['thermodynamic_violations'] += penalty
            penalties['details'].append(
                f"{strand_name}: Self-dimer too stable ({self_dimer_actual} < {self_dimer_threshold}) - {penalty:.1f}pts")

        # 3' hairpin too stable: -6 points per kcal/mol below threshold
        three_prime_hairpin_threshold = settings.get('three_prime_hairpin_dg', -2.0)
        three_prime_hairpin_actual = validation.get('three_prime_hairpin', {}).get('value', 0)
        if three_prime_hairpin_actual < three_prime_hairpin_threshold:
            penalty = abs(three_prime_hairpin_actual - three_prime_hairpin_threshold) * 6
            penalties['thermodynamic_violations'] += penalty
            penalties['details'].append(
                f"{strand_name}: 3' hairpin too stable ({three_prime_hairpin_actual} < {three_prime_hairpin_threshold}) - {penalty:.1f}pts")

    # 2. 3' End Stability Imbalance Penalties
    ideal_range = (-6.0, -3.0)  # Ideal range for 3' self-dimer ΔG
    for strand in strands:
        strand_name = strand['name']
        three_prime_dg = strand['validation'].get('three_prime_self_dimer', {}).get('value', 0)

        if three_prime_dg > ideal_range[1]:  # Too weak (>-3.0)
            penalty = (three_prime_dg - ideal_range[1]) * 4
            penalties['three_prime_imbalance'] += penalty
            penalties['details'].append(
                f"{strand_name}: 3' end too weak ({three_prime_dg} > {ideal_range[1]}) - {penalty:.1f}pts")
        elif three_prime_dg < ideal_range[0]:  # Too strong (<-6.0)
            penalty = abs(three_prime_dg - ideal_range[0]) * 6
            penalties['three_prime_imbalance'] += penalty
            penalties['details'].append(
                f"{strand_name}: 3' end too strong ({three_prime_dg} < {ideal_range[0]}) - {penalty:.1f}pts")

    # 3. Cross-Dimer Risk Penalties
    cross_dimer_threshold = settings.get('cross_dimer_dg', -8.0)
    danger_zone = cross_dimer_threshold + 2.0  # -6.0 if threshold is -8.0

    for result in cross_dimer_results:
        interaction = f"{result['strand1']} → {result['strand2']}"

        if result['dg'] < cross_dimer_threshold:
            # CRITICAL: Below threshold - severe penalty
            penalty = abs(result['dg'] - cross_dimer_threshold) * 15
            penalties['cross_dimer_risks'] += penalty
            penalties['details'].append(
                f"{interaction}: Cross-dimer violation ({result['dg']:.2f} < {cross_dimer_threshold}) - {penalty:.1f}pts")
        elif result['dg'] < danger_zone:
            # WARNING: Close to threshold - moderate penalty
            penalty = abs(result['dg'] - danger_zone) * 3
            penalties['cross_dimer_risks'] += penalty
            penalties['details'].append(
                f"{interaction}: Cross-dimer risk ({result['dg']:.2f} near threshold) - {penalty:.1f}pts")

    # Calculate final score and totals
    total_penalty = penalties['thermodynamic_violations'] + penalties['three_prime_imbalance'] + penalties[
        'cross_dimer_risks']
    final_score = max(0, score - total_penalty)

    return {
        'total': round(final_score, 2),
        'penalties': {
            'thermodynamic_violations': round(penalties['thermodynamic_violations'], 2),
            'three_prime_imbalance': round(penalties['three_prime_imbalance'], 2),
            'cross_dimer_risks': round(penalties['cross_dimer_risks'], 2),
            'total_penalty': round(total_penalty, 2)
        },
        'penalty_details': penalties['details']
    }


if __name__ == '__main__':
    app.run(debug=True, port=5000)