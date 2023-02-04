from itertools import groupby
import flametrace.config as config


def flatten(l):
    return [item for sublist in l for item in sublist]


def groupby_sorted(coll, key=None, sort_key=None, group_key=None):
    return dict([(k, list(vs)) for k, vs in groupby(sorted(coll, key=sort_key or key),
                                                    key=group_key or key)])


def min_key(coll, key):
    return key(min(coll, key=key))


def max_key(coll, key):
    return key(max(coll, key=key))


def ps_to_cycles(ps):
    return config.CPU_GHZ * (ps / 1000)


def cycles_to_ps(cycles):
    return (cycles * 1000) / config.CPU_GHZ


def thread_uid_to_id(thread_uid):
    if isinstance(thread_uid, str):
        return 0
    else:
        return thread_uid
