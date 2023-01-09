import colorsys
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
    r.appendTitle(f'{function_name}{thread_uid}{thread_name}\n'
                  f'Begin: {slice_begin:,} ps\n'
                  f'End: {slice_end:,}ps \n'
                  f'Duration: {slice_duration:,} ps ({(slice_duration/500):,} cycles)')

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


def main():
    exec_slice.ignore_funs('registerThread', 'unregisterThread', 'start_pthread')

    with open('Trace.txt') as tf:
        tes = tracefile.parse(tf)

    if tes:
        c_seqs = continuous_sequence.find_all(tes)
        slices = exec_slice.find_all(c_seqs)
        per_cpu_exec_to_svg(slices)


if __name__ == '__main__':
    main()
