import json
import math

####################################################################################################
# Boxplot stuff
####################################################################################################


def _halve(xs):
    n = len(xs)

    if n <= 1:
        return ([], [])

    hn = int(n / 2)

    xs_low = xs[0:hn]
    xs_high = xs[hn:n] if n % 2 == 0 else xs[hn + 1:n]

    return (xs_low, xs_high)


def _median(xs, default=None):
    n = len(xs)

    if n == 0:
        return default

    hn = int(n / 2)

    median = xs[hn]
    return median if n % 2 != 0 else (median + xs[hn - 1]) / 2


def _quartile_stats(xs):
    min = xs[0]
    max = xs[-1]

    median = q2 = _median(xs)
    xs_low, xs_high = _halve(xs)
    q1 = _median(xs_low, q2)
    q3 = _median(xs_high, q2)
    iqr = q3 - q1

    filtered_xs = [x for x in xs if x >= (q1 - 1.5*iqr) and (x <= q3 + 1.5*iqr)]
    q0 = filtered_xs[0]
    q4 = filtered_xs[-1]

    return {'median': median,
            'min': min,
            'max': max,
            'q0': q0,
            'q1': q1,
            'q2': q2,
            'q3': q3,
            'q4': q4,
            'iqr': iqr}


####################################################################################################

FAIR_SCHED_HOOKS = ['enqueue_task_fair',
                    'dequeue_task_fair',
                    'yield_task_fair',
                    'yield_to_task_fair',
                    'check_preempt_wakeup',
                    'pick_next_task_fair',
                    'put_prev_task_fair',
                    'set_next_task_fair',
                    'balance_fair',
                    'select_task_rq_fair',
                    'migrate_task_rq_fair',
                    'rq_online_fair',
                    'rq_offline_fair',
                    'task_dead_fair',
                    'task_tick_fair',
                    'task_fork_fair',
                    'prio_changed_fair',
                    'switched_from_fair',
                    'switched_to_fair',
                    'get_rr_interval_fair',
                    'update_curr_fair',
                    'task_change_group_fair', ]
FAIR_SCHED_FUNS = [*FAIR_SCHED_HOOKS,
                   'enqueue_entity',
                   '__enqueue_entity',
                   'dequeue_entity',
                   '__dequeue_entity',
                   'pick_next_entity',
                   'put_prev_entity',
                   'set_next_entity',
                   'update_curr',
                   'check_preempt_tick',
                   'entity_tick',
                   'place_entity']

RT_SCHED_HOOKS = ['enqueue_task_rt',
                  'dequeue_task_rt',
                  'yield_task_rt',
                  'check_preempt_curr_rt',
                  'pick_next_task_rt',
                  'put_prev_task_rt',
                  'set_next_task_rt',
                  'balance_rt',
                  'select_task_rq_rt',
                  'rq_online_rt',
                  'rq_offline_rt',
                  'task_woken_rt',
                  'switched_from_rt',
                  'task_tick_rt',
                  'get_rr_interval_rt',
                  'prio_changed_rt',
                  'switched_to_rt',
                  'update_curr_rt', ]
RT_SCHED_FUNS = [*RT_SCHED_HOOKS,
                 'rt_queue_push_tasks',
                 'rt_queue_pull_tasks',
                 'enqueue_pushable_task',
                 'dequeue_pushable_task',
                 'sched_rt_rq_enqueue',
                 'sched_rt_rq_dequeue',
                 'dequeue_top_rt_rq',
                 'enqueue_top_rt_rq',
                 '__enqueue_rt_entity',
                 '__dequeue_rt_entity',
                 'dequeue_rt_stack',
                 'enqueue_rt_entity',
                 'dequeue_rt_entity',
                 'requeue_rt_entity',
                 'requeue_task_rt',
                 'pick_next_rt_entity',
                 '_pick_next_task_rt',
                 'pick_highest_pushable_task',
                 'find_lowest_rq',
                 'find_lock_lowest_rq',
                 'pick_next_pushable_task',
                 'push_rt_task',
                 'push_rt_tasks',
                 'pull_rt_task']

SCHED_CLASS_FUNS = {'CFS': FAIR_SCHED_FUNS,
                    'RT': RT_SCHED_FUNS}

CORE_SCHED_FUNS = ['schedule',
                   '__schedule',
                   'migrate_task',
                   'pick_next_task',
                   'context_switch',
                   'try_to_wake_up',
                   'move_queued_task',
                   'scheduler_tick',
                   'resched_curr']

