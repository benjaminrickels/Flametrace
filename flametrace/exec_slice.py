from operator import itemgetter

import flametrace.continuous_sequence as cont_seq
import flametrace.trace_entry as trace_entry
from flametrace.exec_stack import ExecStack
from flametrace.util import flatten, groupby_sorted

#####################
# Finding exec slices
#####################


_ignored_funs = set()


def ignore_funs(*ignore):
    global _ignored_funs
    _ignored_funs = set(ignore)


def _is_ignored(name):
    return name in _ignored_funs


def _process_1(entry, stack):
    FTRACE_PARAMGETTER = itemgetter('function_name', 'timestamp')
    SYSCALL_PARAMGETTER = itemgetter('syscall_name', 'timestamp')

    trace_type = trace_entry.trace_type(entry)
    if trace_type == 'ftrace_entry':
        action = stack.push
        param_getter = FTRACE_PARAMGETTER
    elif trace_type == 'ftrace_exit':
        action = stack.pop
        param_getter = FTRACE_PARAMGETTER
    elif trace_type == 'sys_enter':
        action = stack.push
        param_getter = SYSCALL_PARAMGETTER
    elif trace_type == 'sys_exit':
        action = stack.pop
        param_getter = SYSCALL_PARAMGETTER
    else:
        return

    fun_name, timestamp = param_getter(entry)
    if not _is_ignored(fun_name):
        action(fun_name, timestamp)


def _process(c_seq, stack):
    entries = cont_seq.entries(c_seq)
    cpu_id = cont_seq.cpu_id(c_seq)
    begin_approx = cont_seq.begin_approx(c_seq)
    end_approx = cont_seq.end_approx(c_seq)

    stack.resume(begin_approx, cpu_id)
    for entry in entries:
        _process_1(entry, stack)
    stack.suspend(end_approx)


def _find_all_of(thread_uid, cont_seqs):
    cont_seqs_sorted = sorted(cont_seqs, key=cont_seq.begin)

    stack = ExecStack(thread_uid)
    for c_seq in cont_seqs_sorted:
        _process(c_seq, stack)
    return stack.teardown()


def find_all(cont_seqs):
    seqs_by_tuid = groupby_sorted(cont_seqs,
                                  sort_key=lambda seq: str(cont_seq.thread_uid(seq)),
                                  group_key=cont_seq.thread_uid).items()
    return flatten([_find_all_of(thread_uid, cont_seqs) for thread_uid, cont_seqs in seqs_by_tuid])


###########################
# Operations on exec slices
###########################


def depth(exec_slice):
    return exec_slice['depth'] if 'depth' in exec_slice else float('-inf')


def begin(exec_slice):
    return exec_slice['begin']


def end(exec_slice):
    return exec_slice['end']


def duration(exec_slice):
    return end(exec_slice) - begin(exec_slice)
