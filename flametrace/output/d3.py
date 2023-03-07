import json
from flametrace import exec_slices
from flametrace.util import groupby_sorted, max_key, min_key, ps_to_cycles


def _slice_seq_to_json(slice_seq, slices, begin, slices_by_parent):
    curr_timestamp = begin

    json_seq = []
    for slce in slice_seq:
        delta = slce.begin - curr_timestamp

        if delta > 0:
            json_seq.append({'name': 'HIDEME',
                             'cycles': ps_to_cycles(delta),
                             'value': delta})
        curr_timestamp = slce.begin

        slce_json = _slice_to_json(slce, slices, slices_by_parent)
        json_seq.append(slce_json)

        curr_timestamp = slce.end

    return json_seq


def _slice_children_to_json(slce, slices, slices_by_parent):
    children = slices_by_parent.get(slce.id, [])
    return _slice_seq_to_json(children, slices, slce.begin, slices_by_parent)


def _slice_to_json(slce, slices, slices_py_parent):
    call_name = slce.call_name
    call_name = f': {call_name}' if call_name else ''

    thread_uid = slce.thread_uid
    name = f'{thread_uid}{call_name}'

    children = _slice_children_to_json(slce, slices, slices_py_parent)

    duration = slce.duration
    return {'name': name,
            'value': duration,
            'cycles': ps_to_cycles(duration),
            'thread_uid': thread_uid,
            'children': children}


def _parent_or_m1(slce):
    if (parent := slce.parent) is not None:
        return parent

    return -1


def _cpu_slices_to_json(cpu_id, cpu_slices, trace_begin, trace_duration):
    slices_by_parent = groupby_sorted(cpu_slices, key=_parent_or_m1)

    top_level_slices = slices_by_parent[-1]
    json_children = _slice_seq_to_json(top_level_slices, cpu_slices, trace_begin, slices_by_parent)

    return {'name': f'core{cpu_id}',
            'value': trace_duration,
            'cycles': ps_to_cycles(trace_duration),
            'children': json_children}


def to_json(slices, prefix='d3-trace-cpu'):
    slices_by_cpu = groupby_sorted(slices, lambda s: s.cpu_id)

    begin = min_key(slices, lambda s: s.begin)
    end = max_key(slices, lambda s: s.end)

    for cpu_id, cpu_slices in slices_by_cpu.items():
        cpu_json = _cpu_slices_to_json(cpu_id, cpu_slices, begin, end - begin)

        with open(f'{prefix}-{cpu_id}.json', 'w') as f:
            json.dump(cpu_json, f)
