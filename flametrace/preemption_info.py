from bisect import bisect_left, bisect_right
from operator import itemgetter

import flametrace.trace_entry as trace_entry
from flametrace.util import groupby_sorted


def _trace_entries_by_cpu_cached(trace_entries):
    _this = _trace_entries_by_cpu_cached
    if not hasattr(_this, '_trace_entries_by_cpu'):
        _this._trace_entries_by_cpu = groupby_sorted(trace_entries, key=itemgetter('cpu_id'))

    return _this._trace_entries_by_cpu


def _preemption_context(t_entry, trace_entries):
    cpu_id = trace_entry.cpu_id(t_entry)
    trace_entries_by_cpu = _trace_entries_by_cpu_cached(trace_entries)
    cpu_trace_entries = trace_entries_by_cpu[cpu_id]
    timestamps = list(map(itemgetter('timestamp'), cpu_trace_entries))
    return (trace_entry.timestamp(t_entry), cpu_trace_entries, timestamps)


def find_preempted(trace_entry, trace_entries):
    '''Find the entry in `trace_entries` that was preempted by the given `trace_entry`'''
    timestamp, cpu_trace_entries, timestamps = _preemption_context(trace_entry, trace_entries)
    i = bisect_left(timestamps, timestamp)
    return cpu_trace_entries[i-1] if i else None


def find_preempting(trace_entry, trace_entries):
    '''Find the entry in `trace_entries` that is preempting the given `trace_entry`'''
    timestamp, cpu_trace_entries, timestamps = _preemption_context(trace_entry, trace_entries)
    i = bisect_right(timestamps, timestamp)
    return cpu_trace_entries[i] if i < len(cpu_trace_entries) else None