# Python list flattening and expanding... Yikes!
SCHED_FUNS = [*CORE_SCHED_FUNS, *[fun for funs in SCHED_CLASS_FUNS.values() for fun in funs]]

####################################################################################################
# Sched-stats functions
####################################################################################################


def _sched_active_time(function_stats):
    sched_active_time = {c: 0 for c in SCHED_CLASS_FUNS.keys()}
    sched_active_time['all'] = 0

    for sched_fun in SCHED_FUNS:
        if function_stats_ := function_stats.get(sched_fun):
            active_time_self = function_stats_['active-time-self']
            sched_active_time['all'] += active_time_self
            for sched_class, class_funs in SCHED_CLASS_FUNS.items():
                if sched_fun in class_funs:
                    sched_active_time[sched_class] += active_time_self

    return sched_active_time


def _sched_active_time_perc(trace_stats, function_stats):
    cpu_active_time = trace_stats['cpus-active-time']
    sched_active_time = _sched_active_time(function_stats)

    sched_active_time_perc = {c: 100 * (t / cpu_active_time)
                              for c, t in sched_active_time.items()}

    return sched_active_time_perc


def _assoc_sched_active_time_percs(benchmarks):
    for obj in benchmarks.values():
        trace_stats = obj['trace_stats']
        function_stats = obj['function_stats']

        sched_active_time_perc = _sched_active_time_perc(trace_stats, function_stats)
        obj['sched_active_time_perc'] = sched_active_time_perc


WEIGHTED_AVG = True


def _fun_avg_boxplot(function, benchmarks, self_only):
    fun_active_times = []
    for obj in benchmarks.values():
        if fun_stats := obj['function_stats'].get(function):
            iqr_stats = fun_stats['active-time-self-iqr'] if self_only else fun_stats['active-time-iqr']
            q0 = iqr_stats['q0']
            q1 = iqr_stats['q1']
            q2 = iqr_stats['q2']
            q3 = iqr_stats['q3']
            q4 = iqr_stats['q4']

            weight = obj.get('weight', 1) if WEIGHTED_AVG else 1
            for _ in range(0, weight):
                fun_active_times.append(q0)
                fun_active_times.append(q1)
                fun_active_times.append(q2)
                fun_active_times.append(q3)
                fun_active_times.append(q4)

    if not fun_active_times:
        return None

    return _quartile_stats(sorted(fun_active_times))


def _funs_avg_boxplots(functions, benchmarks, self_only):
    fun_active_time_boxplots = {}
    for function in functions:
        if boxplot := _fun_avg_boxplot(function, benchmarks, self_only):
            fun_active_time_boxplots[function] = boxplot

    return fun_active_time_boxplots


def _fun_per_bm_boxplots(function, benchmarks, self_only):
    fun_active_time_boxplots = {}
    for bm, obj in benchmarks.items():
        if fun_stats := obj['function_stats'].get(function):
            fun_active_time_boxplots[bm] = fun_stats['active-time-self-iqr'] if self_only else fun_stats['active-time-iqr']

    return fun_active_time_boxplots

####################################################################################################
# PGFPlots boxplot functions
####################################################################################################


def _begin_boxplot(f, boxplots, yticklabels, y=0.55, width=0.7, xtick_distance=None):
    xtick_distance_str = f'  xtick distance={{{xtick_distance}}},\n' if xtick_distance else ''
    ytick_str = ','.join(map(str, range(1, len(boxplots)+1)))
    yticklabels_str = ','.join(yticklabels) if yticklabels else ',,'

    if len(boxplots) == 1:
        y_min_max_str = 'ymin=0.3, ymax=1.7\n,'
    else:
        y_min_max_str = ''

    f.write(('\\begin{tikzpicture}\n'
            '\\begin{axis} [\n'
             f'{xtick_distance_str}'
             '  xlabel={cycles},\n'
             '  yticklabel={\\texttt{\\tick}},\n'
             '  y dir=reverse,\n'
             '  xmajorgrids,\n'
             '  xmin=0,\n'
             '  boxplot/box extend=0.6,\n'
             f'{y_min_max_str}'
             f'  width={width}\\textwidth,\n'
             f'  y={y}cm,\n'
             f'  ytick={{{ytick_str}}},\n'
             f'  yticklabels={{{yticklabels_str}}}]\n'))


