#!/usr/bin/env python3
"""
DNA Strand Generator integrated with OligoDesigner Frontend
Creates strands from Redis database based on frontend domain specifications
"""

import redis
import json
import primer3
from typing import List, Dict, Optional, Tuple
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


class StrandGenerator:
    """Generate DNA strands from Redis database using frontend domain specifications"""

    def __init__(self, redis_host='localhost', redis_port=6379, redis_db=0):
        """Initialize Redis connection"""
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True
        )

        # Test connection
        self.redis_client.ping()
        print(f"Connected to Redis at {redis_host}:{redis_port}")

    def get_sequences_by_criteria(self, length: int, max_count: int = 100) -> List[Dict]:
        """Get sequences from Redis that match length criteria"""
        seq_ids = list(self.redis_client.smembers(f"oligo:length:{length}"))
        print("length, ", len(seq_ids))

        sequences = []
        for seq_id in seq_ids[:max_count * 2]:  # Get extra for filtering
            data = self.redis_client.hget(f"oligo:{seq_id}", 'data')
            if data:
                sequences.append(json.loads(data))

        return self._filter_quality_sequences(sequences)[:max_count]

    def _filter_quality_sequences(self, sequences: List[Dict]) -> List[Dict]:
        # """Filter sequences based on quality criteria"""
        # filtered = []
        #
        # for seq in sequences:
        #     # Quality criteria based on thermodynamic properties
        #     if (seq['hairpin_dg'] > -3.0 and  # Low hairpin formation
        #             seq['homodimer_dg'] > -6.0 and  # Low self-dimerization
        #             not seq['has_repeats'] and  # No repeats
        #             40 <= seq['gc_content'] <= 60 and  # Reasonable GC content
        #             seq['complexity'] > 0.7):  # Good sequence complexity
        #         filtered.append(seq)
        #
        # # Sort by thermodynamic stability (lower absolute energy = better)
        # filtered.sort(key=lambda x: abs(x['hairpin_dg']) + abs(x['homodimer_dg']))
        # return filtered
        return sequences

    def check_cross_compatibility(self, sequences: List[str]) -> List[Tuple[int, int, float]]:
        """Check cross-dimerization between all sequence pairs"""
        cross_dimers = []

        for i in range(len(sequences)):
            for j in range(i + 1, len(sequences)):
                result = primer3.calc_heterodimer(
                    sequences[i], sequences[j],
                    mv_conc=50.0, dv_conc=0.0, dntp_conc=0.0, temp_c=37.0
                )
                dg = result.dg / 1000.0  # Convert to kcal/mol
                cross_dimers.append((i, j, dg))

        return cross_dimers

    def generate_strand_from_domains(self, strand_request: Dict) -> Dict:
        """Generate strand based on frontend domain specifications"""
        domains = strand_request.get('domains', [])
        strand_name = strand_request.get('strand_name', 'Generated Strand')
        global_params = strand_request.get('global_params', {})
        validation_settings = strand_request.get('validation_settings', {})

        if not domains:
            return {'success': False, 'error': 'No domains specified'}

        print(f"Generating strand '{strand_name}' with {len(domains)} domains")

        # Generate sequences for each domain
        generated_domains = []
        all_sequences = []

        for i, domain in enumerate(domains):
            domain_name = domain.get('name', f'Domain_{i + 1}')
            domain_length = domain.get('length', 15)

            print(f"Finding sequence for {domain_name} (length: {domain_length})")

            # Get candidate sequences from Redis
            candidates = self.get_sequences_by_criteria(domain_length, max_count=50)

            if not candidates:
                return {'success': False,
                        'error': f'No suitable sequences found for {domain_name} (length {domain_length})'}

            # Select best sequence that doesn't cross-react with existing domains
            selected_seq = None
            for candidate in candidates:
                seq = candidate['sequence']

                # Check cross-reactivity with already selected sequences
                compatible = True
                for existing_seq in all_sequences:
                    cross_dg = self._calc_cross_dimer(seq, existing_seq)
                    if cross_dg < -6.0:  # Too much cross-reactivity
                        compatible = False
                        break

                if compatible:
                    selected_seq = candidate
                    break

            if not selected_seq:
                # Fallback: use best candidate anyway with warning
                selected_seq = candidates[0]
                print(f"Warning: Using potentially cross-reactive sequence for {domain_name}")

            # Store domain with sequence (no individual validation)
            generated_domains.append({
                'name': domain_name,
                'length': domain_length,
                'sequence': selected_seq['sequence']
            })

            all_sequences.append(selected_seq['sequence'])

        # Construct full strand
        full_sequence = ''.join([d['sequence'] for d in generated_domains])

        # Calculate full strand properties
        strand_properties = self._calculate_full_strand_properties(
            full_sequence, global_params
        )

        # Validate only the full strand
        validation_results = self._validate_full_strand(
            full_sequence, global_params, validation_settings
        )

        result = {
            'success': True,
            'strand': {
                'name': strand_name,
                'sequence': full_sequence,
                'total_length': len(full_sequence)
            },
            'validation': validation_results,
            'generation_time': 0.5,
            'domains': generated_domains  # Include for frontend display
        }

        return result

    def _calc_cross_dimer(self, seq1: str, seq2: str) -> float:
        """Calculate cross-dimer energy between two sequences"""
        result = primer3.calc_heterodimer(seq1, seq2, mv_conc=50.0, temp_c=37.0)
        return result.dg / 1000.0

    def _calculate_full_strand_properties(self, sequence: str, global_params: Dict) -> Dict:
        """Calculate thermodynamic properties of full strand"""
        # Use global_params if provided, otherwise defaults
        mv_conc = global_params.get('salt_conc', 50.0)
        dv_conc = global_params.get('mg_conc', 0.0)
        dna_conc = global_params.get('oligo_conc', 250.0)
        temp = global_params.get('reaction_temp', 37.0)

        # Calculate properties using primer3
        tm = primer3.calc_tm(sequence, mv_conc=mv_conc, dv_conc=dv_conc, dna_conc=dna_conc)

        hairpin_result = primer3.calc_hairpin(sequence, mv_conc=mv_conc, dv_conc=dv_conc, temp_c=temp)
        hairpin_dg = hairpin_result.dg / 1000.0

        homodimer_result = primer3.calc_homodimer(sequence, mv_conc=mv_conc, dv_conc=dv_conc, temp_c=temp)
        homodimer_dg = homodimer_result.dg / 1000.0

        gc_content = (sequence.count('G') + sequence.count('C')) / len(sequence) * 100

        return {
            'melting_temp': round(tm, 2),
            'hairpin_dg': round(hairpin_dg, 2),
            'homodimer_dg': round(homodimer_dg, 2),
            'gc_content': round(gc_content, 2),
            'length': len(sequence)
        }

    def _validate_full_strand(self, sequence: str, global_params: Dict, validation_settings: Dict) -> Dict:
        """Validate only the full strand against criteria"""
        results = []
        overall_pass = True

        # Calculate strand properties
        props = self._calculate_full_strand_properties(sequence, global_params)

        # Get reaction temperature for melting temp validation
        reaction_temp = global_params.get('reaction_temp', 37.0)

        # Get validation thresholds
        melting_temp_settings = validation_settings.get('melting_temp',
                                                        {'enabled': True, 'min_offset': 5, 'max_offset': 25})
        hairpin_settings = validation_settings.get('hairpin', {'enabled': True, 'max_dg': -3.0})
        self_dimer_settings = validation_settings.get('self_dimer', {'enabled': True, 'max_dg': -6.0})
        gc_content_settings = validation_settings.get('gc_content',
                                                      {'enabled': True, 'min_percent': 40, 'max_percent': 60})

        # Melting temperature validation
        if melting_temp_settings.get('enabled'):
            tm = props['melting_temp']
            target_min = reaction_temp + melting_temp_settings.get('min_offset', 5)
            target_max = reaction_temp + melting_temp_settings.get('max_offset', 25)
            tm_pass = target_min <= tm <= target_max
            overall_pass &= tm_pass
            results.append({
                'name': 'Melting Temperature',
                'pass': tm_pass,
                'message': f"Tm = {tm}°C (target: {target_min}-{target_max}°C)"
            })

        # Hairpin validation
        if hairpin_settings.get('enabled'):
            hairpin_dg = props['hairpin_dg']
            max_dg = hairpin_settings.get('max_dg', -3.0)
            hairpin_pass = hairpin_dg > max_dg
            overall_pass &= hairpin_pass
            results.append({
                'name': 'Hairpin Formation',
                'pass': hairpin_pass,
                'message': f"ΔG = {hairpin_dg} kcal/mol (max: {max_dg})"
            })

        # Self-dimer validation
        if self_dimer_settings.get('enabled'):
            homodimer_dg = props['homodimer_dg']
            max_dg = self_dimer_settings.get('max_dg', -6.0)
            dimer_pass = homodimer_dg > max_dg
            overall_pass &= dimer_pass
            results.append({
                'name': 'Self Dimerization',
                'pass': dimer_pass,
                'message': f"ΔG = {homodimer_dg} kcal/mol (max: {max_dg})"
            })

        # GC content validation
        if gc_content_settings.get('enabled'):
            gc_content = props['gc_content']
            min_gc = gc_content_settings.get('min_percent', 40)
            max_gc = gc_content_settings.get('max_percent', 60)
            gc_pass = min_gc <= gc_content <= max_gc
            overall_pass &= gc_pass
            results.append({
                'name': 'GC Content',
                'pass': gc_pass,
                'message': f"GC = {gc_content}% (target: {min_gc}-{max_gc}%)"
            })

        return {
            'overall_pass': overall_pass,
            'results': results
        }


# Initialize generator
generator = StrandGenerator()


@app.route('/api/generate-oligonucleotide', methods=['POST'])
def generate_oligonucleotide():
    """API endpoint for generating strands from frontend requests"""
    request_data = request.get_json()
    print(f"Received generation request: {request_data}")

    result = generator.generate_strand_from_domains(request_data)
    return jsonify(result)


@app.route('/api/database-stats', methods=['GET'])
def get_database_stats():
    """Get statistics about available sequences in database"""
    total_sequences = generator.redis_client.scard('oligo:all')

    # Get length distribution
    length_dist = {}
    for key in generator.redis_client.scan_iter(match="oligo:length:*"):
        length = int(key.split(':')[-1])
        count = generator.redis_client.scard(key)
        length_dist[length] = count

    return jsonify({
        'total_sequences': total_sequences,
        'length_distribution': length_dist,
        'available_lengths': sorted(length_dist.keys())
    })


if __name__ == '__main__':
    print("Starting Strand Generator API...")
    print("Frontend can now generate strands from Redis database")
    print("API endpoints:")
    print("  POST /api/generate-oligonucleotide - Generate strand from domain specs")
    print("  GET  /api/database-stats - Get database statistics")
    app.run(debug=True, host='localhost', port=5000)