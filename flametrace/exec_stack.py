from operator import itemgetter


def _normalize_depth(fun_slices):
    min_depth_obj = min(fun_slices, key=itemgetter('_denorm_depth'), default=None)
    if min_depth_obj:
        min_depth = min_depth_obj['_denorm_depth']
        for slce in fun_slices:
            denorm_depth = slce.pop('_denorm_depth')
            slce['depth'] = denorm_depth - min_depth


class ExecStack:
    _call_id = 0

    def __init__(self, thread_uid):
        self._begin = None
        self._cpu_id = None
        self._depth = 0
        self._fun_slices = []
        self._thread_slices = []
        self._stack = []
        self._thread_uid = thread_uid

    def _is_active(self):
        return (self._begin is not None) and (self._cpu_id is not None)

    def _is_inactive(self):
        return (self._begin is None) and (self._cpu_id is None)

    def _make_push_slice(self, function_name, timestamp):
        return {'type': 'function_slice',
                'begin': timestamp,
                'call_id': ExecStack._call_id,
                'cpu_id': self._cpu_id,
                '_denorm_depth': self._depth,
                'function_name': function_name,
                'is_begin': True,
                'thread_uid': self._thread_uid}

    def push(self, function_name, timestamp):
        assert self._is_active()

        slce = self._make_push_slice(function_name, timestamp)
        self._stack.append(slce)

        self._depth += 1
        ExecStack._call_id += 1

    def _make_prev_pop_slice(self, function_name, thread_slice):
        return {'type': 'function_slice',
                'begin': thread_slice['begin'],
                'end': thread_slice['end'],
                'cpu_id': self._cpu_id,
                'call_id': ExecStack._call_id,
                '_denorm_depth': self._depth,
                'function_name': function_name,
                'thread_uid': self._thread_uid}

    def _make_prev_pop_slices(self, function_name):
        return [self._make_prev_pop_slice(function_name, thread_slice)
                for thread_slice
                in self._thread_slices]

    def _make_pop_slice(self, function_name, timestamp):
        return {'type': 'function_slice',
                'begin': self._begin,
                'end': timestamp,
                'call_id': ExecStack._call_id,
                'cpu_id': self._cpu_id,
                '_denorm_depth': self._depth,
                'function_name': function_name,
                'is_end': True,
                'thread_uid': self._thread_uid}

    def _pop(self, timestamp):
        slce = self._stack.pop()
        slce['end'] = timestamp
        slce['is_end'] = True
        return slce

    def _emulate_pop(self, function_name, timestamp):
        prev_slices = self._make_prev_pop_slices(function_name)
        slce = self._make_pop_slice(function_name, timestamp)

        prev_slices.append(slce)
        return prev_slices

    def pop(self, function_name, timestamp):
        assert self._is_active()

        self._depth -= 1

        if self._stack:
            slce = self._pop(timestamp)
            self._fun_slices.append(slce)
        else:
            slices = self._emulate_pop(function_name, timestamp)
            self._fun_slices.extend(slices)

            ExecStack._call_id += 1

    def _make_thread_slice(self, timestamp):
        return {'type': 'thread_slice',
                'begin': self._begin,
                'end': timestamp,
                'cpu_id': self._cpu_id,
                'thread_uid': self._thread_uid}

    def _suspend_slice(self, slce, timestamp):
        susp_slice = dict(slce)
        susp_slice['end'] = timestamp

        slce.pop('begin', None)
        slce.pop('is_begin', None)

        return susp_slice

    def _suspend_slices(self, timestamp):
        return [self._suspend_slice(slce, timestamp) for slce in self._stack]

    def suspend(self, timestamp):
        assert self._is_active()

        thread_slice = self._make_thread_slice(timestamp)
        self._thread_slices.append(thread_slice)

        fun_slices = self._suspend_slices(timestamp)
        self._fun_slices.extend(fun_slices)

        self._begin = None
        self._cpu_id = None

    def resume(self, timestamp, cpu_id):
        assert self._is_inactive()

        self._begin = timestamp
        self._cpu_id = cpu_id

        for slce in self._stack:
            slce['cpu_id'] = cpu_id
            slce['begin'] = timestamp

    def teardown(self):
        _normalize_depth(self._fun_slices)
        self._fun_slices.extend(self._thread_slices)
        return self._fun_slices
