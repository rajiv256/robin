#!/usr/bin/env python3
"""
Oligonucleotide Redis Database Loader
Reads oligos from file and stores them in Redis with calculated properties using primer3
"""

import redis
import json
import hashlib
from typing import Dict, List, Optional
import re
import numpy as np
import primer3


class ThermodynamicCalculator:
    """Calculate thermodynamic properties using primer3"""

    def __init__(self, mv_conc: float = 50.0, dv_conc: float = 0.0, dntp_conc: float = 0.0,
                 dna_conc: float = 250.0, temp_c: float = 37.0):
        """
        Initialize thermodynamic calculator with reaction conditions

        Args:
            mv_conc: Monovalent cation concentration (mM)
            dv_conc: Divalent cation concentration (mM)
            dntp_conc: dNTP concentration (mM)
            dna_conc: DNA concentration (nM)
            temp_c: Temperature in Celsius
        """
        self.mv_conc = mv_conc
        self.dv_conc = dv_conc
        self.dntp_conc = dntp_conc
        self.dna_conc = dna_conc
        self.temp_c = temp_c

    def calculate_tm(self, sequence: str) -> float:
        """Calculate melting temperature using primer3"""
        if len(sequence) < 2:
            return 0.0

        tm = primer3.calc_tm(
            sequence,
            mv_conc=self.mv_conc,
            dv_conc=self.dv_conc,
            dntp_conc=self.dntp_conc,
            dna_conc=self.dna_conc
        )
        return round(tm, 2)

    def calculate_hairpin_dg(self, sequence: str) -> float:
        """Calculate hairpin formation ΔG using primer3"""
        result = primer3.calc_hairpin(
            sequence,
            mv_conc=self.mv_conc,
            dv_conc=self.dv_conc,
            dntp_conc=self.dntp_conc,
            temp_c=self.temp_c
        )
        return round(result.dg / 1000.0, 2)  # Convert cal/mol to kcal/mol

    def calculate_homodimer_dg(self, sequence: str) -> float:
        """Calculate homodimer (self-dimer) formation ΔG using primer3"""
        result = primer3.calc_homodimer(
            sequence,
            mv_conc=self.mv_conc,
            dv_conc=self.dv_conc,
            dntp_conc=self.dntp_conc,
            temp_c=self.temp_c
        )
        return round(result.dg / 1000.0, 2)  # Convert cal/mol to kcal/mol

    def calculate_heterodimer_dg(self, seq1: str, seq2: str) -> float:
        """Calculate heterodimer formation ΔG between two sequences"""
        result = primer3.calc_heterodimer(
            seq1, seq2,
            mv_conc=self.mv_conc,
            dv_conc=self.dv_conc,
            dntp_conc=self.dntp_conc,
            temp_c=self.temp_c
        )
        return round(result.dg / 1000.0, 2)  # Convert cal/mol to kcal/mol

    def calculate_end_stability(self, sequence: str, length: int = 5) -> float:
        """Calculate 3' end stability (ΔG of last few bases)"""
        if len(sequence) < length:
            return 0.0

        end_seq = sequence[-length:]
        result = primer3.calc_hairpin(
            end_seq,
            mv_conc=self.mv_conc,
            dv_conc=self.dv_conc,
            dntp_conc=self.dntp_conc,
            temp_c=self.temp_c
        )
        return round(result.dg / 1000.0, 2)


