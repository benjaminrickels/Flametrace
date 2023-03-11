# Flametrace

Flametrace can generate per-core thread and function exectution flamegraph SVGs, a thread activity SVG, and runtime statistics from a gem5 `Trace.txt` file.

## Prerequisites and Dependencies

Tested on `Python 3.10.6`. To install all dependencies, simply run

```
python -m pip install -r requirements.txt
```

## Usage

As per usual the option `-h|--help` can be used to show some basic usage information.
Some more information regarding some of the options:

* `--limit LIMIT`:
  Can be used to specify a limit on the region that should be analyzed/plotted by  `flametrace`.
  Its argument `LIMIT` is of the form `<begin>:<end>`,
  which specifies the begin and end of the region.

  `<begin>` and `<end>` itself must be a `limit_spec`.
  A `limit_spec` can be of the form `<number>(%|a|c|s|t)`.
  `%` specifies a percentage of the entire trace duration at which the region should start/end,
  and `a` an absolute time (if specifying an absolute time, the `a`-suffix is optional).
  `c`, `s`, `t` specify the beginning/end of a *call*, *slice*, or *thread* respectively,
  at which the region should begin/end, and `<number>` that object's ID.
  If you want to specify a swapper thread for `<begin>`/`<end`>,
  you must use the `<limit_spec>` syntax `swapper/<cpu>`, as they all have ID 0.
  Additionally, for the region of interest and the benchmark region,
  `roi` and `benchmark` can be used as `<limit_spec>`s as well.

  One of `<begin>` or `<end>` can be missing (keeping the `:` however, e.g. `<begin>:`),
  which results in a region that runs from the beginning of the trace to `<end>`,
  or from `<begin>` to the end of the trace respectively.
  For the `limit_spec` types `c`, `s`, `t`, as well as `roi` and `benchmark`,
  the syntax `<limit_spec>` can be used as a short hand version of `<limit_spec>:<limit_spec>`.

* `--limit-context LIMIT_CONTEXT`:
  Can be used to draw some context around the `--limit` region.
  Its argument is a percentage, specifying how much context -
  in percent of the size of the original `--limit` region -
  should be included to the left *and* to the right.

* `--ignored-funs IGNORED_FUNS`:
  Can be used to ignore some functions when generating the flamegraphs.
  Useful, for buggy/missing `INST_TP_FUNC_ENTRY` and `INST_TP_FUNC_EXIT` tracepoints.
  `IGNORED_FUNS` should be a JSON list
  (i.e. with `'`s for names)
  of function/tracepoint names,
  that should be ignored.

* `--no-filter-pre-m5`:
  If specified,
  tracepoints before the first tracepoint belonging to the `m5` thread will be filtered from `Trace.txt`.
  This can be useful as sometimes the tracefile seems to be buggy before this point.

* `--no-trace-convert-to-cycles`:
  Do not convert the timestamps in the `Trace.txt` from picoseconds into cycles when parsing it.
  By default, `--cpu-ghz` (or its default value) will be used for the conversion.

## Further Configuration

Some defaults and other things can be configured in `flametrace/config.py`
