from itertools import groupby
from flametrace.config import CPU_GHZ


def flatten(l):
    return [item for sublist in l for item in sublist]


def groupby_sorted(coll, key=None, sort_key=None, group_key=None):
    return dict([(k, list(vs)) for k, vs in groupby(sorted(coll, key=sort_key or key),
                                                    key=group_key or key)])


def ps_to_cycles(ps):
    return CPU_GHZ * (ps / 1000)


def cycles_to_ps(cycles):
    return (cycles * 1000) / CPU_GHZ
