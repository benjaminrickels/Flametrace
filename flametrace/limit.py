import re


def _parse_1(lim_str):
    if lim_str in ['benchmark', 'roi']:
        return {'limit_type': lim_str}

    try:
        if m := re.fullmatch('(?P<thread_uid>swapper\/\d+)t?', lim_str):
            return {'limit_type': 'thread', 'limit_value': m.group('thread_uid')}
        elif m := re.fullmatch(f'(?P<value>\d+)(?P<type>\%|a|c|s|t)?', lim_str):
            TYPE_DICT = {'%': 'perc', 'a': 'abs', 'c': 'call', 's': 'slice', 't': 'thread'}

            gd = m.groupdict()

            limit_value = int(gd['value'])
            limit_type = gd['type']
            limit_type = limit_type if limit_type is not None else 'a'
            limit_type = TYPE_DICT[limit_type]

            return {'limit_type': limit_type,
                    'limit_value': limit_value}
        else:
            raise ValueError()
    except:
        raise ValueError()


def parse(lims_str):
    lims_str = lims_str.strip()
    lims_strs = lims_str.split(':', 1)

    if len(lims_strs) == 1:
        limit = _parse_1(lims_strs[0])
        limit_type = limit['limit_type']
        if limit_type not in ['benchmark', 'call', 'roi', 'slice', 'thread']:
            raise ValueError()

        limit_value = limit.get('limit_value')

        limit = {'limit_type_from': limit_type,
                 'limit_type_to': limit_type}

        if limit_value:
            limit['limit_value_from'] = limit_value
            limit['limit_value_to'] = limit_value

        return limit

    lim_str_from = lims_strs[0]
    lim_str_to = lims_strs[1]

    if len(lim_str_from) == 0 and len(lim_str_to) == 0:
        raise ValueError()

    limit_from = _parse_1(lim_str_from) if len(lim_str_from) > 0 else {}
    limit_to = _parse_1(lim_str_to) if len(lim_str_to) > 0 else {}

    lims = {}
    for k, v in limit_from.items():
        lims[f'{k}_from'] = v
    for k, v in limit_to.items():
        lims[f'{k}_to'] = v

    return lims
