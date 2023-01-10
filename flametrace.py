import colorsys
import json
from argparse import ArgumentParser
from operator import itemgetter

import drawSvg as draw_svg

import flametrace.continuous_sequence as continuous_sequence
import flametrace.exec_slice as exec_slice
import flametrace.trace_entry as trace_entry
import flametrace.tracefile as tracefile
from flametrace.util import groupby_sorted

SVG_X_SCALE = 100 * 1e3
SVG_Y_UNIT = 100

#
# Parse a tracefile (Trace.txt) into a list of trace entries
#
# A trace entry is a map with at least the keys 'trace_type', 'thread_uid', 'thread_id', 'cpu_id',
# and 'timestamp'
#
# 'thread_uid' is 'thread_id' if 'thread_id' != 0, otherwise it is "swapper/'cpu_id'" to uniquely
# identify the idle threads
#


def int_to_hsl(i):
    # Maps 0 -> 0, 1 -> 20, 2 -> 40, ..., 17 -> 340, 18 -> 0, ...
    hue = 20 * (i % 18)
    # Maps [0, 17] -> 85, [18, 35] -> 70, [36, 53] -> 55, [54, 71] -> 40, [72, 89] -> 85, ...
    luminance = 85 - 15*int((i % 72) / 18)

    return (hue / 360, 0.8, luminance / 100)


def thread_id_to_fill(thread_id):
    if thread_id == 0:
        hsl = (0.5, 0, 0.3)
    elif thread_id < 1000:
        hsl = (0.5, 0, 0.6)
    else:
        hsl = int_to_hsl(thread_id - 1000)

    h, s, l = hsl
    r, g, b = colorsys.hls_to_rgb(h, l, s)

    return f'#{int(255*r):02x}{int(255*g):02x}{int(255*b):02x}'


def exec_slice_to_rectangle(exec_slice, begin):
    depth = exec_slice.get('depth', -1) + 1

    thread_uid = exec_slice['thread_uid']

    function_name = exec_slice.get('function_name', '')
    if function_name != '':
        function_name = f'{function_name}:'

    slice_begin = exec_slice['begin']
    slice_end = exec_slice['end']
    slice_duration = slice_end - slice_begin

    x = (slice_begin - begin) / SVG_X_SCALE
    y = depth*SVG_Y_UNIT
    width = (slice_duration) / SVG_X_SCALE
    height = SVG_Y_UNIT
    fill = thread_id_to_fill(trace_entry.to_id(thread_uid))

    thread_name = exec_slice.get('thread_name', '')
    if thread_name != '':
        thread_name = f' ({thread_name})'

    r = draw_svg.Rectangle(x, y, width, height, fill=fill, stroke='black', stroke_width='0.2')

    s_type = exec_slice['type']
    slice_id = exec_slice.get('slice_id', 'N/A')
    parent = exec_slice.get('parent', 'N/A')
    depth = exec_slice.get('depth', 'N/A')
    r.appendTitle(f'{function_name}{thread_uid}{thread_name}\n'
                  f'Type: {s_type}\n'
                  f'Begin: {slice_begin:,} ps\n'
                  f'End: {slice_end:,}ps \n'
                  f'Duration: {slice_duration:,} ps ({(slice_duration/500):,} cycles)\n'
                  f'Slice ID: {slice_id}\n'
                  f'Parent: {parent}\n'
                  f'Depth: {depth}')

    return r


def per_cpu_exec_to_svg(e_slices):
    slices_by_cpu_id = groupby_sorted(e_slices, itemgetter('cpu_id')).items()
    for cpu_id, cpu_slices in slices_by_cpu_id:
        if not cpu_slices:
            continue

        begin = exec_slice.begin(min(cpu_slices, key=exec_slice.begin))
        end = exec_slice.end(max(cpu_slices, key=exec_slice.end))
        max_depth = exec_slice.depth(max(cpu_slices, key=exec_slice.depth))

        duration = end - begin

        width = duration / SVG_X_SCALE
        height = (max_depth + 3) * SVG_Y_UNIT

        svg = draw_svg.Drawing(width, height)

        for slice in cpu_slices:
            svg.append(exec_slice_to_rectangle(slice, begin))

        svg.saveSvg(f'flamegraph-core{cpu_id}.svg')


def slice_to_json(slce, slices):
    slice_id = slce['slice_id']
    curr_timestamp = slce['begin']

    children = [slce for slce in slices if slce.get('parent') == slice_id]
    json_children = []
    for child in children:
        delta = child['begin'] - curr_timestamp

        if delta > 0:
            json_children.append({'name': 'HIDEME',
                                  'value': delta})
        curr_timestamp = child['begin']

        json_child = slice_to_json(child, slices)
        json_children.append(json_child)

        curr_timestamp = child['end']

    function_name = slce.get('function_name', None)
    function_name = f': {function_name}' if function_name else ''

    thread_uid = slce['thread_uid']

    name = f'{thread_uid}{function_name}'

    return {'name': name,
            'value': slce['end'] - slce['begin'],
            'thread_uid': slce['thread_uid'],
            'children': json_children}


def slices_to_json(slices):
    slices_by_cpu = groupby_sorted(slices, itemgetter('cpu_id'))

    max_time = max(slices, key=itemgetter('end'))['end']
    min_time = min(slices, key=itemgetter('begin'))['begin']

    for cpu_id, cpu_slices in slices_by_cpu.items():
        cpu_slices = sorted(cpu_slices, key=itemgetter('begin'))
        top_level_slices = [slce for slce in cpu_slices if 'parent' not in slce]

        curr_timestamp = min_time

        children = []
        for slce in top_level_slices:
            delta = slce['begin'] - curr_timestamp

            if delta > 0:
                children.append({'name': 'HIDEME',
                                 'value': delta})

            json_slce = slice_to_json(slce, cpu_slices)
            children.append(json_slce)

            curr_timestamp = slce['end']

        root_delta = max_time - min_time
        trace_json = {'name': f'core{cpu_id}',
                      'value': root_delta,
                      'children': children}

        with open(f'trace-cpu-{cpu_id}.json', 'w') as f:
            json.dump(trace_json, f)


def main():
    parser = ArgumentParser()
    parser.add_argument('tracefile', nargs='?', default='Trace.txt')
    parser.add_argument('--d3-fg', action='store_true',
                        help='Generate JSON files that can be used with the D3 flamegraph plotter')
    parser.add_argument('--svg-fg', action='store_true', help='Generate static SVG flamegraphs')
    args = parser.parse_args()

    exec_slice.ignore_funs('registerThread', 'unregisterThread', 'start_pthread')

    with open(args.tracefile) as tf:
        tes = tracefile.parse(tf)

    if tes:
        c_seqs = continuous_sequence.find_all(tes)
        slices = exec_slice.find_all(c_seqs)

        if args.d3_fg:
            slices_to_json(slices)

        if args.svg_fg:
            per_cpu_exec_to_svg(slices)


if __name__ == '__main__':
    main()
