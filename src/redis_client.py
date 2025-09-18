import redis
import json
from typing import Dict, List, Optional, Union
from utils import dna_utils
import re


class RedisClient:
    def __init__(self, host: str = 'localhost', port: int = 6379, decode_responses=True):
        if not hasattr(self, 'client'):
            self.client = redis.Redis(host=host, port=port, decode_responses=decode_responses)

    def add_entry(self, key: str, sequence: str):
        """Add a DNA sequence with computed attributes to Redis"""
        if not dna_utils.is_valid(sequence):
            raise ValueError("Invalid DNA sequence. Only A, T, G, C characters allowed.")

        attributes = self.compute_attributes(sequence)
        self.client.set(key, json.dumps(attributes))
        return attributes

    def delete_entry(self, key: str) -> bool:
        """Delete an entry"""
        return bool(self.client.delete(key))

    def search_by_attribute(self, attribute: str, value: Union[str, int, float],
                            operator: str = 'eq') -> List[str]:
        """Search entries by attribute value"""
        matching_keys = []

        for key in self.client.scan_iter():
            data = self.client.get(key)
            print(data)
            if data:
                entry = json.loads(data)
                if attribute in entry:
                    attr_value = entry[attribute]

                    if operator == 'eq' and attr_value == value:
                        matching_keys.append(key)
                    elif operator == 'gt' and attr_value > value:
                        matching_keys.append(key)
                    elif operator == 'lt' and attr_value < value:
                        matching_keys.append(key)
                    elif operator == 'gte' and attr_value >= value:
                        matching_keys.append(key)
                    elif operator == 'lte' and attr_value <= value:
                        matching_keys.append(key)

        return matching_keys

    def flush(self):
        """Clear all entries"""
        self.client.flushdb()

    def compute_attributes(self, sequence: str) -> Dict:
        """Compute DNA sequence attributes"""
        sequence = sequence.upper()
        length = len(sequence)

        # Count G and C nucleotides
        g_count = sequence.count('G')
        c_count = sequence.count('C')

        # GC content
        gc_content = (g_count + c_count) / length * 100 if length > 0 else 0

        # Melting temperature calculation
        melting_point = self._calculate_tm(sequence)

        return {
            'sequence': sequence,
            'length': length,
            'gc_content': round(gc_content, 2),
            'melting_point': round(melting_point, 2)
        }

    def _calculate_tm(self, sequence: str) -> float:
        """Calculate melting temperature"""
        length = len(sequence)

        if length < 14:
            # Simple formula for short sequences
            return (sequence.count('A') + sequence.count('T')) * 2 + \
                (sequence.count('G') + sequence.count('C')) * 4
        else:
            # Formula for longer sequences
            gc_count = sequence.count('G') + sequence.count('C')
            return 64.9 + 41 * (gc_count - 16.4) / length


# Example usage
if __name__ == "__main__":
    db = RedisClient()

    db.flush()
    # Add some sequences
    db.add_entry('seq1', 'ATGCGCTAGCTAG')
    db.add_entry('seq2', 'GCTAGCTAGCTAG')
    db.add_entry('seq3', 'ATATATATATATA')

    # Search by GC content
    high_gc = db.search_by_attribute('gc_content', 50, 'gt')
    print(f"High GC sequences: {high_gc}")

    # Search by melting point
    stable_seqs = db.search_by_attribute('melting_point', 40, 'gte')
    print(f"Stable sequences (Tm >= 40): {stable_seqs}")