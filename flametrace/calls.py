from flametrace.call import Call
from flametrace.util import groupby_sorted


def _parent(parent, slices_map):
    if (parent_slice := slices_map.get(parent, None)) and parent_slice.is_call_slice:
        return parent_slice.call_id


def _children(call_slices, slices_map):
    children = set()
    for slce in call_slices:
        for child_id in slce.children:
            if child := slices_map.get(child_id):
                children.add(child.call_id)

    return children


def _from_call_slices(call_id, call_slices, slices_map, parent_ids, children_ids):
    first = call_slices[0]
    last = call_slices[-1]

    active_time = sum(map(lambda s: s.duration, call_slices))

    call = Call(active_time,
                first.begin,
                last.end,
                first.is_call_begin and last.is_call_end,
                call_id,
                first.call_name,
                first.thread_uid)

    if parent := _parent(first.parent, slices_map):
        parent_ids[call_id] = parent

    children_ids[call_id] = []
    if children := _children(call_slices, slices_map):
        children_ids[call_id] = list(children)

    return call


def all_from_slices(call_slices):
    slices_grouped_by_call_id = groupby_sorted(call_slices, key=lambda s: s.call_id)
    slices_map = {s.id: s for s in call_slices}

    calls = {}
    parent_ids = {}
    children_ids = {}

    for call_id, call_slices_ in slices_grouped_by_call_id.items():
        call = _from_call_slices(call_id, call_slices_, slices_map, parent_ids, children_ids)
        calls[call_id] = call

    for call_id, call in calls.items():
        if (parent_id := parent_ids.get(call_id)) is not None:
            call.parent = calls[parent_id]

        children = map(lambda id: calls[id], children_ids[call_id])
        call.children = list(children)

    return calls.values()
