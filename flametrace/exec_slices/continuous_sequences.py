from flametrace.exec_slices.continuous_sequence import ContinuousSequence


def _process_entry_with_seq(entry, cpu_seq):
    preempted_seq = None
    if cpu_seq.thread_uid != entry.thread_uid:
        cpu_seq.preempt_with(entry)
        preempted_seq = cpu_seq
        cpu_seq = ContinuousSequence(entry, preempted_seq.last)
    else:
        cpu_seq.append(entry)

    return (cpu_seq, preempted_seq)


def _process_entry(entry, cont_seqs, cpu_seqs):
    cpu_id = entry.cpu_id
    cpu_seq = cpu_seqs.get(cpu_id, None)

    if cpu_seq is None:
        cpu_seqs[cpu_id] = ContinuousSequence(entry)
    else:
        cpu_seqs[cpu_id], preempted_seq = _process_entry_with_seq(entry, cpu_seq)
        if preempted_seq:
            cont_seqs.append(preempted_seq)


def find_all(trace_entries):
    cont_seqs = []
    cpu_seqs = {}

    for entry in trace_entries:
        _process_entry(entry, cont_seqs, cpu_seqs)

    for cpu_seq in cpu_seqs.values():
        cont_seqs.append(cpu_seq)

    return cont_seqs
