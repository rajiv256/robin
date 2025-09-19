from flask import Blueprint, request, jsonify
from dataclasses import asdict
from core.designer import OligonucleotideDesigner

api_bp = Blueprint('api', __name__)
designer = OligonucleotideDesigner()


@api_bp.route('/generate-oligonucleotide', methods=['POST'])
def generate_oligonucleotide():
    """API endpoint for oligonucleotide generation"""
    try:
        data = request.get_json()

        result = designer.design_strand(
            strand_name=data['strand_name'],
            domains=data['domains'],
            global_params=data['global_params']
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
        return jsonify({
            'success': False,
            'error_message': str(e)
        }), 500


@api_bp.route('/repository/sequences', methods=['GET'])
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


@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'oligonucleotide-designer'})