class OligoAnalyzer:
    """Analyze oligonucleotide sequences and calculate properties"""

    def calculate_gc_content(self, sequence: str) -> float:
        """Calculate GC content as percentage"""
        seq = sequence.upper()
        gc_count = seq.count('G') + seq.count('C')
        return (gc_count / len(seq)) * 100 if seq else 0.0

    def find_repeats(self, sequence: str, min_length: int = 3) -> List[Dict]:
        """Find repetitive sequences"""
        seq = sequence.upper()
        repeats = []

        for length in range(min_length, len(seq) // 2 + 1):
            for i in range(len(seq) - length + 1):
                pattern = seq[i:i + length]
                count = 1
                j = i + length

                # Count consecutive repeats
                while j + length <= len(seq) and seq[j:j + length] == pattern:
                    count += 1
                    j += length

                if count > 1:
                    repeats.append({
                        'pattern': pattern,
                        'count': count,
                        'start': i,
                        'total_length': count * length
                    })

        return repeats

    def calculate_complexity(self, sequence: str) -> float:
        """Calculate sequence complexity (Shannon entropy)"""
        seq = sequence.upper()
        if not seq:
            return 0.0

        # Calculate base frequencies
        bases = ['A', 'T', 'G', 'C']
        freqs = [seq.count(base) / len(seq) for base in bases]

        # Calculate Shannon entropy
        entropy = -sum(f * np.log2(f) for f in freqs if f > 0)
        return entropy / 2.0  # Normalize to 0-1 scale

    def analyze_sequence(self, sequence: str, seq_id: str = None,
                         mv_conc: float = 50.0, dv_conc: float = 0.0,
                         dna_conc: float = 250.0, temp_c: float = 37.0) -> Dict:
        """Comprehensive sequence analysis using primer3"""
        if not sequence or not re.match(r'^[ATGC]+$', sequence.upper()):
            raise ValueError(f"Invalid sequence: {sequence}")

        seq = sequence.upper()
        seq_id = seq_id or hashlib.md5(seq.encode()).hexdigest()[:8]

        # Initialize thermodynamic calculator with specified conditions
        thermo_calc = ThermodynamicCalculator(
            mv_conc=mv_conc, dv_conc=dv_conc,
            dna_conc=dna_conc, temp_c=temp_c
        )

        # Basic properties
        length = len(seq)
        gc_content = self.calculate_gc_content(seq)
        complexity = self.calculate_complexity(seq)

        # Thermodynamic properties using primer3
        tm = thermo_calc.calculate_tm(seq)
        hairpin_dg = thermo_calc.calculate_hairpin_dg(seq)
        homodimer_dg = thermo_calc.calculate_homodimer_dg(seq)
        end_stability = thermo_calc.calculate_end_stability(seq)

        # Sequence features
        repeats = self.find_repeats(seq)
        has_repeats = len(repeats) > 0
        max_repeat_length = max([r['total_length'] for r in repeats], default=0)

        # Terminal stability
        terminal_gc = (seq[0] in 'GC') + (seq[-1] in 'GC') if length > 0 else 0

        # Analysis results
        analysis = {
            'sequence_id': seq_id,
            'sequence': seq,
            'length': length,
            'gc_content': round(gc_content, 2),
            'complexity': round(complexity, 3),

            # Thermodynamic properties (primer3)
            'melting_temp': tm,
            'hairpin_dg': hairpin_dg,
            'homodimer_dg': homodimer_dg,
            'end_stability_dg': end_stability,

            # Reaction conditions used
            'mv_conc': mv_conc,
            'dv_conc': dv_conc,
            'dna_conc': dna_conc,
            'temp_c': temp_c,

            # Sequence features
            'has_repeats': has_repeats,
            'max_repeat_length': max_repeat_length,
            'repeats': repeats,
            'terminal_gc_count': terminal_gc,
            'purine_content': round((seq.count('A') + seq.count('G')) / length * 100, 2) if length > 0 else 0,
            'pyrimidine_content': round((seq.count('T') + seq.count('C')) / length * 100, 2) if length > 0 else 0,

            # Additional metrics
            'at_content': round(100 - gc_content, 2)
        }

        return analysis


class OligoRedisManager:
    """Manage oligonucleotide data in Redis"""

    def __init__(self, host='localhost', port=6379, db=0, password=None):
        """Initialize Redis connection"""
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True
        )
        self.analyzer = OligoAnalyzer()

        # Test connection
        try:
            self.redis_client.ping()
            print(f"Connected to Redis at {host}:{port}")
        except redis.ConnectionError:
            raise ConnectionError(f"Could not connect to Redis at {host}:{port}")

    def load_oligos_from_file(self, filepath: str, mv_conc: float = 50.0,
                              dv_conc: float = 0.0, dna_conc: float = 250.0,
                              temp_c: float = 37.0) -> int:
        """Load oligonucleotides from file and store in Redis with specified conditions"""
        try:
            with open(filepath, 'r') as f:
                sequences = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {filepath}")

        print(f"Reading {len(sequences)} sequences from {filepath}")
        print(f"Using primer3 with conditions: {mv_conc}mM Na+, {dv_conc}mM Mg2+, {dna_conc}nM DNA, {temp_c}°C")

        loaded_count = 0
        failed_count = 0

        for i, sequence in enumerate(sequences):
            try:
                # Analyze sequence with specified conditions
                analysis = self.analyzer.analyze_sequence(
                    sequence,
                    mv_conc=mv_conc,
                    dv_conc=dv_conc,
                    dna_conc=dna_conc,
                    temp_c=temp_c
                )
                seq_id = analysis['sequence_id']

                # Store in Redis
                self._store_oligo(seq_id, analysis)
                loaded_count += 1

                if (i + 1) % 50 == 0:
                    print(f"Processed {i + 1}/{len(sequences)} sequences...")

            except Exception as e:
                print(f"Failed to process sequence '{sequence}': {e}")
                failed_count += 1

        print(f"Successfully loaded {loaded_count} oligonucleotides")
        if failed_count > 0:
            print(f"Failed to load {failed_count} sequences")

        # Store metadata
        self._store_metadata(loaded_count, failed_count, mv_conc, dv_conc, dna_conc, temp_c)

        return loaded_count

    def _store_oligo(self, seq_id: str, analysis: Dict):
        """Store oligonucleotide analysis in Redis"""
        # Store main data as JSON
        self.redis_client.hset(f"oligo:{seq_id}", mapping={
            'data': json.dumps(analysis),
            'sequence': analysis['sequence'],
            'length': analysis['length'],
            'gc_content': analysis['gc_content'],
            'melting_temp': analysis['melting_temp'],
            'hairpin_dg': analysis['hairpin_dg'],
            'homodimer_dg': analysis['homodimer_dg'],
            'end_stability_dg': analysis['end_stability_dg']
        })

        # Add to indices for efficient querying
        self.redis_client.sadd('oligo:all', seq_id)
        self.redis_client.sadd(f"oligo:length:{analysis['length']}", seq_id)

        # GC content ranges
        gc_range = f"{int(analysis['gc_content'] // 10) * 10}-{int(analysis['gc_content'] // 10) * 10 + 9}"
        self.redis_client.sadd(f"oligo:gc_range:{gc_range}", seq_id)

        # Temperature ranges
        tm_range = f"{int(analysis['melting_temp'] // 10) * 10}-{int(analysis['melting_temp'] // 10) * 10 + 9}"
        self.redis_client.sadd(f"oligo:tm_range:{tm_range}", seq_id)

    def _store_metadata(self, loaded_count: int, failed_count: int,
                        mv_conc: float, dv_conc: float, dna_conc: float, temp_c: float):
        """Store database metadata including reaction conditions"""
        import datetime
        metadata = {
            'total_oligos': loaded_count,
            'failed_count': failed_count,
            'last_updated': datetime.datetime.now().isoformat(),
            'version': '1.0',
            'conditions': {
                'mv_conc_mM': mv_conc,
                'dv_conc_mM': dv_conc,
                'dna_conc_nM': dna_conc,
                'temp_c': temp_c
            }
        }
        self.redis_client.hset('oligo:metadata', mapping={
            k: json.dumps(v) if isinstance(v, dict) else str(v)
            for k, v in metadata.items()
        })

    def get_oligo(self, seq_id: str) -> Optional[Dict]:
        """Retrieve oligonucleotide data"""
        data = self.redis_client.hget(f"oligo:{seq_id}", 'data')
        if data:
            return json.loads(data)
        return None

    def search_oligos(self, **criteria) -> List[str]:
        """Search oligonucleotides by criteria"""
        # Start with all oligos
        result_set = 'oligo:all'

        # Apply filters
        if 'length' in criteria:
            length_set = f"oligo:length:{criteria['length']}"
            result_set = self._intersect_sets([result_set, length_set])

        if 'gc_range' in criteria:
            gc_set = f"oligo:gc_range:{criteria['gc_range']}"
            result_set = self._intersect_sets([result_set, gc_set])

        if 'tm_range' in criteria:
            tm_set = f"oligo:tm_range:{criteria['tm_range']}"
            result_set = self._intersect_sets([result_set, tm_set])

        return list(self.redis_client.smembers(result_set))

    def _intersect_sets(self, sets: List[str]) -> str:
        """Intersect multiple Redis sets"""
        if len(sets) == 1:
            return sets[0]

        temp_key = f"temp:intersect:{np.random.randint(10000)}"
        self.redis_client.sinterstore(temp_key, *sets)
        self.redis_client.expire(temp_key, 60)  # Expire in 60 seconds
        return temp_key

    def get_statistics(self) -> Dict:
        """Get database statistics"""
        metadata = self.redis_client.hgetall('oligo:metadata')

        # Length distribution
        length_dist = {}
        for key in self.redis_client.scan_iter(match="oligo:length:*"):
            length = key.split(':')[-1]
            count = self.redis_client.scard(key)
            length_dist[int(length)] = count

        return {
            'metadata': metadata,
            'length_distribution': dict(sorted(length_dist.items())),
            'total_sequences': self.redis_client.scard('oligo:all')
        }