def _add_boxplots(f, boxplots, last_highlighted):
    for i, boxplot in enumerate(boxplots):
        q0 = boxplot['q0']
        q1 = boxplot['q1']
        q2 = boxplot['q2']
        q3 = boxplot['q3']
        q4 = boxplot['q4']

        if last_highlighted and i == len(boxplots) - 1:
            draw = 'red'
            fill = 'red!30!white'
        else:
            draw = 'blue'
            fill = 'blue!30!white'
        f.write(
            ('\\addplot [\n'
                f'  fill={fill},\n'
                f'  draw={draw},\n'
                f'  boxplot prepared={{lower whisker={q0}, lower quartile={q1}, median={q2}, upper quartile={q3}, upper whisker={q4}}}]\n'
                '  coordinates {};\n'))


def _end_boxplot(f):
    f.write(('\\end{axis}\n'
             '\\end{tikzpicture}\n'))


def draw_boxplots(f, boxplots, yticklabels, last_highlighted, width, y, xtick_distance=None):
    _begin_boxplot(f, boxplots, yticklabels, y, width, xtick_distance)
    _add_boxplots(f, boxplots, last_highlighted)
    _end_boxplot(f)

####################################################################################################
# LaTeX boxplot tabular functions
####################################################################################################


def _begin_boxplot_tabular(f):
    f.write(('\\begin{tabularx}{\\textwidth}{L R R R R R}\n'
            '  \\toprule'
             '  \\textbf{Benchmark} & \\textbf{Min} & \\textbf{Q1} & \\textbf{Median} & \\textbf{Q3} & \\textbf{Max}\\\\\n'
             '  \\midrule\n'))


def _add_boxplot_tabular_rows(f, rows):
    summary_rows = False

    for row in rows:
        if row == 'summary':
            f.write('  \\midrule\n')
            summary_rows = True
        else:
            for j, entry in enumerate(row):
                if j == 0:
                    if summary_rows:
                        entry_str = f'  \\textbf{{{entry}}}'
                    else:
                        entry_str = f'  \\small{{{entry}}}'
                else:
                    entry_str = f'\\scriptsize{{{entry}}}'

                suffix = '' if j == len(row) - 1 else ' & '

                f.write(f'{entry_str}{suffix}')

            f.write('\\\\\n')

    f.write('\n')


def _end_boxplot_tabular(f):
    f.write(('  \\bottomrule\n'
             '\\end{tabularx}'))


def _draw_boxplot_tabular(f, rows):
    _begin_boxplot_tabular(f)
    _add_boxplot_tabular_rows(f, rows)
    _end_boxplot_tabular(f)


def draw_boxplot_tables(f, funs):
    for fun, rows in funs:
        f.write(('\\begin{table}[ht]\n'
                '\centering'))

        _draw_boxplot_tabular(f, rows)

        caption_short = f'{_latexify_function(fun)} duration distribution'
        caption_long = f'{caption_short} (cycles)'
        f.write((f'\\caption[{caption_short}]{{{caption_long}}}\n'
                f'\\label{{tab:{fun}-duration-dist}}\n'
                 '\\end{table}\n'))

####################################################################################################
# Output functions
####################################################################################################


def _latexify_function(fun):
    fun = fun.replace('_', '\\_')
    return f'\\texttt{{{fun}}}'


def sched_active_time_perc_csv(benchmarks, suffix):
    max_relevant_classes = max([len(obj['relevant_classes']) for obj in benchmarks.values()])

    assert max_relevant_classes > 0
    assert max_relevant_classes <= 2

    with open(f'sched-active-time-perc-{suffix}.csv', 'w') as f:
        if max_relevant_classes == 1:
            f.write('BM SAT CFSRTSAT\n')
        else:
            f.write('BM SAT CFSSAT RTSAT\n')

        for bm, obj in benchmarks.items():
            sched_active_time_perc = obj['sched_active_time_perc']
            relevant_classes = obj['relevant_classes']
            sched_active_time_perc_all = sched_active_time_perc['all']

            f.write(f'{{\\small{{{bm}}}}} {sched_active_time_perc_all} ')
            if max_relevant_classes == 1:
                f.write(
                    f'{sched_active_time_perc[relevant_classes[0]]}\n')
            else:
                if 'CFS' in relevant_classes:
                    f.write(f'{sched_active_time_perc["CFS"]}')
                else:
                    f.write('{}')

                f.write(' ')

                if 'RT' in relevant_classes:
                    f.write(f'{sched_active_time_perc["RT"]}')
                else:
                    f.write('{}')

                f.write('\n')


