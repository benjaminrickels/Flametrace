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


FAIR_SCHED_FUNS = ['enqueue_task_fair',
                   'dequeue_task_fair',
                   'yield_task_fair',
                   'yield_to_task_fair',
                   'check_preempt_wakeup',
                   'pick_next_task_fair',
                   'put_prev_task_fair',
                   'set_next_task_fair',
                   'balance_fair',
                   'select_task_rq_fair',
                   'migrate_task_rq_fair',
                   'rq_online_fair',
                   'rq_offline_fair',
                   'task_dead_fair',
                   'task_tick_fair',
                   'task_fork_fair',
                   'prio_changed_fair',
                   'switched_from_fair',
                   'switched_to_fair',
                   'get_rr_interval_fair',
                   'update_curr_fair',
                   'task_change_group_fair',
                   'enqueue_entity',
                   '__enqueue_entity',
                   'dequeue_entity',
                   '__dequeue_entity',
                   'pick_next_entity',
                   'put_prev_entity',
                   'set_next_entity']
RT_SCHED_FUNS = ['enqueue_task_rt',
                 'dequeue_task_rt',
                 'yield_task_rt',
                 'check_preempt_curr_rt',
                 'pick_next_task_rt',
                 'put_prev_task_rt',
                 'set_next_task_rt',
                 'balance_rt',
                 'select_task_rq_rt',
                 'rq_online_rt',
                 'rq_offline_rt',
                 'task_woken_rt',
                 'switched_from_rt',
                 'task_tick_rt',
                 'get_rr_interval_rt',
                 'prio_changed_rt',
                 'switched_to_rt',
                 'update_curr_rt',
                 'rt_queue_push_tasks',
                 'rt_queue_pull_tasks',
                 'enqueue_pushable_task',
                 'dequeue_pushable_task',
                 'sched_rt_rq_enqueue',
                 'sched_rt_rq_dequeue',
                 'dequeue_top_rt_rq',
                 'enqueue_top_rt_rq',
                 '__enqueue_rt_entity',
                 '__dequeue_rt_entity',
                 'dequeue_rt_stack',
                 'enqueue_rt_entity',
                 'dequeue_rt_entity',
                 'requeue_rt_entity',
                 'requeue_task_rt',
                 'pick_next_rt_entity',
                 '_pick_next_task_rt',
                 'pick_highest_pushable_task',
                 'find_lowest_rq',
                 'find_lock_lowest_rq',
                 'pick_next_pushable_task',
                 'push_rt_task',
                 'push_rt_tasks',
                 'pull_rt_task']
SCHED_CLASS_FUNS = {'CFS': FAIR_SCHED_FUNS,
                    'RT': RT_SCHED_FUNS}


CORE_SCHED_FUNS = ['schedule',
                   '__schedule',
                   'migrate_task',
                   'pick_next_task',
                   'context_switch',
                   'try_to_wake_up',
                   'move_queued_task',
                   'scheduler_tick',
                   'resched_curr']

# Python list flattening and expanding... Yikes!
SCHED_FUNS = [*CORE_SCHED_FUNS, *[fun for funs in SCHED_CLASS_FUNS.values() for fun in funs]]


def _compute_scheduling_stats(function_stats, trace_stats):
    sched_active_time_self = 0
    for sched_fun in SCHED_FUNS:
        if fun_stats := function_stats.get(sched_fun):
            sched_active_time_self += fun_stats['active-time-self']

    cpus_active_time = trace_stats['cpus-active-time']
    sched_active_time_self_to_cpus_active_time_perc = 100 * \
        (sched_active_time_self / cpus_active_time)

    sched_funs_stats = {}
    for sched_fun in SCHED_FUNS:
        if fun_stats := function_stats.get(sched_fun):
            fun_stats = dict(fun_stats)

            active_time_self = fun_stats['active-time-self']
            active_time_self_to_sched_active_time_perc = 100 * \
                (active_time_self / sched_active_time_self)
            fun_stats['active-time-self-to-sched-active-time-perc'] = active_time_self_to_sched_active_time_perc

            sched_class = None
            for sched_class_, funs in SCHED_CLASS_FUNS.items():
                if sched_fun in funs:
                    sched_class = sched_class_
            fun_stats['sched-class'] = sched_class

            sched_funs_stats[sched_fun] = fun_stats

    sched_funs_stats_sorted = sorted(sched_funs_stats.items(),
                                     key=lambda s: s[1]['active-time-self'],
                                     reverse=True)

    return {'sched-active-time-self': sched_active_time_self,
            'sched-active-time-self-to-cpus-active-time-perc': sched_active_time_self_to_cpus_active_time_perc,
            'sched-funs-stats': sched_funs_stats_sorted}


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
    scheduling_stats = _compute_scheduling_stats(function_stats,
                                                 trace_stats)

    thread_slices = [s for s in slices if s.is_thread_slice]

    return {'function': function_stats,
            'per-call': per_call_stats,
            'scheduling': scheduling_stats,
            'thread': _compute_thread_stats(thread_slices, trace_stats),
            'trace': trace_stats}
