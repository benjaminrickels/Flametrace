import json
from flametrace.util import groupby_sorted, ps_to_cycles

import flametrace.exec_slice as exec_slice


def _slice_seq_to_json(slice_seq, slices, begin, slices_by_parent):
    curr_timestamp = begin

    json_seq = []
    for slce in slice_seq:
        delta = exec_slice.begin(slce) - curr_timestamp

        if delta > 0:
            json_seq.append({'name': 'HIDEME',
                             'cycles': ps_to_cycles(delta),
                             'value': delta})
        curr_timestamp = exec_slice.begin(slce)

        slce_json = _slice_to_json(slce, slices, slices_by_parent)
        json_seq.append(slce_json)

        curr_timestamp = exec_slice.end(slce)

    return json_seq


def _slice_children_to_json(slce, slices, slices_by_parent):
    begin = exec_slice.begin(slce)
    children = slices_by_parent.get(exec_slice.slice_id(slce), [])
    return _slice_seq_to_json(children, slices, begin, slices_by_parent)


def _slice_to_json(slce, slices, slices_py_parent):
    function_name = exec_slice.function_name(slce)
    function_name = f': {function_name}' if function_name else ''

    thread_uid = exec_slice.thread_uid(slce)
    name = f'{thread_uid}{function_name}'

    children = _slice_children_to_json(slce, slices, slices_py_parent)

    duration = exec_slice.duration(slce)
    return {'name': name,
            'value': duration,
            'cycles': ps_to_cycles(duration),
            'thread_uid': thread_uid,
            'children': children}


def _cpu_slices_to_json(cpu_id, cpu_slices, trace_begin, trace_duration):
    slices_by_parent = groupby_sorted(cpu_slices, key=lambda slce: exec_slice.parent(slce, -1))

    top_level_slices = slices_by_parent[-1]
    json_children = _slice_seq_to_json(top_level_slices, cpu_slices, trace_begin, slices_by_parent)

    return {'name': f'core{cpu_id}',
            'value': trace_duration,
            'cycles': ps_to_cycles(trace_duration),
            'children': json_children}


def to_json(slices, prefix='d3-trace-cpu'):
    slices_by_cpu = groupby_sorted(slices, exec_slice.cpu_id)

    begin, end = exec_slice.trace_begin_end(slices)

    for cpu_id, cpu_slices in slices_by_cpu.items():
        cpu_json = _cpu_slices_to_json(cpu_id, cpu_slices, begin, end - begin)

        with open(f'{prefix}-{cpu_id}.json', 'w') as f:
            json.dump(cpu_json, f)