def funs_avg_boxplots_pgfplots(functions, benchmarks, suffix, self_only=False, width=0.7, y=0.55, xtick_distance=None, no_labels=False):
    with open(f'boxplots-pgf-avg-{suffix}{"-self" if self_only else ""}.tex', 'w') as f:
        boxplots = _funs_avg_boxplots(functions, benchmarks, self_only)

        yticklabels = map(lambda x: f'\small{{{_latexify_function(x)}}}',
                          boxplots.keys()) if not no_labels else None

        draw_boxplots(f, boxplots.values(), yticklabels, False, width, y, xtick_distance)


def fun_per_bm_boxplots_pgfplots(function, benchmarks, overall_benchmarks=False, suffix=None, self_only=False, y=0.55, width=0.7, xtick_distance=None, no_labels=False):
    suffix = f'-{suffix}' if suffix else ''

    with open(f'boxplots-pgf-fun-{function}{suffix}{"-self" if self_only else ""}.tex', 'w') as f:
        boxplots = _fun_per_bm_boxplots(function, benchmarks, self_only)

        yticklabels = list(map(lambda x: f'\small{{{x}}}',
                           boxplots.keys())) if not no_labels else None
        boxplots = list(boxplots.values())

        if overall_benchmarks:
            if overall_benchmarks == True:
                overall_benchmarks = benchmarks
            else:
                # overall_benchmarks is a map of benchmarks to be used for the overall calculation
                pass

            overall_boxplot = _fun_avg_boxplot(function, overall_benchmarks, self_only=self_only)
            if yticklabels:
                yticklabels.append('\\textbf{Overall}')
            boxplots.append(overall_boxplot)

        draw_boxplots(f, boxplots, yticklabels, overall_benchmarks, width, y, xtick_distance)


def _dur_pair(dur, dur_self):
    if dur != dur_self:
        return f'{int(dur)} ({int(dur_self)})'
    else:
        return int(dur)


def _row_data_from_boxplot(duration_boxplot, self_duration_boxplot):
    if not (duration_boxplot and self_duration_boxplot):
        return

    q0 = duration_boxplot['q0']
    q1 = duration_boxplot['q1']
    q2 = duration_boxplot['q2']
    q3 = duration_boxplot['q3']
    q4 = duration_boxplot['q4']

    q0_s = self_duration_boxplot['q0']
    q1_s = self_duration_boxplot['q1']
    q2_s = self_duration_boxplot['q2']
    q3_s = self_duration_boxplot['q3']
    q4_s = self_duration_boxplot['q4']

    return [_dur_pair(d, ds) for d, ds in [[q0, q0_s],
                                           [q1, q1_s],
                                           [q2, q2_s],
                                           [q3, q3_s],
                                           [q4, q4_s]]]


def boxplot_tables(functions, benchmarks, cpu_benchmarks, io_benchmarks, suffix):
    with open(f'tables-boxplot-{suffix}.tex', 'w') as f:
        fun_tables = []
        for fun in sorted(functions):
            fun_duration_boxplots = _fun_per_bm_boxplots(fun, benchmarks, False)

            if not fun_duration_boxplots:
                continue

            fun_duration_self_boxplots = _fun_per_bm_boxplots(fun, benchmarks, True)

            fun_duration_avg_boxplot = _fun_avg_boxplot(fun, benchmarks, self_only=False)
            fun_duration_self_avg_boxplot = _fun_avg_boxplot(fun, benchmarks, self_only=True)

            fun_duration_cpu_avg_boxplot = _fun_avg_boxplot(fun, cpu_benchmarks, self_only=False)
            fun_duration_self_cpu_avg_boxplot = _fun_avg_boxplot(
                fun, cpu_benchmarks, self_only=True)

            fun_duration_io_avg_boxplot = _fun_avg_boxplot(fun, io_benchmarks, self_only=False)
            fun_duration_self_io_avg_boxplot = _fun_avg_boxplot(fun, io_benchmarks, self_only=True)

            rows = []
            for bm in fun_duration_boxplots.keys():
                row_data = _row_data_from_boxplot(fun_duration_boxplots[bm],
                                                  fun_duration_self_boxplots[bm])
                row = [bm, *row_data]
                rows.append(row)

            overall_data = _row_data_from_boxplot(
                fun_duration_avg_boxplot, fun_duration_self_avg_boxplot)
            overall_cpu_data = _row_data_from_boxplot(
                fun_duration_cpu_avg_boxplot, fun_duration_self_cpu_avg_boxplot)
            overall_io_data = _row_data_from_boxplot(
                fun_duration_io_avg_boxplot, fun_duration_self_io_avg_boxplot)

            rows.append('summary')

            if overall_cpu_data and overall_io_data:
                row_cpu = ['CPU-bound', *overall_cpu_data]
                row_io = ['IO-bound', *overall_io_data]
                rows.append(row_cpu)
                rows.append(row_io)

            row = ['Overall', *overall_data]
            rows.append(row)

            fun_tables.append([fun, rows])

        draw_boxplot_tables(f, fun_tables)