def main():
    """Main function to load oligonucleotides into Redis"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Load oligonucleotides into Redis database with primer3 thermodynamics')
    parser.add_argument('--file', '-f', default='data/oligos.txt',
                        help='Path to oligonucleotides file')
    parser.add_argument('--host', default='localhost', help='Redis host')
    parser.add_argument('--port', type=int, default=6379, help='Redis port')
    parser.add_argument('--db', type=int, default=0, help='Redis database number')
    parser.add_argument('--password', help='Redis password')
    parser.add_argument('--stats', action='store_true', help='Show statistics after loading')

    # Thermodynamic condition arguments
    parser.add_argument('--mv-conc', type=float, default=50.0,
                        help='Monovalent cation concentration (mM), default: 50.0')
    parser.add_argument('--dv-conc', type=float, default=0.0,
                        help='Divalent cation concentration (mM), default: 0.0')
    parser.add_argument('--dna-conc', type=float, default=250.0,
                        help='DNA concentration (nM), default: 250.0')
    parser.add_argument('--temp', type=float, default=37.0,
                        help='Temperature (°C), default: 37.0')

    args = parser.parse_args()

    # Initialize Redis manager
    try:
        manager = OligoRedisManager(
            host=args.host,
            port=args.port,
            db=args.db,
            password=args.password
        )

        # Load oligonucleotides with specified conditions
        count = manager.load_oligos_from_file(
            args.file,
            mv_conc=args.mv_conc,
            dv_conc=args.dv_conc,
            dna_conc=args.dna_conc,
            temp_c=args.temp
        )

        if args.stats:
            print("\nDatabase Statistics:")
            stats = manager.get_statistics()
            print(f"Total sequences: {stats['total_sequences']}")
            print(f"Length distribution: {stats['length_distribution']}")

            # Show some example data
            if count > 0:
                all_ids = list(manager.redis_client.smembers('oligo:all'))
                if all_ids:
                    example_id = all_ids[0]
                    example_data = manager.get_oligo(example_id)
                    print(f"\nExample oligo ({example_id}):")
                    print(f"  Sequence: {example_data['sequence']}")
                    print(f"  Length: {example_data['length']}")
                    print(f"  GC%: {example_data['gc_content']}")
                    print(f"  Tm: {example_data['melting_temp']}°C")
                    print(f"  Hairpin ΔG: {example_data['hairpin_dg']} kcal/mol")
                    print(f"  Homodimer ΔG: {example_data['homodimer_dg']} kcal/mol")

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())