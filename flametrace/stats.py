from operator import itemgetter
from flametrace.util import groupby_sorted, ps_to_cycles

import flametrace.exec_slice as exec_slice


def _halve(xs):
    n = len(xs)

    if n <= 1:
        return ([], [])

    hn = int(n / 2)

    xs_low = xs[0:hn]
    xs_high = xs[hn:n] if n % 2 == 0 else xs[hn + 1:n]

    return (xs_low, xs_high)


def _median(xs, default=None):
    n = len(xs)

    if n == 0:
        return default

    hn = int(n / 2)

    median = xs[hn]
    return median if n % 2 != 0 else (median + xs[hn - 1]) / 2


def _boxplot_stats(runtimes):
    min = runtimes[0]
    max = runtimes[-1]

    median = q2 = _median(runtimes)
    xs_low, xs_high = _halve(runtimes)
    q1 = _median(xs_low, q2)
    q3 = _median(xs_high, q2)
    iqr = q3 - q1

    filtered_rts = [x for x in runtimes if x >= (q1 - iqr) and (x <= q3 + iqr)]
    q0 = filtered_rts[0]
    q4 = filtered_rts[-1]

    return {'median': ps_to_cycles(median),
            'min': ps_to_cycles(min),
            'max': ps_to_cycles(max),
            'q0': ps_to_cycles(q0),
            'q1': ps_to_cycles(q1),
            'q2': ps_to_cycles(q2),
            'q3': ps_to_cycles(q3),
            'q4': ps_to_cycles(q4),
            'iqr': ps_to_cycles(iqr)}


def _get_call_rt(call_slices):
    has_begin = has_end = False
    rt = 0

    for cs in call_slices:
        rt += exec_slice.duration(cs)
        has_begin = has_begin or ('is_begin' in cs)
        has_end = has_end or ('is_end' in cs)

    return rt if has_begin and has_end else None


def _insert_function_runtime(fun_rts, fun_name, rt):
    if not fun_name in fun_rts:
        fun_rts[fun_name] = []

    fun_rts[fun_name].append(rt)


def _get_functions_runtimes(slices_by_call_id):
    fun_rts = {}

    for _, call_slices in slices_by_call_id.items():
        if rt := _get_call_rt(call_slices):
            fun_name = call_slices[0]['function_name']
            _insert_function_runtime(fun_rts, fun_name, rt)

    return fun_rts


def _get_functions_stats(function_runtimes):
    fun_stats = {}

    for fun_name, runtimes in function_runtimes.items():
        runtimes = sorted(runtimes)

        count = len(runtimes)
        total = sum(runtimes)

        boxplot_stats = _boxplot_stats(runtimes)

        fun_stats[fun_name] = {'count': count,
                               'total': ps_to_cycles(total),
                               **boxplot_stats}

    return fun_stats


def stringify_function_stats(fun_stats):
    str_stats = []

    for fun_name, stats in fun_stats.items():
        count = stats['count']
        total = stats['total']

        median = stats['median']
        min = stats['min']
        max = stats['max']
        q0 = stats['q0']
        q1 = stats['q1']
        q3 = stats['q3']
        q4 = stats['q4']
        iqr = stats['iqr']

        stats_str = (f'{fun_name}:\n'
                     f'  Count:  {count}\n'
                     f'  Min:    {min}\n'
                     f'  Q0:     {q0}\n'
                     f'  Q1:     {q1}\n'
                     f'  Median: {median}\n'
                     f'  Q3:     {q3}\n'
                     f'  Q4:     {q4}\n'
                     f'  Max:    {max}\n'
                     f'  IQR:    {iqr}\n'
                     f'  Total:  {total}\n\n')

        str_stats.append(stats_str)

    return ''.join(str_stats)


def get_function_stats(slices):
    fun_slices = [x for x in slices if x['type'] == 'function_slice']
    slices_by_call_id = groupby_sorted(fun_slices, key=itemgetter('call_id'))

    fun_rts = _get_functions_runtimes(slices_by_call_id)
    fun_stats = _get_functions_stats(fun_rts)

    return fun_stats
