from argparse import ArgumentParser

import flametrace.config as config
import flametrace.output.d3 as d3
import flametrace.exec_slices as exec_slices
import flametrace.stats as stats
import flametrace.output.svg as svg
import flametrace.tracefile as tracefile
import flametrace.limit as Limit

import json
import os
import shutil


def _setup_parser():
    def limit(x):
        return Limit.parse(x)

    parser = ArgumentParser()

    parser.add_argument('tracefiles', nargs='*', default=['Trace.txt'],
                        help='The tracefile(s) (defaults to \'Trace.txt\')')

    parser.add_argument('--limit', action='store', type=limit)
    parser.add_argument('--limit-context', action='store', type=float, default=0)

    parser.add_argument('--cpu-ghz', action='store', type=float,
                        help='CPU frequency in GHz (defaults can be configured in flametrace/config.py)')
    parser.add_argument('--no-filter-pre-m5', action='store_true', default=False,
                        help=('do not filter entries from the tracefile that appear before the first entry belonging '
                              'to the m5 thread'))
    parser.add_argument('--no-trace-convert-to-cycles', action='store_true', default=False,
                        help=('do not convert timestamps (in the tracefile) to cycles and keep them in picoseconds'
                              '(defaults can be configured in flametrace/config.py)'))
    parser.add_argument('--throw', action='store_true', default=False,
                        help=('When specified and more than one tracefile is specified, throw and exit the program at'
                              'the first exception'))

    output_group = parser.add_argument_group('Output')
    output_group.add_argument('--fg-d3', action='store_true',
                              help='generate JSON files that can be used with the D3 flamegraph plotter')
    output_group.add_argument('--fg-svg', action='store_true',
                              help='generate static SVG flamegraphs')
    output_group.add_argument('--fg-svg-width', action='store', type=int, default=2000,
                              help='width of the SVG flamegraph (in pixels)')
    output_group.add_argument('--fg-svg-height', action='store', type=int, default=700,
                              help='height of the SVG flamegraph (in pixels)')

    output_group.add_argument('--stats', action='store_true',
                              help='generate JSON files containing stats')

    return parser


def _parse_args():
    parser = _setup_parser()
    return parser.parse_args()


def _results_dir(tracefile):
    cwd = os.getcwd()
    return f'{cwd}/ft-results--{tracefile}'


def _setup_results_dir(tracefile):
    dir = _results_dir(tracefile)

    if os.path.exists(dir):
        shutil.rmtree(dir)

    os.mkdir(dir)
    os.chdir(dir)


def _run1(tracefile_name, args):
    if os.path.isdir(tracefile_name):
        return

    cwd = os.getcwd()

    try:
        with open(tracefile_name) as tf:
            events = tracefile.parse(tf, filter_pre_m5=not args.no_filter_pre_m5)

        _setup_results_dir(tracefile_name)

        benchmark_events = tracefile.benchmark_events(events)

        if events:
            slices = exec_slices.find_all(events)
            if limit := args.limit:
                slices = exec_slices.limit(slices,
                                           limit,
                                           args.limit_context,
                                           benchmark_events)

            if args.stats:
                stats_ = stats.compute_stats(slices)
                for stat_group, group_stats in stats_.items():
                    with open(f'stats-{stat_group}.json', 'w') as sf:
                        json.dump(group_stats, sf, indent=4)

            if args.fg_d3:
                d3.to_json(slices)

            if args.fg_svg:
                svg.to_svg(slices, args.fg_svg_width, args.fg_svg_height)
    except Exception:
        raise
    finally:
        os.chdir(cwd)


def _try_run1(tracefile, args):
    try:
        _run1(tracefile, args)
        print(f'"{tracefile}" done')
    except Exception as e:
        print(f'ERROR: when processing "{tracefile}": {repr(e)}')
        if len(args.tracefiles) == 1 or args.throw:
            raise e


def main():
    args = _parse_args()

    if cpu_ghz := args.cpu_ghz:
        config.CPU_GHZ = cpu_ghz
    if args.no_trace_convert_to_cycles:
        config.TRACE_CONVERT_TO_CYCLES = False

    for tracefile in args.tracefiles:
        _try_run1(tracefile, args)


if __name__ == '__main__':
    main()
