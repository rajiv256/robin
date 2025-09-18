import re


def gc_filter(seq: str, min_percentage:int =40, max_percentage: int= 70):
    ngc = len(re.findall('G|C', seq))/(len(seq)+1e-9) *100
    print(ngc)
    return min_percentage <= ngc <= max_percentage