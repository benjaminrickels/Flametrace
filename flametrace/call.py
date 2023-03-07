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

    def children_list(self, call_map):
        if (children_ := getattr(self, '_children_list', None)) is not None:
            return children_

        children_ = []
        for child in self.children:
            if child_call := call_map.get(child, None):
                children_.append(child_call)

        setattr(self, '_children_list', children_)

        return children_

    def successors_list(self, call_map):
        if (successors_ := getattr(self, '_successors_list', None)) is not None:
            return successors_

        successors_ = []
        for child in self.children_list(call_map):
            successors_.append(child.successors_list(call_map))

        successors_ = flatten(successors_)
        setattr(self, '_successors_list', successors_)

        return successors_

    ################################################################################################
    # Properties
    ################################################################################################

    @property
    def active_time(self):
        return self._active_time

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
    def thread_uid(self):
        return self._thread_uid
