import flametrace.tracefile.trace_entry as trace_entry

##############################
# Finding continuous sequences
##############################


def _curr_thread(cpu_seq):
    return trace_entry.thread_uid(cpu_seq['entries'][0])


def _init_cpu_seq(entry, preempted=None):
    cpu_seq = {'entries': [entry]}
    if preempted:
        cpu_seq['preempts'] = preempted

    return cpu_seq


def _preempt_seq(entry, cpu_seq, cont_seqs):
    preempted = last(cpu_seq)
    cpu_seq['preempted_by'] = entry
    cont_seqs.append(cpu_seq)

    return preempted


def _process_entry_with_seq(entry, cpu_seq, cont_seqs):
    thread_uid = trace_entry.thread_uid(entry)
    cpu_curr_thread = _curr_thread(cpu_seq)

    if cpu_curr_thread != thread_uid:
        preempted = _preempt_seq(entry, cpu_seq, cont_seqs)
        cpu_seq = _init_cpu_seq(entry, preempted)
    else:
        cpu_seq['entries'].append(entry)

    return cpu_seq


def _process_entry(entry, cont_seqs, cpu_seqs):
    cpu_id = trace_entry.cpu_id(entry)

    cpu_seq = cpu_seqs.get(cpu_id, None)

    if cpu_seq is None:
        cpu_seqs[cpu_id] = _init_cpu_seq(entry)
    else:
        cpu_seqs[cpu_id] = _process_entry_with_seq(entry, cpu_seq, cont_seqs)


def find_all(trace_entries):
    cont_seqs = []
    cpu_seqs = {}

    for entry in trace_entries:
        _process_entry(entry, cont_seqs, cpu_seqs)

    for cpu_seq in cpu_seqs.values():
        cont_seqs.append(cpu_seq)

    return cont_seqs


####################################
# Operations on continuous sequences
####################################


def entries(cont_seq):
    return cont_seq['entries']


def entry(i, cont_seq):
    return entries(cont_seq)[i]


def preempted(cont_seq):
    return cont_seq.get('preempts', None)


def preempting(cont_seq):
    return cont_seq.get('preempted_by', None)


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
