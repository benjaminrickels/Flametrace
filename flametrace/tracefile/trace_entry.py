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


def cpu_id(trace_entry):
    return trace_entry['cpu_id']


def function_name(trace_entry):
    return trace_entry.get('function_name')


def syscall_name(trace_entry):
    return trace_entry.get('syscall_name')


def call_name(trace_entry):
    return function_name(trace_entry) or syscall_name(trace_entry)


def thread_id(trace_entry):
    return trace_entry['thread_id']


def thread_uid(trace_entry):
    if not thread_id(trace_entry):
        return f'swapper/{cpu_id(trace_entry)}'

    return thread_id(trace_entry)


def timestamp(trace_entry):
    return trace_entry['timestamp']


def trace_type(trace_entry):
    return trace_entry['trace_type']