####################################################################################################
# main
####################################################################################################


def select_from(map, keys):
    return {k: v for k, v in map.items() if k in keys}


def _weight(weight1, weight2, weight3):
    return weight1 * weight2 * weight3


BENCHMARKS = {'CFS 8': {'file': 'Trace__synth_cfs_8.txt',
                        'boundedness': 'CPU',
                        'relevant_classes': ['CFS'],
                        'weight': _weight(10, 90, 40)},
              'CFS 16': {'file': 'Trace__synth_cfs_16.txt',
                         'boundedness': 'CPU',
                         'relevant_classes': ['CFS'],
                         'weight': _weight(15, 90, 40)},
              'CFS 32': {'file': 'Trace__synth_cfs_32.txt',
                         'boundedness': 'CPU',
                         'relevant_classes': ['CFS'],
                         'weight': _weight(30, 90, 40)},
              'CFS 64': {'file': 'Trace__synth_cfs_64.txt',
                         'boundedness': 'CPU',
                         'relevant_classes': ['CFS'],
                         'weight': _weight(30, 90, 40)},
              'CFS 128': {'file': 'Trace__synth_cfs_128.txt',
                          'boundedness': 'CPU',
                          'relevant_classes': ['CFS'],
                          'weight': _weight(15, 90, 40)},
              'FIFO 8': {'file': 'Trace__synth_fifo_8.txt',
                         'boundedness': 'CPU',
                         'relevant_classes': ['RT'],
                         'weight': _weight(75, 2, 40)},
              'FIFO 16': {'file': 'Trace__synth_fifo_16.txt',
                          'boundedness': 'CPU',
                          'relevant_classes': ['RT'],
                          'weight': _weight(15, 2, 40)},
              'FIFO 32': {'file': 'Trace__synth_fifo_32.txt',
                          'boundedness': 'CPU',
                          'relevant_classes': ['RT'],
                          'weight': _weight(8, 2, 40)},
              'FIFO 64': {'file': 'Trace__synth_fifo_64.txt',
                          'boundedness': 'CPU',
                          'relevant_classes': ['RT'],
                          'weight': _weight(2, 2, 40)},
              'RR 8': {'file': 'Trace__synth_rr_8.txt',
                       'boundedness': 'CPU',
                       'relevant_classes': ['RT'],
                       'weight': _weight(50, 7, 40)},
              'RR 16': {'file': 'Trace__synth_rr_16.txt',
                        'boundedness': 'CPU',
                        'relevant_classes': ['RT'],
                        'weight': _weight(30, 7, 40)},
              'RR 32': {'file': 'Trace__synth_rr_32.txt',
                        'boundedness': 'CPU',
                        'relevant_classes': ['RT'],
                        'weight': _weight(15, 7, 40)},
              'RR 64': {'file': 'Trace__synth_rr_64.txt',
                        'boundedness': 'CPU',
                        'relevant_classes': ['RT'],
                        'weight': _weight(5, 7, 40)},
              'FIFO rand 8': {'file': 'Trace__synth_fifo_rand_8.txt',
                              'boundedness': 'CPU',
                              'relevant_classes': ['RT'],
                              'weight': _weight(60, 1, 40)},
              'FIFO rand 16': {'file': 'Trace__synth_fifo_rand_16.txt',
                               'boundedness': 'CPU',
                               'relevant_classes': ['RT'],
                               'weight': _weight(20, 1, 40)},
              'FIFO rand 32': {'file': 'Trace__synth_fifo_rand_32.txt',
                               'boundedness': 'CPU',
                               'relevant_classes': ['RT'],
                               'weight': _weight(10, 1, 40)},
              'FIFO rand 64': {'file': 'Trace__synth_fifo_rand_64.txt',
                               'boundedness': 'CPU',
                               'relevant_classes': ['RT'],
                               'weight': _weight(5, 1, 40)},
              'Lib CFS 4/1': {'file': 'Trace__lib_cfs_4_1_32_1200.txt',
                              'boundedness': 'IO',
                              'relevant_classes': ['CFS'],
                              'weight': _weight(30, 90, 60)},
              'Lib CFS 5/1': {'file': 'Trace__lib_cfs_5_1_32_1200.txt',
                              'boundedness': 'IO',
                              'relevant_classes': ['CFS'],
                              'weight': _weight(20, 90, 60)},
              'Lib CFS 6/1': {'file': 'Trace__lib_cfs_6_1_32_1200.txt',
                              'boundedness': 'IO',
                              'relevant_classes': ['CFS'],
                              'weight': _weight(20, 90, 60)},
              'Lib CFS 7/1': {'file': 'Trace__lib_cfs_7_1_32_1200.txt',
                              'boundedness': 'IO',
                              'relevant_classes': ['CFS'],
                              'weight': _weight(20, 90, 60)},
              'Lib CFS 8/1': {'file': 'Trace__lib_cfs_8_1_32_1200.txt',
                              'boundedness': 'IO',
                              'relevant_classes': ['CFS'],
                              'weight': _weight(10, 90, 60)},
              'Lib FIFO 4/1': {'file': 'Trace__lib_fifo_4_1_32_5000.txt',
                               'boundedness': 'IO',
                               'relevant_classes': ['CFS', 'RT'],
                               'weight': _weight(35, 10, 60)},
              'Lib FIFO 5/1': {'file': 'Trace__lib_fifo_5_1_32_4000.txt',
                               'boundedness': 'IO',
                               'relevant_classes': ['CFS', 'RT'],
                               'weight': _weight(20, 10, 60)},
              'Lib FIFO 6/1': {'file': 'Trace__lib_fifo_6_1_32_4000.txt',
                               'boundedness': 'IO',
                               'relevant_classes': ['CFS', 'RT'],
                               'weight': _weight(20, 10, 60)},
              'Lib FIFO 7/1': {'file': 'Trace__lib_fifo_7_1_32_4000.txt',
                               'boundedness': 'IO',
                               'relevant_classes': ['CFS', 'RT'],
                               'weight': _weight(15, 10, 60)},
              'Lib FIFO 8/1': {'file': 'Trace__lib_fifo_8_1_32_4000.txt',
                               'boundedness': 'IO',
                               'relevant_classes': ['CFS', 'RT'],
                               'weight': _weight(10, 10, 60)}, }


