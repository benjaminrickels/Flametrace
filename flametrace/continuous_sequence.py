import flametrace.trace_entry as trace_entry
from flametrace.preemption_info import find_preempted, find_preempting
from flametrace.util import flatten

##############################
# Finding continuous sequences
##############################


def _has_thread_uid(entry, thread_uid):
    return trace_entry.thread_uid(entry) == thread_uid


def _is_begin(entry, thread_uid):
    return _has_thread_uid(entry, thread_uid)


def _is_end(entry, thread_uid, cpu_id):
    if not _has_thread_uid(entry, thread_uid):
        return trace_entry.cpu_id(entry) == cpu_id
    else:
        # Our thread suddenly switched CPU. This should not be happening, but better be safe
        # than sorry...
        return trace_entry.cpu_id(entry) != cpu_id


def _find_begin(thread_uid, it):
    return next((i for i, entry in it if _is_begin(entry, thread_uid)), None)


def _find_end(thread_uid, cpu_id, it):
    return next((i for i, entry in it if _is_end(entry, thread_uid, cpu_id)),
                None)


def _filter_thread_uid(trace_entries, thread_uid):
    return filter(lambda entry: _has_thread_uid(entry, thread_uid), trace_entries)


def _find_next_entries(thread_uid, trace_entries, it):
    if (begin := _find_begin(thread_uid, it)) is None:
        return None

    cpu_id = trace_entry.cpu_id(trace_entries[begin])

    end = _find_end(thread_uid, cpu_id, it) or len(trace_entries)

    return list(_filter_thread_uid(trace_entries[begin:end], thread_uid))


def _find_preemption_info(seq_entries, trace_entries):
    return (find_preempted(seq_entries[0], trace_entries),
            find_preempting(seq_entries[-1], trace_entries))


def _with_preemption_info(seq_entries, preemption_info):
    preempted, preempting = preemption_info
    return {'entries': seq_entries,
            'preempts': preempted,
            'preempted_by': preempting}


def _find_next(thread_uid, trace_entries, it):
    if (entries := _find_next_entries(thread_uid, trace_entries, it)):
        preemption_info = _find_preemption_info(entries, trace_entries)
        return _with_preemption_info(entries, preemption_info)

    return None


def _find_all_for(thread_uid, trace_entries):
    cont_seqs = []
    it = enumerate(trace_entries)
    while (cont_seq := _find_next(thread_uid, trace_entries, it)):
        cont_seqs.append(cont_seq)

    return list(cont_seqs)


def find_all(trace_entries):
    thread_uids = trace_entry.thread_uids(trace_entries)
    return flatten([_find_all_for(thread_uid, trace_entries) for thread_uid in thread_uids])


####################################
# Operations on continuous sequences
####################################


def entries(cont_seq):
    return cont_seq['entries']


def entry(i, cont_seq):
    return entries(cont_seq)[i]


def preempted(cont_seq):
    return cont_seq['preempts']


def preempting(cont_seq):
    return cont_seq['preempted_by']


def first(cont_seq):
    return entry(0, cont_seq)


def last(cont_seq):
    return entry(-1, cont_seq)


def begin(cont_seq):
    return trace_entry.timestamp(first(cont_seq))


def end(cont_seq):
    return trace_entry.timestamp(last(cont_seq))


def duration(cont_seq):
    return end(cont_seq) - begin(cont_seq)


def begin_approx(cont_seq):
    if (entry := preempted(cont_seq)):
        preempted_end = trace_entry.timestamp(entry)
        return (preempted_end + begin(cont_seq)) / 2

    return begin(cont_seq)


def end_approx(cont_seq):
    if (entry := preempting(cont_seq)):
        preempting_begin = trace_entry.timestamp(entry)
        return (end(cont_seq) + preempting_begin) / 2

    return end(cont_seq)


def duration_approx(cont_seq):
    return end_approx(cont_seq) - begin_approx(cont_seq)


def cpu_id(cont_seq):
    return trace_entry.cpu_id(first(cont_seq))


def thread_uid(cont_seq):
    return trace_entry.thread_uid(first(cont_seq))
