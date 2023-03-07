from copy import deepcopy


class ExecSlice:
    """An exec slice represents a slice of execution of a call or an entire thread. Its `type` is
    therefore either `'call'` or `'thread'`. Call slices have the additional properties
    `call_depth`, `call_id` and `call_name`, as well as `is_call_begin` and `is_call_end`."""
    _slice_id = 0

    def _next_id():
        id = ExecSlice._slice_id
        ExecSlice._slice_id += 1
        return id

    def __init__(self, type_, begin, cpu_id, thread_uid,
                 call_depth=None, call_id=None, call_name=None,
                 end=None,
                 parent=None,
                 thread_name=None,
                 is_call_begin=False, is_call_end=False):
        """Create an exec slice with the given properties. Prefer calling the convenience
        constructors `mk_call_slice` or `mk_thread_slice` instead."""
        assert type_ in ['call', 'thread']

        self._id = ExecSlice._next_id()

        # Attributes that must be set initially; begin and cpu_id can also be changed later
        self._type = type_
        self._begin = begin
        self._cpu_id = cpu_id
        self._thread_uid = thread_uid

        # For call slices, these attributes must be set initially (but call_depth can be changed later)
        if type_ == 'call':
            assert (call_depth is not None)
            assert (call_id is not None)
            assert call_name

            self._call_depth = call_depth
            self._call_id = call_id
            self._call_name = call_name

        # For thread slices, end must be set initially; for call slices eventually
        assert (type != 'thread') or (end is not None)
        self._end = end

        # parent *can* be set initially for every call slice, but *must* be set eventually
        if type_ == 'call':
            self._parent = parent

        # thread_name can be set initially
        if thread_name:
            self._thread_name = thread_name

        # For call slices, these attributes can be set at some point
        if is_call_begin:
            self._is_call_begin = is_call_begin
        if is_call_end:
            self._is_call_end = is_call_end

    ################################################################################################

    def call_depth_or(self, default=None):
        return self.call_depth if self.call_depth is not None else default

    def copy(self):
        return deepcopy(self)

    def new_id(self):
        self._id = ExecSlice._next_id()

    def __repr__(self):
        return self.__dict__

    ################################################################################################
    # Properties
    ################################################################################################

    @property
    def begin(self):
        return self._begin

    @begin.setter
    def begin(self, val):
        self._begin = val

    @property
    def end(self):
        return self._end

    @end.setter
    def end(self, val):
        self._end = val

    @property
    def duration(self):
        return self.end - self.begin

    @property
    def is_call_begin(self):
        """Is this call slice the beginning of its `call_id`'s call?"""
        if self.type != 'call':
            raise AttributeError(obj=self, name='_is_call_begin')
        return getattr(self, '_is_call_begin', False)

    @is_call_begin.setter
    def is_call_begin(self, val):
        if not val and hasattr(self, '_is_call_begin'):
            delattr(self, '_is_call_begin')
        else:
            self._is_call_begin = val

    @property
    def is_call_end(self):
        """Is this call slice the end of its `call_id`'s call?"""
        if self.type != 'call':
            raise AttributeError(obj=self, name='_is_call_end')
        return getattr(self, '_is_call_end', False)

    @is_call_end.setter
    def is_call_end(self, val):
        if not val and hasattr(self, '_is_call_end'):
            delattr(self, '_is_call_end')
        else:
            self._is_call_end = val

    @property
    def call_depth(self):
        return getattr(self, '_call_depth', None)

    @call_depth.setter
    def call_depth(self, val):
        self._call_depth = val

    @property
    def call_id(self):
        return getattr(self, '_call_id', None)

    @property
    def call_name(self):
        return getattr(self, '_call_name', None)

    @property
    def children(self):
        return getattr(self, '_children', [])

    @children.setter
    def children(self, val):
        if val:
            setattr(self, '_children', val)
        else:
            if hasattr(self, '_children'):
                delattr(self, '_children')

    @property
    def cpu_id(self):
        return self._cpu_id

    @cpu_id.setter
    def cpu_id(self, val):
        self._cpu_id = val

    @property
    def duration(self):
        return self.end - self.begin

    @property
    def id(self):
        return self._id

    @property
    def parent(self):
        return getattr(self, '_parent', None)

    @parent.setter
    def parent(self, val):
        self._parent = val

    @property
    def thread_name(self):
        return getattr(self, '_thread_name', None)

    @property
    def thread_uid(self):
        return self._thread_uid

    @property
    def type(self):
        return self._type

    @property
    def is_call_slice(self):
        return self.type == 'call'

    @property
    def is_thread_slice(self):
        return self.type == 'thread'

    ################################################################################################
    # Convenience constructors
    ################################################################################################

    def mk_call_slice(begin, cpu_id, thread_uid,
                      call_depth, call_id, call_name,
                      end=None,
                      parent=None,
                      thread_name=None,
                      is_call_begin=False, is_call_end=False):
        """Create a call slice with the given properties"""
        return ExecSlice('call', begin, cpu_id, thread_uid,
                         call_depth=call_depth, call_id=call_id, call_name=call_name,
                         end=end,
                         parent=parent,
                         thread_name=thread_name,
                         is_call_begin=is_call_begin, is_call_end=is_call_end)

    def mk_thread_slice(begin, end, cpu_id, thread_uid, thread_name=None):
        """Create a thread slice with the given properties"""
        return ExecSlice('thread', begin, cpu_id, thread_uid,
                         end=end,
                         thread_name=thread_name)
