from math import floor, log

import drawSvg as draw_svg

from flametrace.util import groupby_sorted, max_key, min_key, thread_uid_to_id
import flametrace.config as config

MAJOR_HEIGHT = 15
TEXT_HEIGHT = 60
Y_OFFSET = MAJOR_HEIGHT + TEXT_HEIGHT + 15

FIXED_COLORS = config.COLORS['fixed']
RANDOM_COLORS = config.COLORS['random']


def _thread_id_to_fill(thread_id):
    if color := FIXED_COLORS.get(thread_id):
        return color

    if thread_id == 0:
        return '#404040'
    elif thread_id < 1000:
        return '#C0C0C0'
    else:
        return RANDOM_COLORS[(thread_id - 1000) % len(RANDOM_COLORS)]


def _call_slice_infos(slce):
    infos = [f'Call ID: {slce.call_id}']
    if slce.is_call_begin and slce.is_call_end:
        infos.append('Is call begin and end')
    elif slce.is_call_begin:
        infos.append('Is call begin')
    elif slce.is_call_end:
        infos.append('Is call end')

    return infos


def _slice_info(slce):
    if slce.is_call_slice:
        slice_type_str = 'Call slice'
        call_name_str = f'{slce.call_name}:'
        type_infos = _call_slice_infos(slce)
    else:
        slice_type_str = 'Thread slice'
        call_name_str = ''
        type_infos = []

    id = slce.id
    thread_uid = slce.thread_uid
    if thread_name := slce.thread_name:
        thread_name_str = f' ({thread_name})'
    else:
        thread_name_str = ''

    infos = [f'Begin: {slce.begin}',
             f'End: {slce.end}',
             f'Duration: {slce.duration}']

    title_str = f'{slice_type_str} ({id}) - {call_name_str}{thread_uid}{thread_name_str} - CPU {slce.cpu_id}'
    infos_str = '\n'.join([f'  {info}' for info in [*infos, '', *type_infos]])

    return '\n'.join([title_str, infos_str])


def exec_slice_to_rectangle(slce, trace_begin, slice_x_factor, y, slice_height):
    thread_uid = slce.thread_uid

    slice_begin = slce.begin
    slice_end = slce.end
    slice_duration = slice_end - slice_begin

    x = (slice_begin - trace_begin) * slice_x_factor
    width = (slice_duration) * slice_x_factor
    fill = _thread_id_to_fill(thread_uid_to_id(thread_uid))

    slice_info = _slice_info(slce)

    r = draw_svg.Rectangle(x, y, width, slice_height, fill=fill,
                           stroke='black', stroke_width='0.2')
    r.appendTitle(slice_info)

    return r


def _tick_type_selector(i, min_step):
    if min_step == 'major':
        return 'major'
    elif min_step == 'med':
        if i % 10 == 0:
            return 'med'
        else:
            return 'major'
    elif min_step == 'minor':
        if i % 100 == 0:
            return 'major'
        elif i % 10 == 0:
            return 'med'
        else:
            return 'minor'


def _draw_axis_tick(svg, x, type_):
    if type_ == 'major':
        height = MAJOR_HEIGHT
    elif type_ == 'med':
        height = 2*MAJOR_HEIGHT / 3
    elif type_ == 'minor':
        height = MAJOR_HEIGHT / 3

    tick = draw_svg.Line(x, TEXT_HEIGHT, x, TEXT_HEIGHT+height, stroke='black', stroke_width='1')
    svg.append(tick)


def _draw_axis_ticks(svg, trace_duration, x_factor, axis_step):
    min_step = axis_step['min']
    step = axis_step['step']

    t = 0
    i = 0
    while t <= trace_duration:
        type_ = _tick_type_selector(i, min_step)
        _draw_axis_tick(svg, t * x_factor, type_)

        t += step
        i += 1


def _get_axis_step(trace_duration):
    major = 1
    while 10*major < trace_duration:
        major *= 10

    med = int(major / 10)
    minor = int(major / 100)

    if minor >= 1:
        return {'min': 'minor', 'step': minor}
    if med >= 1:
        return {'min': 'med', 'step': med}
    else:
        return {'min': 'major', 'step': major}


def _draw_axis(svg, trace_duration, x_factor):
    svg.append(draw_svg.Line(0, TEXT_HEIGHT, trace_duration*x_factor,
               TEXT_HEIGHT, stroke='black', stroke_width='2'))

    axis_step = _get_axis_step(trace_duration)
    step = axis_step['step']

    svg.append(draw_svg.Text(f'Step: {step}', 18, 0, TEXT_HEIGHT/2))

    _draw_axis_ticks(svg, trace_duration, x_factor, axis_step)


def _per_cpu_fg_to_svg(slices_by_cpu_id, width, height):
    for cpu_id, cpu_slices in slices_by_cpu_id.items():
        if not cpu_slices:
            continue

        trace_begin = min_key(cpu_slices, key=lambda s: s.begin)
        trace_end = max_key(cpu_slices, key=lambda s: s.end)
        max_depth = max_key(cpu_slices, key=lambda s: s.call_depth_or(-1))

        trace_duration = trace_end - trace_begin
        x_factor = width / trace_duration
        slice_height = (height - Y_OFFSET) / (max_depth + 2.5)

        svg = draw_svg.Drawing(width, height)

        _draw_axis(svg, trace_duration, x_factor)
        for slce in cpu_slices:
            depth = slce.call_depth_or(-1) + 1
            y = Y_OFFSET + depth*slice_height
            svg.append(exec_slice_to_rectangle(slce, trace_begin,
                       x_factor, y, slice_height))

        svg.saveSvg(f'flamegraph-core{cpu_id}.svg')


def _thread_activity_to_svg(slices, slices_by_cpu_id, width, height):
    trace_begin = min_key(slices, key=lambda s: s.begin)
    trace_end = max_key(slices, key=lambda s: s.end)
    cpus = len(slices_by_cpu_id.keys())

    trace_duration = trace_end - trace_begin
    x_factor = width / trace_duration
    slice_height = (height - Y_OFFSET) / (cpus * 1.5)

    svg = draw_svg.Drawing(width, height)

    _draw_axis(svg, trace_duration, x_factor)
    y = Y_OFFSET
    for cpu_slices in slices_by_cpu_id.values():
        for slce in cpu_slices:
            if slce.is_thread_slice:
                svg.append(exec_slice_to_rectangle(slce, trace_begin,
                                                   x_factor, y, slice_height))

        y += 1.5*slice_height

    svg.saveSvg(f'thread-activity.svg')


def to_svg(slices, width, height):
    height = max(height, Y_OFFSET + 200)

    slices_by_cpu_id = groupby_sorted(slices, lambda s: s.cpu_id)
    _per_cpu_fg_to_svg(slices_by_cpu_id, width, height)
    _thread_activity_to_svg(slices, slices_by_cpu_id, width, height)
