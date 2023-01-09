from operator import itemgetter

from flametrace.util import groupby_sorted


def _make(trace_type, thread_id, cpu_id, timestamp, **attrs):
    trace_entry = {'trace_type': trace_type,
                   'thread_id': thread_id,
                   'cpu_id': cpu_id,
                   'timestamp': timestamp}

    for k, v in attrs.items():
        trace_entry[k] = v

    return trace_entry


def make(trace_type, thread_id, cpu_id, timestamp, trace_info):
    return _make(trace_type, thread_id, cpu_id, timestamp, trace_info=trace_info)


def make_ftrace_entry(thread_id, cpu_id, timestamp, function_name):
    return _make('ftrace_entry', thread_id, cpu_id, timestamp, function_name=function_name)


def make_ftrace_exit(thread_id, cpu_id, timestamp, function_name):
    return _make('ftrace_exit', thread_id, cpu_id, timestamp, function_name=function_name)


def make_sys_enter(thread_id, cpu_id, timestamp, syscall_name):
    return _make('sys_enter', thread_id, cpu_id, timestamp, syscall_name=syscall_name)


def make_sys_exit(thread_id, cpu_id, timestamp, syscall_name):
    return _make('sys_exit', thread_id, cpu_id, timestamp, syscall_name=syscall_name)


def make_sched_switch(thread_id, cpu_id, timestamp, thread_name_from, thread_id_to, thread_name_to):
    return _make('sched_switch',
                 thread_id,
                 cpu_id,
                 timestamp,
                 thread_id_from=thread_id,
                 thread_name_from=thread_name_from,
                 thread_id_to=thread_id_to,
                 thread_name_to=thread_name_to)


def trace_type(trace_entry):
    return trace_entry['trace_type']


def thread_id(trace_entry):
    return trace_entry['thread_id']


def cpu_id(trace_entry):
    return trace_entry['cpu_id']


def thread_uid(trace_entry):
    if not thread_id(trace_entry):
        return f'swapper/{cpu_id(trace_entry)}'

    return thread_id(trace_entry)


def timestamp(trace_entry):
    return trace_entry['timestamp']


def to_id(thread_uid):
    if isinstance(thread_uid, str):
        return 0
    else:
        return thread_uid


def thread_uids(trace_entries):
    return set(map(thread_uid, trace_entries))


def by_cpu(trace_entries):
    return groupby_sorted(trace_entries, key=itemgetter('cpu_id'))
