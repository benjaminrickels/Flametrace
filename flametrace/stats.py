from itertools import groupby
from operator import itemgetter
from flametrace.util import groupby_sorted

import flametrace.calls as calls


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


def _quartile_stats(xs):
    min = xs[0]
    max = xs[-1]

    median = q2 = _median(xs)
    xs_low, xs_high = _halve(xs)
    q1 = _median(xs_low, q2)
    q3 = _median(xs_high, q2)
    iqr = q3 - q1

    filtered_xs = [x for x in xs if x >= (q1 - 1.5*iqr) and (x <= q3 + 1.5*iqr)]
    q0 = filtered_xs[0]
    q4 = filtered_xs[-1]

    return {'median': median,
            'min': min,
            'max': max,
            'q0': q0,
            'q1': q1,
            'q2': q2,
            'q3': q3,
            'q4': q4,
            'iqr': iqr}


def _compute_per_call_stats(calls):
    STAT_GETTERS = [('begin', lambda c: c.begin),
                    ('end', lambda c: c.end),
                    ('duration', lambda c: c.duration),
                    ('active_time', lambda c: c.active_time),
                    ('active_perc', lambda c: 100 * (c.active_time / c.duration)),
                    ('is_complete', lambda c: c.is_complete),
                    ('id', lambda c: c.id),
                    ('name', lambda c: c.name),
                    ('thread_uid', lambda c: c.thread_uid)]

    calls_by_id = {c.id: c for c in calls}

    per_call_stats = []

    for c in calls:
        call_stats = {k: f(c) for k, f in STAT_GETTERS}
        duration = c.duration

        child_durations = [calls_by_id[ch].duration for ch in c.children]
        children_duration = sum(child_durations)

        call_stats['children_duration'] = children_duration
        if duration:
            call_stats['children_duration_perc'] = 100 * (children_duration / duration)

        if parent := c.parent:
            parent_duration = calls_by_id[parent].duration

            call_stats['parent_duration'] = parent_duration
            call_stats['parent_duration_perc'] = 100 * (duration / parent_duration)

        per_call_stats.append(call_stats)

    return per_call_stats


def _compute_function_stats(per_call_stats):
    per_call_stats = [pcs for pcs in per_call_stats if pcs['is_complete']]
    per_call_stats_by_name = groupby_sorted(per_call_stats, key=itemgetter('name'))

    function_stats = {}

    for function_name, pcss in per_call_stats_by_name.items():
        durations = sorted([pcs['duration'] for pcs in pcss])
        children_durations = [pcs['children_duration'] for pcs in pcss]

        children_percs = sorted([100 * (pcs['children_duration'] / pcs['duration'])
                                 for pcs in pcss])

        total = sum(durations)

        function_stats[function_name] = {'count': len(pcss),
                                         'total': total,
                                         'children_perc': 100 * (sum(children_durations) / total),
                                         'duration_quartiles': _quartile_stats(durations),
                                         'children_perc_quartiles': _quartile_stats(children_percs)}

    return function_stats


def _compute_thread_stats(thread_slices):
    thread_slices_by_thread_uid = groupby_sorted(thread_slices,
                                                 key=lambda s: str(s.thread_uid))

    thread_stats = {}

    for thread_uid, slices in thread_slices_by_thread_uid.items():
        begin = slices[0].begin
        end = slices[-1].end
        duration = end - begin
        slice_durations = sorted([s.duration for s in slices])

        slices_by_cpu_id = groupby(slices, lambda s: s.cpu_id)
        migrations = len(dict(slices_by_cpu_id).keys()) - 1

        active_time = sum(slice_durations)
        active_perc = 100 * (active_time / duration)

        slice_duration_quartiles = _quartile_stats(slice_durations)

        thread_stats[thread_uid] = {'begin': begin,
                                    'end': end,
                                    'duration': duration,
                                    'active_time': active_time,
                                    'active_perc': active_perc,
                                    'migrations': migrations,
                                    'slice_duration_quartiles': slice_duration_quartiles}

    return thread_stats


def compute_stats(slices):
    call_slices = [s for s in slices if s.is_call_slice]
    calls_ = calls.all_from_slices(call_slices)

    per_call_stats = _compute_per_call_stats(calls_)

    thread_slices = [s for s in slices if s.is_thread_slice]

    return {'per_call_stats': per_call_stats,
            'function_stats': _compute_function_stats(per_call_stats),
            'thread_stats': _compute_thread_stats(thread_slices)}
