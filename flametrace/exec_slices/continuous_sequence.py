##############################
# Finding continuous sequences
##############################


class ContinuousSequence:
    def __init__(self, entry, preempted=None):
        self._entries = [entry]
        if preempted:
            self._preempted = preempted

    def append(self, entry):
        self._entries.append(entry)

    def entry_at(self, i):
        return self.entries[i]

    def preempt_with(self, entry):
        self._preempted_by = entry

    ################################################################################################
    # Properties
    ################################################################################################

    @property
    def preempted(self):
        return getattr(self, '_preempted', None)

    @property
    def preempted_by(self):
        return getattr(self, '_preempted_by', None)

    @property
    def first(self):
        return self.entry_at(0)

    @property
    def last(self):
        return self.entry_at(-1)

    @property
    def begin(self):
        return self.first.timestamp

    @property
    def end(self):
        return self.last.timestamp

    @property
    def duration(self):
        return self.end - self.begin

    @property
    def begin_approx(self):
        if (entry := self.preempted):
            preempted_end = entry.timestamp
            return (preempted_end + self.begin) / 2

        return self.begin

    @property
    def end_approx(self):
        if (entry := self.preempted_by):
            preempting_begin = entry.timestamp
            return (self.end + preempting_begin) / 2

        return self.end

    @property
    def duration_approx(self):
        return self.end_approx - self.begin_approx

    @property
    def cpu_id(self):
        return self.first.cpu_id

    @property
    def thread_name(self):
        return self.first.thread_name

    @property
    def thread_uid(self):
        return self.first.thread_uid

    @property
    def entries(self):
        return self._entries
