from flametrace.util import flatten


class Call:
    def __init__(self, active_time, begin, end, is_complete, id, name, thread_uid):
        self._active_time = active_time
        self._begin = begin
        self._end = end
        self._is_complete = is_complete
        self._id = id
        self._name = name
        self._thread_uid = thread_uid

    ################################################################################################
    # Properties
    ################################################################################################

    @property
    def active_time(self):
        return self._active_time

    @property
    def active_time_self(self):
        return self.active_time - self.children_active_time

    @property
    def begin(self):
        return self._begin

    @property
    def end(self):
        return self._end

    @property
    def duration(self):
        return self.end - self.begin

    @property
    def children(self):
        return getattr(self, '_children', [])

    @children.setter
    def children(self, val):
        if val:
            setattr(self, '_children', val)
            setattr(self, '_children_active_time', sum(map(lambda c: c.active_time, val)))
            setattr(self, '_children_duration', sum(map(lambda c: c.duration, val)))

    @property
    def children_active_time(self):
        return getattr(self, '_children_active_time', 0)

    @property
    def children_duration(self):
        return getattr(self, '_children_duration', 0)

    @property
    def is_complete(self):
        return self._is_complete

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def parent(self):
        return getattr(self, '_parent', None)

    @parent.setter
    def parent(self, val):
        if val is not None:
            setattr(self, '_parent', val)

    @property
    def successors(self):
        if (successors_ := getattr(self, '_successors', None)) is not None:
            return successors_

        successors_ = []
        for child in self.children:
            successors_.append(child)
            successors_.extend(child.successors)

        setattr(self, '_successors', successors_)

        return successors_

    @property
    def thread_uid(self):
        return self._thread_uid
