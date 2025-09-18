import random
import re
from vars.gvars import PUNCT, ALPHABET
import yaml
from yaml import Loader, CLoader
import random


def generate_random_string(**kwargs):
    def __shuffle(string):
        lst = [c for c in string]
        random.shuffle(lst)
        return PUNCT['EMPTY'].join(lst)

    # Assign length of the string
    assert "length" in kwargs
    length = kwargs["length"]

    # Assign the alphabet
    alphabet = kwargs["alphabet"] if "alphabet" in kwargs else ALPHABET

    # Collect the bases that need to be used and their number
    bps = kwargs['base_percentages']
    assert len(bps.keys()) == len(ALPHABET)
    assert sum(bps.values()) == 100
    s = [c * int((length * (bps[c] if c in bps else 0)) // 100) for c in \
         alphabet]
    s = PUNCT['EMPTY'].join(s)
    # Randomize
    s = __shuffle(s)
    return s


if __name__ == "__main__":
    config = yaml.load(open('../config.yaml', "r"), Loader=Loader)
    print(config)
    print(generate_random_string(**config))