from itertools import groupby
from operator import itemgetter
from flametrace.util import flatten, groupby_sorted, max_key, thread_uid_to_id

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


def _active_time_perc(call):
    return 100 * (call.active_time / call.duration)


def _active_time_self_perc(call):
    return 100 * (call.active_time_self / call.active_time)


def _compute_per_call_stats(calls):
    STAT_GETTERS = {'begin': lambda c: c.begin,
                    'end': lambda c: c.end,
                    'duration': lambda c: c.duration,
                    'active-time': lambda c: c.active_time,
                    'active-time-perc': _active_time_perc,
                    'active-time-self': lambda c: c.active_time_self,
                    'active-time-self-perc': _active_time_self_perc,
                    'is-complete': lambda c: c.is_complete,
                    'id': lambda c: c.id,
                    'name': lambda c: c.name,
                    'thread_uid': lambda c: c.thread_uid}

    per_call_stats = []

    for c in calls:
        call_stats = {k: f(c) for k, f in STAT_GETTERS.items()}
        per_call_stats.append(call_stats)

    return per_call_stats


def _compute_function_stats(per_call_stats, trace_stats):
    per_call_stats = [pcs for pcs in per_call_stats if pcs['is-complete']]
    per_call_stats_by_name = groupby_sorted(per_call_stats, key=itemgetter('name'))

    function_stats = {}

    for function_name, pcss in per_call_stats_by_name.items():
        count = len(pcss)
        durations = list(sorted(map(lambda s: s['duration'], pcss)))
        duration = sum(durations)
        active_times = list(sorted(map(lambda s: s['active-time'], pcss)))
        active_time = sum(active_times)
        active_time_percs = list(
            sorted(map(lambda s: 100 * (s['active-time'] / s['duration']), pcss)))
        active_times_self = list(sorted(map(lambda s: s['active-time-self'], pcss)))
        active_time_self = sum(active_times_self)
        active_time_self_percs = list(
            sorted(map(lambda s: 100 * (s['active-time-self'] / s['active-time']), pcss)))

        cpus_active_time = trace_stats['cpus-active-time']
        active_time_to_cpus_active_time_perc = 100 * (active_time / cpus_active_time)
        active_time_self_to_cpus_active_time_perc = 100 * (active_time_self / cpus_active_time)

        function_stats[function_name] = {'count': count,
                                         'duration': duration,
                                         'duration-iqr': _quartile_stats(durations),
                                         'active-time': active_time,
                                         'active-time-iqr': _quartile_stats(active_times),
                                         'active-time-perc-iqr': _quartile_stats(active_time_percs),
                                         'active-time-self': active_time_self,
                                         'active-time-self-iqr': _quartile_stats(active_times_self),
                                         'active-time-self-perc-iqr': _quartile_stats(active_time_self_percs),
                                         'active-time-to-cpus-active-time': active_time_to_cpus_active_time_perc,
                                         'active-time-self-to-cpus-active-time': active_time_self_to_cpus_active_time_perc}

    return function_stats


def _compute_thread_stats(thread_slices, trace_stats):
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

        total_cpu_time = trace_stats['total-cpu-time']
        active_time_to_total_cpu_time_perc = 100 * (active_time / total_cpu_time)

        if thread_uid_to_id(thread_uid) != 0:
            cpus_active_time = trace_stats['cpus-active-time']
            active_time_to_cpus_active_time_perc = 100 * (active_time / cpus_active_time)
        else:
            active_time_to_cpus_active_time_perc = 'N/A'

        thread_stats[thread_uid] = {'begin': begin,
                                    'end': end,
                                    'duration': duration,
                                    'active_time': active_time,
                                    'active_time_perc': active_perc,
                                    'active-time-to-total-cpu-time-perc': active_time_to_total_cpu_time_perc,
                                    'active-time-to-cpus-active-time_perc': active_time_to_cpus_active_time_perc,
                                    'migrations': migrations,
                                    'slice_duration_quartiles': slice_duration_quartiles}

    return thread_stats


def _is_non_swapper_thread_slice(slce):
    return slce.is_thread_slice and thread_uid_to_id(slce.thread_uid) != 0


def _is_swapper_depth0_slice(slce):
    return thread_uid_to_id(slce.thread_uid) == 0 and slce.call_depth_or(-1) == 0


def _compute_trace_stats(slices):
    trace_begin = slices[0].begin
    trace_end = max_key(slices, key=lambda s: s.end)
    trace_duration = trace_end - trace_begin
    slices_by_cpu_id = groupby_sorted(slices, key=lambda s: s.cpu_id)
    no_cpus = len(slices_by_cpu_id.keys())
    total_cpu_time = trace_duration * no_cpus

    cpus_active_time = 0
    cpu_statss = {}
    for cpu_id, cpu_slices in slices_by_cpu_id.items():
        cpu_active_time = sum(map(lambda s: s.duration,
                                  filter(lambda s: _is_non_swapper_thread_slice(s) or _is_swapper_depth0_slice(s),
                                         cpu_slices)))
        cpu_active_time_perc = 100 * (cpu_active_time / trace_duration)
        cpus_active_time += cpu_active_time

        cpu_statss[cpu_id] = {'cpu-active-time': cpu_active_time,
                              'cpu-active-time-perc': cpu_active_time_perc}

    cpus_active_time_perc = 100 * (cpus_active_time / total_cpu_time)

    stats = {'no-cpus': no_cpus,
             'trace-begin': trace_begin,
             'trace-end': trace_end,
             'trace-duration': trace_duration,
             'total-cpu-time': total_cpu_time,
             'cpus-active-time': cpus_active_time,
             'cpus-active-time-perc': cpus_active_time_perc}

    for cpu_id, cpu_stats in cpu_statss.items():
        stats[f'cpu-{cpu_id}-stats'] = cpu_stats

    return stats


def compute_stats(slices):
    call_slices = [s for s in slices if s.is_call_slice]
    calls_ = calls.all_from_slices(call_slices)

    per_call_stats = _compute_per_call_stats(calls_)
    trace_stats = _compute_trace_stats(slices)
    function_stats = _compute_function_stats(per_call_stats, trace_stats)

    thread_slices = [s for s in slices if s.is_thread_slice]

    return {'function': function_stats,
            'per-call': per_call_stats,
            'thread': _compute_thread_stats(thread_slices, trace_stats),
            'trace': trace_stats}
