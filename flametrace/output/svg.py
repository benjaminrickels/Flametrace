import colorsys

import drawSvg as draw_svg

import flametrace.exec_slice as exec_slice
import flametrace.tracefile.trace_entry as trace_entry
from flametrace.util import groupby_sorted, max_key, min_key, ps_to_cycles, thread_uid_to_id

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


def _int_to_hsl(i):
    # Maps 0 -> 0, 1 -> 20, 2 -> 40, ..., 17 -> 340, 18 -> 0, ...
    hue = 20 * (i % 18)
    # Maps [0, 17] -> 85, [18, 35] -> 70, [36, 53] -> 55, [54, 71] -> 40, [72, 89] -> 85, ...
    luminance = 85 - 15*int((i % 72) / 18)

    return (hue / 360, 0.8, luminance / 100)


def _thread_id_to_fill(thread_id):
    if thread_id == 0:
        hsl = (0.5, 0, 0.3)
    elif thread_id < 1000:
        hsl = (0.5, 0, 0.6)
    else:
        hsl = _int_to_hsl(thread_id - 1000)

    h, s, l = hsl
    r, g, b = colorsys.hls_to_rgb(h, l, s)

    return f'#{int(255*r):02x}{int(255*g):02x}{int(255*b):02x}'


def exec_slice_to_rectangle(slce, trace_begin):
    depth = exec_slice.depth(slce, -1) + 1

    thread_uid = exec_slice.thread_uid(slce)

    function_name = exec_slice.function_name(slce, '')
    if function_name != '':
        function_name = f'{function_name}:'

    slice_begin = exec_slice.begin(slce)
    slice_end = exec_slice.end(slce)
    slice_duration = slice_end - slice_begin

    x = (slice_begin - trace_begin) / SVG_X_SCALE
    y = depth*SVG_Y_UNIT
    width = (slice_duration) / SVG_X_SCALE
    height = SVG_Y_UNIT
    fill = _thread_id_to_fill(thread_uid_to_id(thread_uid))

    thread_name = ''

    r = draw_svg.Rectangle(x, y, width, height, fill=fill, stroke='black', stroke_width='0.2')

    s_type = exec_slice.type(slce)
    slice_id = exec_slice.slice_id(slce)
    parent = exec_slice.parent(slce, 'N/A')
    depth = exec_slice.depth(slce, 'N/A')
    r.appendTitle(f'{function_name}{thread_uid}{thread_name}\n'
                  f'Type: {s_type}\n'
                  f'Begin: {slice_begin:,} ps\n'
                  f'End: {slice_end:,}ps \n'
                  f'Duration: {ps_to_cycles(slice_duration):,} cycles ({slice_duration:,} ps)\n'
                  f'Slice ID: {slice_id}\n'
                  f'Parent: {parent}\n'
                  f'Depth: {depth}')

    return r


def to_svg(slices):
    slices_by_cpu_id = groupby_sorted(slices, exec_slice.cpu_id).items()
    for cpu_id, cpu_slices in slices_by_cpu_id:
        if not cpu_slices:
            continue

        trace_begin = min_key(cpu_slices, key=exec_slice.begin)
        trace_end = max_key(cpu_slices, key=exec_slice.end)
        max_depth = max_key(cpu_slices, key=lambda slce: exec_slice.depth(slce, -1))

        trace_duration = trace_end - trace_begin

        width = trace_duration / SVG_X_SCALE

        # +1 because of the thread_slice,
        # +1 because only one slice already needs at least 1 height,
        # and +1 to have some space at the top
        height = (max_depth + 3) * SVG_Y_UNIT

        svg = draw_svg.Drawing(width, height)

        for slice in cpu_slices:
            svg.append(exec_slice_to_rectangle(slice, trace_begin))

        svg.saveSvg(f'flamegraph-core{cpu_id}.svg')
