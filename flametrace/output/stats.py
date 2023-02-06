def stringify(fun_stats):
    str_stats = []

    for fun_name, stats in fun_stats.items():
        NAME_MAPPING = {'iqr': 'IQR'}

        stats_str = f'{fun_name}\n'
        for stat, stat_value in stats.items():
            stat = NAME_MAPPING.get(stat) or stat.capitalize()
            stats_str += f'  {stat}: {stat_value}\n'

        stats_str += '\n'

        str_stats.append(stats_str)

    return ''.join(str_stats)