def _norm_weight(bms):
    weight_gcd = math.gcd(*list(map(lambda x: x['weight'], bms.values())))

    for obj in bms.values():
        obj['weight'] = int(obj['weight'] / weight_gcd)


if __name__ == '__main__':
    remove_bms = []

    for bm, obj in BENCHMARKS.items():
        path = f'ft-results--{obj["file"]}'
        try:
            with open(f'{path}/stats-trace.json') as f:
                BENCHMARKS[bm]['trace_stats'] = json.load(f)
            with open(f'{path}/stats-function.json') as f:
                BENCHMARKS[bm]['function_stats'] = json.load(f)
        except FileNotFoundError:
            print(f'Benchmark "{bm}" stats not found...')
            remove_bms.append(bm)

    for bm in remove_bms:
        BENCHMARKS.pop(bm)

    _norm_weight(BENCHMARKS)

    _assoc_sched_active_time_percs(BENCHMARKS)

    cpu_bound_bms = {bm: obj for bm, obj in BENCHMARKS.items() if obj['boundedness'] == 'CPU'}
    io_bound_bms = {bm: obj for bm, obj in BENCHMARKS.items() if obj['boundedness'] == 'IO'}

    # Sched active time

    sched_active_time_perc_csv(select_from(cpu_bound_bms,
                                           ['CFS 8',
                                            'CFS 32',
                                            'CFS 128',
                                            'FIFO 8',
                                            'FIFO 64',
                                            'RR 8',
                                            'RR 64',
                                            'FIFO rand 8',
                                            'FIFO rand 64']),
                               'cpu')
    sched_active_time_perc_csv(select_from(io_bound_bms,
                                           ['Lib CFS 4/1',
                                            'Lib CFS 6/1',
                                            'Lib CFS 8/1',
                                            'Lib FIFO 4/1',
                                            'Lib FIFO 6/1',
                                            'Lib FIFO 8/1']),
                               'io')

    cfs_bms = {bm: obj for bm, obj in BENCHMARKS.items() if 'CFS' in obj['relevant_classes']}
    cfs_cpu_bms = select_from(cfs_bms, cpu_bound_bms.keys())
    cfs_io_bms = select_from(cfs_bms, io_bound_bms.keys())

    rt_bms = {bm: obj for bm, obj in BENCHMARKS.items() if 'RT' in obj['relevant_classes']}
    rt_cpu_bms = select_from(rt_bms, cpu_bound_bms.keys())
    rt_io_bms = select_from(rt_bms, io_bound_bms.keys())

    #
    # Core stuff
    #

    ## Schedule and subfuns
    funs_avg_boxplots_pgfplots(['__schedule',
                                'pick_next_task',
                                'context_switch', ],
                               BENCHMARKS, '__schedule-and-subfuns', False)

    # Schedule CPU and IO
    schedule_cpu_bms = select_from(BENCHMARKS,
                                   ['CFS 8', 'CFS 128', 'FIFO 8', 'FIFO 64', 'RR 64', 'FIFO rand 64'])
    schedule_io_bms = select_from(BENCHMARKS,
                                  ['Lib CFS 4/1', 'Lib CFS 6/1', 'Lib CFS 8/1', 'Lib FIFO 4/1', 'Lib FIFO 6/1', 'Lib FIFO 8/1'])

    fun_per_bm_boxplots_pgfplots('__schedule', schedule_cpu_bms,
                                 overall_benchmarks=cpu_bound_bms, width=0.8, suffix='cpu')
    fun_per_bm_boxplots_pgfplots('__schedule', schedule_io_bms,
                                 overall_benchmarks=io_bound_bms, width=0.8, suffix='io')

    # Subfuns CPU and IO
    funs_avg_boxplots_pgfplots(['pick_next_task',
                                'context_switch', ],
                               cpu_bound_bms, '__schedule-subfuns-cpu', False, width=0.75)
    funs_avg_boxplots_pgfplots(['pick_next_task',
                                'context_switch', ],
                               io_bound_bms, '__schedule-subfuns-io', False, no_labels=True, width=1.05)

    # Scheduler tick
    scheduler_tick_bms_1 = select_from(BENCHMARKS,
                                       ['CFS 8', 'CFS 128', 'RR 8', 'FIFO rand 64', 'Lib CFS 4/1', 'Lib CFS 8/1'])
    scheduler_tick_overall_bms_1 = {k: v for k,
                                    v in BENCHMARKS.items() if not k.startswith('Lib FIFO')}
    scheduler_tick_bms_2 = select_from(BENCHMARKS,
                                       ['Lib FIFO 4/1', 'Lib FIFO 5/1', 'Lib FIFO 6/1', 'Lib FIFO 7/1', 'Lib FIFO 8/1', ])
    scheduler_tick_overall_bms_2 = {k: v for k,
                                    v in BENCHMARKS.items() if k.startswith('Lib FIFO')}

    fun_per_bm_boxplots_pgfplots('scheduler_tick', scheduler_tick_bms_1,
                                 overall_benchmarks=scheduler_tick_overall_bms_1, suffix='1', width=0.83)
    fun_per_bm_boxplots_pgfplots('scheduler_tick', scheduler_tick_bms_2,
                                 overall_benchmarks=scheduler_tick_overall_bms_2, suffix='2', width=0.83)

    funs_avg_boxplots_pgfplots(['scheduler_tick'], BENCHMARKS, 'scheduler-tick', no_labels=True)

    #
    # Fair stuff
    #

    # Hooks
    cfs_hooks = ['enqueue_task_fair',
                 'dequeue_task_fair',
                 'pick_next_task_fair',
                 'task_tick_fair']
    funs_avg_boxplots_pgfplots(cfs_hooks, cfs_bms, 'main-cfs-hooks', False)
    funs_avg_boxplots_pgfplots(cfs_hooks, cfs_cpu_bms, 'main-cfs-hooks-cpu', False, width=0.65)
    funs_avg_boxplots_pgfplots(cfs_hooks, cfs_io_bms, 'main-cfs-hooks-io',
                               False, no_labels=True, width=1.05)

    # Pick next task fair
    pick_next_task_fair_bms_1 = cfs_cpu_bms
    pick_next_task_fair_bms_2 = select_from(BENCHMARKS,
                                            ['Lib CFS 4/1', 'Lib CFS 5/1', 'Lib CFS 8/1', 'Lib FIFO 4/1', 'Lib FIFO 8/1', ])

    fun_per_bm_boxplots_pgfplots('pick_next_task_fair', pick_next_task_fair_bms_1,
                                 overall_benchmarks=cfs_cpu_bms, suffix='cpu', width=0.83)
    fun_per_bm_boxplots_pgfplots('pick_next_task_fair', pick_next_task_fair_bms_2,
                                 overall_benchmarks=cfs_io_bms, suffix='io', width=0.8)

    # Task tick fair
    task_tick_fair_bms_1 = select_from(
        BENCHMARKS, ['CFS 8', 'CFS 32', 'CFS 128', 'Lib CFS 4/1', 'Lib CFS 8/1'])
    task_tick_fair_overall_bms_1 = scheduler_tick_overall_bms_1
    task_tick_fair_bms_2 = scheduler_tick_bms_2
    task_tick_fair_overall_bms_2 = scheduler_tick_overall_bms_2

    fun_per_bm_boxplots_pgfplots('task_tick_fair', task_tick_fair_bms_1,
                                 overall_benchmarks=task_tick_fair_overall_bms_1, suffix='1', width=0.8)
    fun_per_bm_boxplots_pgfplots('task_tick_fair', task_tick_fair_bms_2,
                                 overall_benchmarks=task_tick_fair_overall_bms_2, suffix='2', width=0.8)

    # Enqueue/Dequeue entity
    en_dequeue_entity = ['__enqueue_entity', '__dequeue_entity']

    funs_avg_boxplots_pgfplots(en_dequeue_entity, cfs_cpu_bms,
                               '__en_dequeue_entity-cpu', width=0.65)
    funs_avg_boxplots_pgfplots(en_dequeue_entity, cfs_io_bms,
                               '__en_dequeue_entity-io', width=1.05, no_labels=True)

    #
    # RT stuff
    #

    rt_hooks = ['enqueue_task_rt',
                'dequeue_task_rt',
                'pick_next_task_rt',
                'task_tick_rt']

    funs_avg_boxplots_pgfplots(rt_hooks, rt_bms, 'main-rt-hooks')
    funs_avg_boxplots_pgfplots(rt_hooks, rt_cpu_bms, 'main-rt-hooks-cpu', width=0.65)
    funs_avg_boxplots_pgfplots(rt_hooks, rt_io_bms, 'main-rt-hooks-io',
                               no_labels=True, width=1.05)

    # Pick next task RT

    pick_next_task_rt_bms_1 = select_from(BENCHMARKS,
                                          ['FIFO 8', 'FIFO 64', 'RR 16', 'RR 64', 'FIFO rand 64'])
    pick_next_task_rt_bms_2 = rt_io_bms

    fun_per_bm_boxplots_pgfplots('pick_next_task_rt', pick_next_task_rt_bms_1,
                                 overall_benchmarks=rt_cpu_bms, suffix='cpu')
    fun_per_bm_boxplots_pgfplots('pick_next_task_rt', pick_next_task_rt_bms_2,
                                 overall_benchmarks=rt_io_bms, suffix='io')

    # Task tick RT

    task_tick_rt_bms_1 = select_from(BENCHMARKS,
                                     ['FIFO 64', 'RR 8', 'FIFO rand 64'])
    task_tick_rt_bms_2 = select_from(BENCHMARKS,
                                     ['Lib FIFO 4/1', 'Lib FIFO 6/1', 'Lib FIFO 8/1'])

    fun_per_bm_boxplots_pgfplots('task_tick_rt', task_tick_rt_bms_1,
                                 overall_benchmarks=rt_cpu_bms, suffix='cpu')
    fun_per_bm_boxplots_pgfplots('task_tick_rt', task_tick_rt_bms_2,
                                 overall_benchmarks=rt_io_bms, suffix='io')

    # Enqueue/Dequeue RT entity
    en_dequeue_rt_entity = ['__enqueue_rt_entity', '__dequeue_rt_entity']

    funs_avg_boxplots_pgfplots(en_dequeue_rt_entity, rt_cpu_bms,
                               '__en_dequeue_rt_entity-cpu', width=0.65)
    funs_avg_boxplots_pgfplots(en_dequeue_rt_entity, rt_io_bms,
                               '__en_dequeue_rt_entity-io', width=1.05, no_labels=True)

    #
    # Appendix boxplots
    #

    boxplot_tables(CORE_SCHED_FUNS, BENCHMARKS, cpu_bound_bms, io_bound_bms, 'core')
    boxplot_tables(FAIR_SCHED_FUNS, cfs_bms, cfs_cpu_bms, cfs_io_bms, 'cfs')
    boxplot_tables(RT_SCHED_FUNS, rt_bms, rt_cpu_bms, rt_io_bms, 'rt')
