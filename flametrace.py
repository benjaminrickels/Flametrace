from argparse import ArgumentParser

import flametrace.continuous_sequence as continuous_sequence
import flametrace.d3 as d3
import flametrace.exec_slice as exec_slice
import flametrace.stats as stats
import flametrace.svg as svg
import flametrace.tracefile as tracefile

import json


def main():
    parser = ArgumentParser()

    parser.add_argument('tracefile', nargs='?', default='Trace.txt')

    parser.add_argument('--fg-d3', action='store_true',
                        help='Generate JSON files that can be used with the D3 flamegraph plotter')
    parser.add_argument('--fg-svg', action='store_true', help='Generate static SVG flamegraphs')

    parser.add_argument('--stats', action='store_true',
                        help='Generate a text file containing formatted function stats')
    parser.add_argument('--stats-json', action='store_true',
                        help='Generate a JSON file containing function stats')

    args = parser.parse_args()

    exec_slice.ignore_funs('registerThread', 'unregisterThread', 'start_pthread')

    with open(args.tracefile) as tf:
        tentries = tracefile.parse(tf)

    if tentries:
        cseqs = continuous_sequence.find_all(tentries)
        slices = exec_slice.find_all(cseqs)

        if args.stats or args.stats_json:
            fun_stats = stats.get_function_stats(slices)

            if args.stats:
                with open('stats.txt', 'w') as sf:
                    sf.write(stats.stringify_function_stats(fun_stats))

            if args.stats_json:
                with open('stats.json', 'w') as sf:
                    json.dump(fun_stats, sf)

        if args.fg_d3:
            d3.to_json(slices)

        if args.fg_svg:
            svg.to_svg(slices)


if __name__ == '__main__':
    main()
