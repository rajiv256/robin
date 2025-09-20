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
    """Check cross-dimer interactions between selected strands"""
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

        # Run cross-dimer analysis
        results = []
        for i, strand1 in enumerate(target_strands):
            for j, strand2 in enumerate(target_strands):
                if i >= j:  # Avoid duplicates and self-interaction
                    continue

                # Calculate cross-dimer ΔG
                cross_dg = designer.calculate_cross_dimer_dg(
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
                    reason = f"Cross-dimer ΔG ({cross_dg:.2f} kcal/mol) is below threshold ({threshold:.1f} kcal/mol)"

                results.append({
                    'strand1': strand1['name'],
                    'strand2': strand2['name'],
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
            'message': f"Analyzed {len(results)} strand pairs. Found {problematic_count} problematic interactions."
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)