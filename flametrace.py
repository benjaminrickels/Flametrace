from argparse import ArgumentParser

import flametrace.continuous_sequence as continuous_sequence
import flametrace.d3 as d3
import flametrace.exec_slice as exec_slice
import flametrace.svg as svg
import flametrace.tracefile as tracefile


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
            d3.to_json(slices)

        if args.svg_fg:
            svg.to_svg(slices)


if __name__ == '__main__':
    main()
