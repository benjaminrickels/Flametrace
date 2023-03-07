from itertools import dropwhile
from flametrace.trace_event import TraceEvent


def _with_thread_names(trace_events):
    curr_thread_name_map = {}
    first_name_map = {}
    unnamed_entries = []

    def try_set_name(te, name_map):
        if thread_name := name_map.get(te.thread_uid):
            te.thread_name = thread_name
            return True
        else:
            return False

    for te in trace_events:
        if te.type == 'sched_switch':
            sw_info = te.sched_switch_info

            uid_from = sw_info['uid_from']
            name_from = sw_info['name_from']
            uid_to = sw_info['uid_to']
            name_to = sw_info['name_to']

            if not (uid_from in curr_thread_name_map):
                first_name_map[uid_from] = name_from
            if not (uid_to in curr_thread_name_map):
                first_name_map[uid_to] = name_to

            curr_thread_name_map[uid_from] = name_from
            curr_thread_name_map[uid_to] = name_to

        if not try_set_name(te, curr_thread_name_map):
            unnamed_entries.append(te)

    for te in unnamed_entries:
        try_set_name(te, first_name_map)


def _filter_pre_m5(trace_events):
    return list(dropwhile(lambda te: te.thread_name != 'm5', trace_events))


def parse(tracefile, filter_pre_m5=True):
    lines = tracefile.readlines()[1:]  # Skip cpus=nproc
    trace_events = [TraceEvent.parse(line) for line in lines]
    _with_thread_names(trace_events)

    if filter_pre_m5:
        trace_events = _filter_pre_m5(trace_events)

    return trace_events


def benchmark_events(trace_events):
    EVENT_MAP = {'ROI start': 'roi_start',
                 'ROI end': 'roi_end',
                 'Benchmark start': 'benchmark_start',
                 'Benchmark end': 'benchmark_end'}

    events = {}

    for te in trace_events:
        if te.type != 'trace_info':
            continue

        thread_info = te.info
        if thread_info in EVENT_MAP.keys():
            e = EVENT_MAP[thread_info]
            events[e] = te.timestamp

    return events
