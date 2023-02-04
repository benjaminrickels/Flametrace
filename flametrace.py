from argparse import ArgumentParser

import flametrace.config as config
import flametrace.output.d3 as d3
import flametrace.exec_slice as exec_slice
import flametrace.output.stats as output_stats
import flametrace.stats as stats
import flametrace.output.svg as svg
import flametrace.tracefile as tracefile

import json


def _setup_parser():
    parser = ArgumentParser()

    parser.add_argument('tracefile', nargs='?', default='Trace.txt',
                        help='The tracefile (defaults to \'Trace.txt\')')

    parser.add_argument('--fg-d3', action='store_true',
                        help='Generate JSON files that can be used with the D3 flamegraph plotter')
    parser.add_argument('--fg-svg', action='store_true', help='Generate static SVG flamegraphs')

    parser.add_argument('--stats', action='store_true',
                        help='Generate a text file containing formatted function stats')
    parser.add_argument('--stats-json', action='store_true',
                        help='Generate a JSON file containing function stats')

    parser.add_argument('--cpu-ghz', action='store', type=float,
                        help='CPU frequency in GHz (defaults be configured in /flametrace/config.py)')
    parser.add_argument('--ignored-funs', action='store', type=json.loads,
                        help='A list of function/tracepoint names that should be ignored when building the list of execution slices (defaults can be configured in /flametrace/config.py)')

    return parser


def _parse_args():
    parser = _setup_parser()
    return parser.parse_args()


def main():
    args = _parse_args()

    if cpu_ghz := args.cpu_ghz:
        config.CPU_GHZ = cpu_ghz
    if ignored_funs := args.ignored_funs:
        config.IGNORED_FUNS = ignored_funs

    with open(args.tracefile) as tf:
        trace_entries = tracefile.parse(tf)

    if trace_entries:
        slices = exec_slice.find_all(trace_entries)

        if args.stats or args.stats_json:
            fun_stats = stats.get_function_stats(slices)

            if args.stats:
                with open('stats.txt', 'w') as sf:
                    sf.write(output_stats.stringify(fun_stats))

            if args.stats_json:
                with open('stats.json', 'w') as sf:
                    json.dump(fun_stats, sf)

        if args.fg_d3:
            d3.to_json(slices)

        if args.fg_svg:
            svg.to_svg(slices)


if __name__ == '__main__':
    main()
