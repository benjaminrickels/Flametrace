from itertools import groupby


def flatten(l):
    return [item for sublist in l for item in sublist]


def groupby_sorted(coll, key=None, sort_key=None, group_key=None):
    return dict([(k, list(vs)) for k, vs in groupby(sorted(coll, key=sort_key or key),
                                                    key=group_key or key)])
