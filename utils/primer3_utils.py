"""
Filename: primer3_utils.py
Author: rajiv256
Created on: 16-07-2024
"""

import os
import sys
import random
import logging
import pickle as pkl
from tqdm import tqdm
import primer3
from primer3.bindings import calc_heterodimer, calc_tm, calc_homodimer
from primer3.bindings import calc_end_stability
from primer3 import calc_hairpin
import copy
from utils import dna_utils

logging.Logger(__name__)
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)


def dimer_check(invader='', base='', dgmin=-5):
    """Checks for both homodimer and heterodimer formation by the 3' end of `s`
    over `r`.
    calculating the end stability. dG >= -9 kcal/mol is good.
    """
    # TODO: Check if the temperature is OK!
    dg = calc_end_stability(invader, base).dg / 1000
    ret = (dg >= dgmin)
    if not ret:
        logging.debug(f"Dimer check failed for invader: {invader} | base: {base}")
    return ret


# def end_hairpin_check(s, check_tail=5, max_tail_match=2, dgmin=-2):
#     """First checks if end hairpin is a possibility, i.e., the final
#     `check_tail` nucleotides have a match elsewhere in the sequence. If so,
#     requires `dg` of the hairpin to be > 0.
#     """
#     tail = s[-check_tail:]
#     rest = s[:-check_tail]
#     score = dna_utils.seq_match_score(rest, tail)
#     if score >= max_tail_match:
#         return False
#     # This shouldn't be possible.
#     # This is not rigid because if this happens, the primer will just dimerize.
#     dg = calc_hairpin(s).dg / 1000
#     if dg <= dgmin:
#         logging.debug(f"End hairpin check failed for {s}")
#         return False
#     return True


def nonspecific_binding_check(target, tsub, primer, dgmin=-4):
    """Checks every subsequence of target except the one that contains the
    target portion of the binding domain.
    """
    tgtcopy = copy.deepcopy(target).replace(tsub, '')

    # The order of arguments is correct.
    dg = calc_end_stability(primer, tgtcopy).dg / 1000
    if dg <= dgmin:
        logging.debug(f"Non specific binding check against target failed for: {primer}")
        return False
    return True


def end_stability(seq1, seq2, kwargs={}):
    """Checks how stable the 3' end of `seq1` on `seq2`.
    """
    res = calc_end_stability(seq1, seq2, **kwargs)
    return res


def melting_temp(s, kwargs={}):
    """Returns the melting temperature.
    """
    res = calc_tm(s, **kwargs)
    return res


def Tm_check(primer, Tmin=60, Tmax=65):
    """Returns `True` if none of the primers in `primers` violate the
    `has_valid_Tm(..)` check.
    Args:
        primers (str): Primer sequence.
        Tmin (float): Minimum melting temperature.
        Tmax (float): Maximum melting temperature.
    Returns:
        bool: `True` only when all the primers pass the check.
    """
    tm = melting_temp(primer)
    ret = ((tm >= Tmin) and (tm <= Tmax))
    if not ret:
        logging.debug("Tm check failed")
    return ret


def gc_check(primer, gcmin=40, gcmax=60, clampgcmin=2, clampgcmax=3,
             clampsize=5):
    """Checks if:
        - % of GC content within each primer is within `(gcmin, gcmax)`.
        - last 5 base pairs on the 3' end has 2-3 G/C nt. (GC clamps)
    Args:
        primers ([str]): Consists of all the primers.
        gcmin (float): Minimum percentage of GC content.
        gcmax (float): Maximum percentage of GC content.
    Returns:
        bool: `True` only when all the primers pass the check.
    """
    # Calculate the %GC content of the entire string.
    gc = dna_utils.gc_content(primer)
    ret = ((gc >= gcmin) and (gc <= gcmax))

    gc_clamp = dna_utils.gc_count(primer[-clampsize:])
    ret &= (gc_clamp >= clampgcmin and gc_clamp <= clampgcmax)
    if not ret:
        logging.debug("GC check failed")
    return ret


def primer_dinucleotide_repeats_check(primer, maxrepeats=3):
    """Checks if a dinucleotide occurs more than `maxrepeats` times.
    """
    ret = True
    # Obtain a `dict` of dinucleotide counts.
    d = dna_utils.max_dinucleotide_repeats(primer)
    # Check if any of them repeated more than `maxrepeats` times.
    ret = d <= maxrepeats
    if not ret:
        logging.debug("Primer dinucleotide repeats check failed")
    return ret


def primer_nucleotide_runs_check(primer, maxruns=4):
    """Checks if there are nucleotide runs in primers of length greater than
    `maxruns`.
    """
    ret = dna_utils.max_nucleotide_runs(primer) <= maxruns
    if not ret:
        logging.debug("Primer nucleotide runs check failed.")
    return ret


def primer_end_specific_binding_check(binding_domain, dgmax=-4):
    dg = end_stability(binding_domain,
                       dna_utils.reverse_complement(binding_domain)).dg / 1000
    ret = (dg <= dgmax)
    if not ret:
        logging.debug("Primer end specific binding check failed")
    return ret


def end_stability_score(bdomains, kwargs={}):
    """Calculates the `dg` of all the primers and returns the `max` of them.
    This is so that the least stable primer is as strong as possible.
    """
    dgs = [calc_end_stability(bd, dna_utils.reverse_complement(bd)).dg / 1000 for bd in bdomains]
    dgs = [round(dg, ndigits=2) for dg in dgs]
    ret = max(dgs)
    return -ret


def melting_temp_score(bdomains, kwargs={}):
    """Calculates the `tm` of all the primers and returns the `min` of them.
    This is so that the least stable primer is as strong as possible.
    """
    tms = [calc_tm(bd) for bd in bdomains]
    tms = [round(tm, ndigits=2) for tm in tms]
    ret = min(tms)
    return ret


def nonspecific_dimer_score(primers):
    dgs = []
    for p in primers:
        for q in primers:
            dg = calc_end_stability(p, q).dg / 1000
            dgs.append(dg)
    # Higher dG is better. So returning the infimum.
    return min(dgs)