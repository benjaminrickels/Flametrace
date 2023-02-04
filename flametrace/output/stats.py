def stringify(fun_stats):
    str_stats = []

    for fun_name, stats in fun_stats.items():
        count = stats['count']
        total = stats['total']

        median = stats['median']
        min = stats['min']
        max = stats['max']
        q0 = stats['q0']
        q1 = stats['q1']
        q3 = stats['q3']
        q4 = stats['q4']
        iqr = stats['iqr']

        stats_str = (f'{fun_name}:\n'
                     f'  Count:  {count}\n'
                     f'  Min:    {min}\n'
                     f'  Q0:     {q0}\n'
                     f'  Q1:     {q1}\n'
                     f'  Median: {median}\n'
                     f'  Q3:     {q3}\n'
                     f'  Q4:     {q4}\n'
                     f'  Max:    {max}\n'
                     f'  IQR:    {iqr}\n'
                     f'  Total:  {total}\n\n')

        str_stats.append(stats_str)

    return ''.join(str_stats)
