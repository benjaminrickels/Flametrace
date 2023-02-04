import bisect

import flametrace.config as config
import flametrace.exec_slice.continuous_sequence as cont_seq
import flametrace.tracefile.trace_entry as trace_entry
from flametrace.exec_slice.exec_stack import ExecStack
from flametrace.util import flatten, groupby_sorted, max_key, min_key

#####################
# Finding exec slices
#####################


def _is_ignored(name):
    if not 'ignored_funs' in _is_ignored.__dict__:
        _is_ignored.ignored_funs = set(config.IGNORED_FUNS)

    return name in _is_ignored.ignored_funs


def _process_1(entry, stack):
    trace_type = trace_entry.trace_type(entry)
    if trace_type in ['ftrace_entry', 'syscall_enter']:
        action = stack.push
    elif trace_type in ['ftrace_exit', 'syscall_exit']:
        action = stack.pop
    else:
        return

    call_name = trace_entry.call_name(entry)
    if not _is_ignored(call_name):
        action(call_name, trace_entry.timestamp(entry))


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


def _grouped_slices(fun_slices):
    slices_by_thread_uid = groupby_sorted(fun_slices,
                                          group_key=thread_uid,
                                          sort_key=lambda slce: str(thread_uid(slce)))
    for uid, thread_slices in slices_by_thread_uid.items():
        slices_by_depth = groupby_sorted(thread_slices, key=lambda slce: depth(slce, -1))
        for depth_, depth_slices in slices_by_depth.items():
            slices_time_sorted = sorted(depth_slices, key=begin)
            slices_begins = [begin(slce) for slce in slices_time_sorted]

            slices_by_depth[depth_] = (slices_time_sorted, slices_begins)

        slices_by_thread_uid[uid] = slices_by_depth

    return slices_by_thread_uid


def _find_parent(slce, grouped_slices):
    uid = thread_uid(slce)
    depth = slce.get('depth', -1)

    if depth < 0:
        return

    candidates, begins = grouped_slices[uid][depth - 1]

    i = bisect.bisect_right(begins, begin(slce))
    slce['parent'] = slice_id(candidates[i-1])


def _find_parents(fun_slices):
    grouped_slices = _grouped_slices(fun_slices)
    for slce in fun_slices:
        _find_parent(slce, grouped_slices)


def _with_ids(slices):
    for i, s in enumerate(slices):
        s['slice_id'] = i


def find_all(trace_entries):
    cont_seqs = cont_seq.find_all(trace_entries)

    seqs_by_tuid = groupby_sorted(cont_seqs,
                                  sort_key=lambda seq: str(cont_seq.thread_uid(seq)),
                                  group_key=cont_seq.thread_uid).items()
    slices = flatten([_find_all_of(thread_uid, cont_seqs)
                     for thread_uid, cont_seqs in seqs_by_tuid])
    _with_ids(slices)

    _find_parents(slices)

    slices.sort(key=begin)

    return slices


###########################
# Operations on exec slices
###########################


def begin(exec_slice):
    return exec_slice['begin']


def end(exec_slice):
    return exec_slice['end']


def duration(exec_slice):
    return end(exec_slice) - begin(exec_slice)


def call_id(exec_slice, default=None):
    return exec_slice.get('call_id', default)


def cpu_id(exec_slice):
    return exec_slice['cpu_id']


def depth(exec_slice, default=None):
    return exec_slice.get('depth', default)


def function_name(exec_slice, default=None):
    return exec_slice.get('function_name', default)


def is_begin(exec_slice):
    return 'is_begin' in exec_slice


def is_end(exec_slice):
    return 'is_end' in exec_slice


def parent(exec_slice, default=None):
    return exec_slice.get('parent', default)


def slice_id(exec_slice):
    return exec_slice['slice_id']


def thread_uid(exec_slice):
    return exec_slice['thread_uid']


def type(exec_slice):
    return exec_slice['type']


#################
# More operations
#################

def trace_begin_end(slices):
    begin_ = min_key(slices, begin)
    end_ = max_key(slices, end)

    return (begin_, end_)
