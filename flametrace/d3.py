import json
from operator import itemgetter
from flametrace.util import groupby_sorted, ps_to_cycles


def _slice_seq_to_json(slice_seq, slices, begin, slices_by_parent):
    curr_timestamp = begin

    json_seq = []
    for slce in slice_seq:
        delta = slce['begin'] - curr_timestamp

        if delta > 0:
            json_seq.append({'name': 'HIDEME',
                             'cycles': ps_to_cycles(delta),
                             'value': delta})
        curr_timestamp = slce['begin']

        slce_json = _slice_to_json(slce, slices, slices_by_parent)
        json_seq.append(slce_json)

        curr_timestamp = slce['end']

    return json_seq


def _slice_children_to_json(slce, slices, slices_by_parent):
    begin = slce['begin']
    children = slices_by_parent.get(slce['slice_id'], [])
    return _slice_seq_to_json(children, slices, begin, slices_by_parent)


def _slice_to_json(slce, slices, slices_py_parent):
    function_name = slce.get('function_name', None)
    function_name = f': {function_name}' if function_name else ''

    thread_uid = slce['thread_uid']
    name = f'{thread_uid}{function_name}'

    children = _slice_children_to_json(slce, slices, slices_py_parent)

    value = slce['end'] - slce['begin']
    return {'name': name,
            'value': value,
            'cycles': ps_to_cycles(value),
            'thread_uid': slce['thread_uid'],
            'children': children}


def _min_max_time(slices):
    min_time = min(slices, key=itemgetter('begin'))['begin']
    max_time = max(slices, key=itemgetter('end'))['end']

    return (min_time, max_time)


def _cpu_slices_to_json(cpu_id, cpu_slices, min_max_time):
    min_time, max_time = min_max_time

    slices_by_parent = groupby_sorted(cpu_slices, key=lambda slce: slce.get('parent', -1))

    top_level_slices = slices_by_parent[-1]
    json_children = _slice_seq_to_json(top_level_slices, cpu_slices, min_time, slices_by_parent)

    root_delta = max_time - min_time
    return {'name': f'core{cpu_id}',
            'value': root_delta,
            'cycles': ps_to_cycles(root_delta),
            'children': json_children}


def to_json(slices, entire=True, prefix='d3-trace-cpu'):
    slices_by_cpu = groupby_sorted(slices, key=itemgetter('cpu_id'))

    if entire:
        min_max_time = _min_max_time(slices)

    for cpu_id, cpu_slices in slices_by_cpu.items():
        cpu_slices = sorted(cpu_slices, key=itemgetter('begin'))
        if not entire:
            min_max_time = _min_max_time(cpu_slices)

        cpu_json = _cpu_slices_to_json(cpu_id, cpu_slices, min_max_time)

        with open(f'{prefix}-{cpu_id}.json', 'w') as f:
            json.dump(cpu_json, f)
