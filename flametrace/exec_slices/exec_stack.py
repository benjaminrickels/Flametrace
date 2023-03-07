from flametrace.exec_slice import ExecSlice
from flametrace.util import min_key


def _normalize_call_depth(call_slices):
    min_depth = min_key(call_slices, key=lambda slce: slce.call_depth, default=0)
    if min_depth:
        for slce in call_slices:
            slce.call_depth = slce.call_depth - min_depth


class ExecStack:
    """An execution stack for a single thread. i.e. a call stack that also stores information about the begin and end of
    a call. Calls can be pushed onto and popped from the stack, and the stack can be suspended and resumed. Popping also
    works for calls that have not been pushed, e.g. because tracing was not active when the call begun."""

    # Unique ID for each call *across* all threads
    _call_id = 0

    def __init__(self, thread_uid):
        self._begin = None
        self._cpu_id = None
        self._depth = 0
        self._call_slices = []
        self._thread_slices = []
        self._stack = []
        self._thread_uid = thread_uid

    @property
    def begin(self):
        assert self.is_active

        return self._begin

    @property
    def cpu_id(self):
        assert self.is_active

        return self._cpu_id

    @property
    def thread_uid(self):
        return self._thread_uid

    @property
    def is_active(self):
        return (self._begin is not None) and (self._cpu_id is not None)

    @property
    def is_inactive(self):
        return not self.is_active

    ################################################################################################

    def deactivate(self):
        self._begin = self._cpu_id = None

    def _mk_push_slice(self, call_name, timestamp):
        """Create a slice for a call that has just been pushed onto the stack"""

        return ExecSlice.mk_call_slice(timestamp,
                                       self.cpu_id,
                                       self.thread_uid,
                                       call_depth=self._depth,
                                       call_id=ExecStack._call_id,
                                       call_name=call_name,
                                       thread_name=self._thread_name,
                                       is_call_begin=True)

    def push(self, call_name, begin):
        """Push a call with given name and `begin` timestamp onto the stack"""

        assert self.is_active

        new_slice = self._mk_push_slice(call_name, begin)
        self._stack.append(new_slice)

        self._depth += 1
        ExecStack._call_id += 1

    def _emulate_prev_pop_slice(self, call_name, thread_slice):
        """Emulate the slice that corresponds to the call during the given previous active phase of the thread"""

        return ExecSlice.mk_call_slice(thread_slice.begin,
                                       self.cpu_id,
                                       self.thread_uid,
                                       call_depth=self._depth,
                                       call_id=ExecStack._call_id,
                                       call_name=call_name,
                                       end=thread_slice.end,
                                       thread_name=thread_slice.thread_name)

    def _emulate_prev_pop_slices(self, function_name):
        """Emulate slices that correspond to the call during previously active phases of the thread"""

        return [self._emulate_prev_pop_slice(function_name, thread_slice)
                for thread_slice
                in self._thread_slices]

    def _emulate_pop_slice(self, call_name, timestamp):
        """Emulate the slice that corresponds to the call during the currently active phase of the thread"""

        return ExecSlice.mk_call_slice(self.begin,
                                       self.cpu_id,
                                       self.thread_uid,
                                       call_depth=self._depth,
                                       call_id=ExecStack._call_id,
                                       call_name=call_name,
                                       end=timestamp,
                                       thread_name=self._thread_name,
                                       is_call_end=True)

    def _pop(self, timestamp):
        """Set some more properties for a slice that has previously been pushed and return it"""

        slce = self._stack.pop()
        slce.end = timestamp
        slce.is_call_end = True
        self._depth -= 1
        return slce

    def _emulate_pop(self, function_name, timestamp):
        """"Emulate" a pop for a call that has not been pushed before"""

        self._depth -= 1
        prev_slices = self._emulate_prev_pop_slices(function_name)
        slce = self._emulate_pop_slice(function_name, timestamp)

        prev_slices.append(slce)
        return prev_slices

    def pop(self, call_name, end):
        """Pop a call with given name and `end` timestamp from the stack"""
        assert self.is_active

        # Yay, there is a call in the stack, so we can actually pop it
        if self._stack:
            popped_slice = self._pop(end)
            self._call_slices.append(popped_slice)
        # There is a pop but nothing in the stack => "Emulate" a pop
        else:
            popped_slices = self._emulate_pop(call_name, end)
            self._call_slices.extend(popped_slices)

            ExecStack._call_id += 1

    def _suspend_slice(self, slce, timestamp):
        suspended_slice = slce.copy()
        suspended_slice.end = timestamp
        return suspended_slice

    def _suspend_slices(self, timestamp):
        return [self._suspend_slice(slce, timestamp) for slce in self._stack]

    def suspend(self, timestamp):
        """Suspend the stack at the given `timestamp` when this thread stopped executing, e.g. because a new thread has
        started running on the same core"""

        assert self.is_active

        thread_slice = ExecSlice.mk_thread_slice(self.begin,
                                                 timestamp,
                                                 self.cpu_id,
                                                 self.thread_uid,
                                                 self._thread_name)
        self._thread_slices.append(thread_slice)

        new_call_slices = self._suspend_slices(timestamp)
        self._call_slices.extend(new_call_slices)

        self.deactivate()

    def resume(self, timestamp, cpu_id, thread_name):
        """Resume this stack at the given `timestamp` when the threads starts running on the given `cpu_id`, e.g because
        this thread preempts another one"""

        assert self.is_inactive

        self._begin = timestamp
        self._cpu_id = cpu_id
        self._thread_name = thread_name

        for slce in self._stack:
            slce.new_id()
            slce.begin = timestamp
            slce.cpu_id = cpu_id
            slce.is_call_begin = False

    def teardown(self):
        """Teardown this stack once a thread has stopped executing"""
        _normalize_call_depth(self._call_slices)

        slices = self._call_slices
        slices.extend(self._thread_slices)

        self._call_slices = []
        self._thread_slices = []
        self.deactivate()

        return slices
