import bisect

import flametrace.config as config
import flametrace.exec_slices.continuous_sequences as cont_seqs
from flametrace.exec_slices.exec_stack import ExecStack
from flametrace.util import flatten, groupby_sorted

####################################################################################################
# Finding slices
####################################################################################################


def _is_ignored(name):
    if not 'ignored_funs' in _is_ignored.__dict__:
        _is_ignored.ignored_funs = set(config.IGNORED_FUNS)

    return name in _is_ignored.ignored_funs


def _process_1(entry, stack):
    trace_type = entry.type
    if trace_type in ['ftrace_entry', 'syscall_enter']:
        action = stack.push
    elif trace_type in ['ftrace_exit', 'syscall_exit']:
        action = stack.pop
    else:
        return

    call_name = entry.call_name
    if not _is_ignored(call_name):
        action(call_name, entry.timestamp)


def _process(cseq, stack):
    entries = cseq.entries
    cpu_id = cseq.cpu_id
    begin_approx = cseq.begin_approx
    end_approx = cseq.end_approx

    stack.resume(begin_approx, cpu_id, cseq.thread_name)
    for entry in entries:
        _process_1(entry, stack)
    stack.suspend(end_approx)


def _find_all_of(thread_uid, cseqs):
    cseqs_sorted = sorted(cseqs, key=lambda cs: cs.begin)

    stack = ExecStack(thread_uid)
    for csea in cseqs_sorted:
        _process(csea, stack)
    return stack.teardown()


def _get_find_parent_info(call_slices):
    """Group `(slices, map(begin, slices))`-pairs by `thread_uid` and then `depth`"""
    slices_by_thread_uid = groupby_sorted(call_slices, key=lambda s: s.thread_uid)
    for uid, uid_slices in slices_by_thread_uid.items():
        slices_by_depth = groupby_sorted(uid_slices, key=lambda s: s.call_depth_or(-1))
        for depth, depth_slices in slices_by_depth.items():
            slices_time_sorted = sorted(depth_slices, key=lambda s: s.begin)
            slices_begins = [s.begin for s in slices_time_sorted]

            slices_by_depth[depth] = (slices_time_sorted, slices_begins)

        slices_by_thread_uid[uid] = slices_by_depth

    return slices_by_thread_uid


def _find_parent(slce, find_parent_info):
    if not slce.is_call_slice:
        return

    thread_uid = slce.thread_uid
    call_depth = slce.call_depth

    candidates, begins = find_parent_info[thread_uid][call_depth - 1]

    i = bisect.bisect_right(begins, slce.begin)
    slce.parent = candidates[i-1].id


def _find_parents(slices, call_slices):
    find_parent_info = _get_find_parent_info(slices)
    for slce in call_slices:
        _find_parent(slce, find_parent_info)


def _find_children(slices, call_slices):
    slices_by_parent = groupby_sorted(call_slices, key=lambda slce: slce.parent)
    for slce in slices:
        slce.children = [other.id for other in slices_by_parent.get(slce.id, [])]


def _filter_dur0_slices(slices):
    return [s for s in slices if s.duration > 0]


def find_all(trace_entries):
    cseqs = cont_seqs.find_all(trace_entries)

    cseqs_by_thread_uid = groupby_sorted(cseqs, key=lambda cs: cs.thread_uid).items()
    slices = flatten([_find_all_of(thread_uid, cont_seqs)
                     for thread_uid, cont_seqs in cseqs_by_thread_uid])
    slices = _filter_dur0_slices(slices)

    call_slices = list(filter(lambda s: s.is_call_slice, slices))
    _find_parents(slices, call_slices)
    _find_children(slices, call_slices)

    slices.sort(key=lambda s: s.begin)

    return slices

####################################################################################################
# Limiting slices
####################################################################################################


def _find_first_by(slices, key, val):
    for s in slices:
        if key(s) == val:
            return s


def _get_limit_from_to(slices, limit, limit_context, benchmark_events):
    slices_rev = sorted(slices, key=lambda s: s.end, reverse=True)

    slices_begin = slices[0].begin
    slices_end = slices_rev[0].end

    limit_type_from = limit.get('limit_type_from')
    limit_type_to = limit.get('limit_type_to')
    limit_value_from = limit.get('limit_value_from')
    limit_value_to = limit.get('limit_value_to')

    limit_from = slices_begin
    limit_to = slices_end

    if limit_type_from == 'abs':
        limit_from = limit_value_from
    if limit_type_to == 'abs':
        limit_to = limit_value_to
    if limit_type_from == 'benchmark':
        limit_from = benchmark_events['benchmark_start']
    if limit_type_to == 'benchmark':
        limit_to = benchmark_events['benchmark_end']
    if limit_type_from == 'call':
        limit_from = _find_first_by(slices, lambda s: s.call_id, limit_value_from).begin
    if limit_type_to == 'call':
        limit_to = _find_first_by(slices_rev, lambda s: s.call_id, limit_value_to).end
    if limit_type_from == 'perc' or limit_type_to == 'perc':
        delta = slices_end - slices_begin

        if limit_type_from == 'perc':
            limit_from = slices_begin + 0.01 * limit_value_from * delta
        if limit_type_to == 'perc':
            limit_to = slices_begin + 0.01 * limit_value_to * delta
    if limit_type_from == 'roi':
        limit_from = benchmark_events['roi_start']
    if limit_type_to == 'roi':
        limit_to = benchmark_events['roi_end']
    if limit_type_from == 'slice':
        limit_from = _find_first_by(slices, lambda s: s.id, limit_value_from).begin
    if limit_type_to == 'slice':
        limit_to = _find_first_by(slices_rev, lambda s: s.id, limit_value_to).end
    if limit_type_from == 'thread':
        limit_from = _find_first_by(slices, lambda s: s.thread_uid, limit_value_from).begin
    if limit_type_to == 'thread':
        limit_to = _find_first_by(slices_rev, lambda s: s.thread_uid, limit_value_to).end

    limit_from_to_delta = limit_to - limit_from
    limit_from = limit_from - 0.01 * limit_context * limit_from_to_delta
    limit_to = limit_to + 0.01 * limit_context * limit_from_to_delta

    return (limit_from, limit_to)


def limit(slices, limit, limit_context, benchmark_events):
    limit_from, limit_to = _get_limit_from_to(slices, limit, limit_context, benchmark_events)

    slices = [s for s in slices if s.end > limit_from and s.begin < limit_to]
    for s in slices:
        is_call_slice = s.type == 'call'
        if s.begin < limit_from:
            s.begin = limit_from
            if is_call_slice:
                s.is_call_begin = False
        if s.end > limit_to:
            s.end = limit_to
            if is_call_slice:
                s.is_call_end = False

    return _filter_dur0_slices(slices)
