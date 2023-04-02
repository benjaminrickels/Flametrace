# Flametrace

Flametrace can generate per-core thread and function exectution flamegraph SVGs,
an SVG thread activity diagram, and runtime statistics from a gem5 `Trace.txt` file.

## Prerequisites and Dependencies

Tested on `Python 3.10.6`. To install all dependencies, simply run

```
python -m pip install -r requirements.txt
```

## Usage

As per usual the option `-h|--help` can be used to show some basic usage information.
Some more information regarding some of the options:

* `--limit LIMIT`:
  Can be used to limit the region that should be analyzed/plotted by  `flametrace`.
  Its argument `LIMIT` is of the form `<begin>:<end>` and specifies the begin and end of the region.

  `<begin>` and `<end>` must themselves be `limit_spec`s.
  A `limit_spec` can be of the form `<number>(%|a|c|s|t)`.
  Here `%` specifies a percentage of the entire trace duration at which the region should start/end,
  and `a` an absolute time (if specifying an absolute time, the `a`-suffix is optional).
  `c`, `s`, `t` specify the beginning/end of a *call*, *slice*, or *thread* respectively,
  at which the region itself should begin/end, and `<number>` that object's ID.
  If you want to specify a swapper thread for `<begin>`/`<end`>,
  you must use the `<limit_spec>` syntax `swapper/<cpu>`, as they all have ID 0.
  Additionally for the region of interest and the benchmark region,
  `roi` and `benchmark` can be used as `<limit_spec>`s as well.

  One of `<begin>` or `<end>` can be missing (keeping the `:` however, e.g. `<begin>:`),
  which results in a region that runs from the beginning of the trace to `<end>`,
  or from `<begin>` to the end of the trace respectively.
  For the `limit_spec` types `c`, `s`, `t`, as well as `roi` and `benchmark`,
  the syntax `<limit_spec>` can be used as a shorthand version of `<limit_spec>:<limit_spec>`.

* `--limit-context LIMIT_CONTEXT`:
  Can be used to include context around the `--limit` region.
  Its argument is a percentage, specifying how much context -
  in percent of the size of the original `--limit` region -
  should be included to the left *and* to the right.

* `--no-filter-pre-m5`:
  If specified,
  tracepoints before the first tracepoint belonging to the `m5` thread will be filtered from
  `Trace.txt`.
  This can be useful as sometimes the tracefile seems to be buggy before this point.

* `--no-trace-convert-to-cycles`:
  Do not convert the timestamps in the `Trace.txt` from picoseconds into cycles when parsing it.
  By default, `--cpu-ghz` (or its default value) will be used for the conversion.

* `--reset-cache`:
  When running, `flametrace` caches all slices (*before* applying any `--limit`s) for a tracefile to allow for faster subsequent generating of flamegraphs and statistics.
  If you do not want to use these cached slices (for example, because the tracefile has changed), you can use this option to force regeneration.

## Examples

1. Process the file `Trace.txt`, generating an SVG flamegraph and thread activity diagram

    `python3 flametrace.py --fg-svg`

2. Process the file `Trace2.txt`, generating an SVG flamegraph and thread activity diagram that spans only the region of interest

    `python3 flametrace.py Trace2.txt --fg-svg --limit roi`

3. Process multiple tracefiles (all beginning with the prefix "`Trace`"), generating an SVG flamegraph, thread activity diagram and statistical information that spans from the beginning of the ROI to the end of the trace

    `python3 flametrace.py Trace* --fg-svg --stats --limit roi:`

4. Process the file `Trace.txt`, generating an SVG flamegraph and thread activity diagram that spans just one slice from the flamegraph/activity diagram generated in example 1

    `python3 flametrace.py --fg-svg --limit <slice-id-as-seen-in-svg>s`


## Further Configuration

Some defaults and other things can be configured in `flametrace/config.py`
