import re
import math
import sys
import os
import random

from vars import gvars


def is_palindrome(s):
    for i in range(len(s) // 2):
        if s[i] != s[-i - 1]:
            return False
        return True


def reverse_complement(seq):
    seq = seq[::-1]
    seq = gvars.PUNCT['EMPTYSTRING'].join([gvars.HYBRIDIZE[c] for c in seq])
    return seq

# def parse_value(kind, value):
#     """
#     Currently only considering values and not value ranges if the type
#     is `numeric`.
#     """
#     parsed = None
#     if kind == gvars.PREDICATE_TYPES["NUMERIC"]:
#         parsed = float(value)
#     elif kind == PREDICATE_TYPES["BOOLEAN"]:
#         parsed = True if value == 'true' else False
#     elif kind == PREDICATE_TYPES["STRING"]:
#         parsed = value
#     return parsed


def is_valid(s):
    return bool(re.match('^[AUTGC]+$', s.upper()))


def gc_content(seq):
    ngc = len(re.findall('G|C', seq)) / (len(seq) + 1e-9) * 100
    return ngc


def gc_count(seq):
    gcc = len(re.findall('G|C', seq))
    return gcc


def max_dinucleotide_repeats(s):
    """
    Returns:
        dict: Dinucleotide counts.
    """
    dints = [i + j for i in gvars.ALPHABET for j in gvars.ALPHABET if i != j]
    ret = 0
    for dint in dints:
        for reps in range(1, len(s)):
            if dint * reps in s:
                ret = max(ret, reps)
    return ret


def max_nucleotide_runs(s):
    """
    Returns:
        int: Maximum length of a nucleotide run.
    """
    ret = []
    for nt in gvars.ALPHABET:
        count = 0
        for i in range(len(s)):
            if s[i] == nt:
                count += 1
            else:
                if count != 0:
                    ret.append(count)
                    count = 0

        ret.append(count)
    return max(ret)


def end_hairpin_exists(s, tail=5, required_matches=3):
    """
    Args:
        s (str): Sequence of the single-stranded oligo.
    Returns:
        int: Length of the longest 3' end hairpin structure possible.
    """
    count = 0
    for i in range(tail):
        if s[i] == [s[-i - 1]]:
            count += 1
    return count >= required_matches


if __name__ == '__main__':
    print(reverse_complement('ACTG'))