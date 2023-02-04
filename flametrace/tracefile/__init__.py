from operator import itemgetter
from re import match, search

import flametrace.tracefile.trace_entry as trace_entry
from flametrace.util import groupby_sorted

# Example: " <...>-1234  [001]  ftrace_entry: context_switch"
TRACE_REGEX = ('^\s*<(?P<thread_info>\S*)>-(?P<thread_id>\d*)'
               '\s*\[(?P<cpu_id>\d*)\]'
               '\s*(?P<timestamp>\d*):'
               '\s*(?P<trace_name>\S*):\s*(?P<trace_info>.*)$')

SYSCALL_REGEX = '(sys_enter|sys_exit)_(\S*)'

SCHED_SWITCH_REGEX = ('(?P<from_name>\S*):(?P<from_id>\d*) '
                      '\[\d*\] TBV ==> '
                      '(?P<to_name>\S*):(?P<to_id>\d*)')


def match_to_syscall_entry(trace_name, thread_id, cpu_id, timestamp):
    if not (m := search(SYSCALL_REGEX, trace_name)):
        return None

    trace_type, syscall_name = m.group(1, 2)

    if trace_type == 'sys_enter':
        return trace_entry.make_sys_enter(thread_id, cpu_id, timestamp, syscall_name)
    elif trace_type == 'sys_exit':
        return trace_entry.make_sys_exit(thread_id, cpu_id, timestamp, syscall_name)
    else:
        raise 'BUG'


def parse_sched_switch_info(trace_info):
    m = match(SCHED_SWITCH_REGEX, trace_info)

    from_name, to_id, to_name = itemgetter('from_name', 'to_id', 'to_name')(m.groupdict())
    to_id = int(to_id)

    return (from_name, to_id, to_name)


def match_to_sched_switch_entry(trace_name, thread_id, cpu_id, timestamp, trace_info):
    if trace_name != 'sched_switch':
        return None

    from_name, to_id, to_name = parse_sched_switch_info(trace_info)
    return trace_entry.make_sched_switch(thread_id, cpu_id, timestamp, from_name, to_id, to_name)


def match_to_trace_entry(trace_name, thread_id, cpu_id, timestamp, trace_info):
    if trace_name == 'ftrace_entry':
        return trace_entry.make_ftrace_entry(thread_id, cpu_id, timestamp, trace_info)
    elif trace_name == 'ftrace_exit':
        return trace_entry.make_ftrace_exit(thread_id, cpu_id, timestamp, trace_info)
    elif syscall_entry := match_to_syscall_entry(trace_name, thread_id, cpu_id, timestamp):
        return syscall_entry
    elif sched_switch_entry := match_to_sched_switch_entry(trace_name, thread_id, cpu_id, timestamp, trace_info):
        return sched_switch_entry
    else:
        return trace_entry.make(trace_name, thread_id, cpu_id, timestamp, trace_info)


def parse_1(tracefile_line):
    if not (m := match(TRACE_REGEX, tracefile_line)):
        return None

    trace_name, thread_id, cpu_id, timestamp, trace_info = itemgetter(
        'trace_name', 'thread_id', 'cpu_id', 'timestamp', 'trace_info')(m.groupdict())

    thread_id = int(thread_id)
    cpu_id = int(cpu_id)
    timestamp = int(timestamp)

    return match_to_trace_entry(trace_name, thread_id, cpu_id, timestamp, trace_info)


def parse(tracefile):
    return list(filter(None, map(parse_1, tracefile.readlines())))
