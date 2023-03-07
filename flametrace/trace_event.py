'''Representing and parsing tracefile entries/lines as/into `TraceEntry` objects'''

from operator import itemgetter
from flametrace import config
from flametrace.util import ps_to_cycles, thread_id_to_uid

import re

# Example: "<...>-1234  [001]  9876543210  ftrace_entry: schedule"
EVENT_REGEX = ('<(?P<thread_info>\S*)>-(?P<thread_id>\d*)'
               '\s*\[(?P<cpu_id>\d*)\]'
               '\s*(?P<timestamp>\d*):'
               '\s*(?P<type_>\S*):\s*(?P<info>.*)')


class TraceEvent:
    '''An event representing an entry/line in a tracefile. Each event has certain properties, depending on its type. All
    events have the following properties:
      * `type -> str`: The type of the event
      * `cpu_id -> int`: The ID (number) of the CPU the event belongs to
      * `thread_name -> str | None`: The name of the thread the event belongs to
      * `thread_uid -> str`: A unique ID of the thread the event belongs to (this is different from the first column
      of the tracefile, as all swapper threads have non-unique ID 0)
      * `timestamp -> int`: The timestamp of the event

    If the event is of type `'ftrace_entry'`, `'ftrace_exit'`, `'sys_enter'` or `'sys_exit'` it has a a property
    `call_name -> str`.

    An event of type `'sched_switch'` has the property `sched_switch_info` which returns a map that has the keys
    `'thread_uid_from'`, `'thread_name_from'`, `'thread_uid_to'`, `'thread_name_to'`.

    Otherwise the event has a type corresponding to the fourth column of the tracefile and a property `info -> str`
    corresponding to the fifth column.

    Trying to access a property that does not exist for an event throws an `AttributeError`.
    '''

    def __init__(self, type_, context, **kwargs):
        '''Construct a `TraceEvent` of given `type_`, `context` and `kwargs`. `context` must be a
        `dict` with keys `cpu_id`, `thread_id`, and `timestamp`. `kwargs` will be set on the
        instance using `setattr`.'''

        self._type = type_
        self._cpu_id = int(context['cpu_id'])
        self._thread_uid = thread_id_to_uid(int(context['thread_id']), self._cpu_id)

        timestamp = int(context['timestamp'])
        self._timestamp = timestamp if not config.TRACE_CONVERT_TO_CYCLES else ps_to_cycles(
            timestamp)

        for kw, arg in kwargs.items():
            setattr(self, f'_{kw}', arg)

    def parse(tracefile_line):
        '''Try to parse a single tracefile line into a `TraceEvent`. Throws `ValueError` if parsing
        fails.'''

        tracefile_line = tracefile_line.strip()
        if m := re.fullmatch(EVENT_REGEX, tracefile_line):
            thread_id, cpu_id, timestamp, type_, info = itemgetter('thread_id',
                                                                   'cpu_id',
                                                                   'timestamp',
                                                                   'type_',
                                                                   'info')(m.groupdict())
            context = {'thread_id': thread_id,
                       'cpu_id': cpu_id,
                       'timestamp': timestamp}

            event = None
            for parser in [parse_ftrace_entry_exit,
                           parse_sched_switch,
                           parse_sys_enter_exit]:
                event = parser(context, type_, info)
                if event:
                    break

            if event is None:
                event = TraceEvent(type_, context, info=info)

            return event
        else:
            raise ValueError(tracefile_line)

    def __repr__(self):
        return str(self.__dict__)

    ################################################################################################
    # Properties
    ################################################################################################

    @property
    def call_name(self):
        return self._call_name

    @property
    def cpu_id(self):
        return self._cpu_id

    @property
    def info(self):
        return self._info

    @property
    def sched_switch_info(self):
        if self.type != 'sched_switch':
            raise AttributeError(obj=self, name='sched_switch_info')

        return {'uid_from': self._thread_uid,
                'name_from': self._thread_name_from,
                'uid_to': self._thread_uid_to,
                'name_to': self._thread_name_to}

    @property
    def thread_name(self):
        return getattr(self, '_thread_name', None)

    @thread_name.setter
    def thread_name(self, name):
        setattr(self, '_thread_name', name)

    @property
    def thread_uid(self):
        return self._thread_uid

    @property
    def timestamp(self):
        return self._timestamp

    @property
    def type(self):
        return self._type


####################################################################################################
# Parsing functions
#
# A parsing function tries to parse a tracefile line with the given `type_` and `info` into a
# `TraceEvent` using the `context` also given as a parameter. Thus a parsing function's signature is
# `(context, type_, info) -> TraceEvent`. If the line could not be parsed, `None` should be
# returned.
####################################################################################################


def parse_ftrace_entry_exit(context, type_, info):
    if type_ == 'ftrace_entry':
        return mk_ftrace_entry(context, info)
    elif type_ == 'ftrace_exit':
        return mk_ftrace_exit(context, info)


# Example: "m5:1263 [120] TBV ==> swapper/3:0 [120]"
SCHED_SWITCH_PARSE_REGEX = ('^(?P<name_from>\S*):(?P<id_from>\d*) '
                            '\[\d*\] TBV ==> '
                            '(?P<name_to>\S*):(?P<id_to>\d*) \[\d*\]$')


def parse_sched_switch(context, type_, info):
    if type_ == 'sched_switch' and (m := re.fullmatch(SCHED_SWITCH_PARSE_REGEX, info)):
        name_from, id_to, name_to = itemgetter('name_from', 'id_to', 'name_to')(m.groupdict())
        return mk_sched_switch(context, name_from, id_to, name_to)


# Example: "sys_enter_write"
SYS_ENTER_EXIT_PARSE_REGEX = '^(sys_enter|sys_exit)_(\S*)$'


def parse_sys_enter_exit(context, type_, _):
    if m := re.fullmatch(SYS_ENTER_EXIT_PARSE_REGEX, type_):
        sys_type, syscall_name = m.group(1, 2)
        if sys_type == 'sys_enter':
            return mk_syscall_enter(context, syscall_name)
        elif sys_type == 'sys_exit':
            return mk_syscall_exit(context, syscall_name)


####################################################################################################
# Convenience constructors for specific `TraceEvent` types
####################################################################################################


def mk_ftrace_entry_exit(type_, context, function_name):
    return TraceEvent(type_, context, call_name=function_name)


def mk_ftrace_entry(context, function_name):
    return mk_ftrace_entry_exit('ftrace_entry', context, function_name)


def mk_ftrace_exit(context, function_name):
    return mk_ftrace_entry_exit('ftrace_exit', context, function_name)


def mk_sched_switch(context, thread_name_from, thread_id_to, thread_name_to):
    cpu_id = context['cpu_id']
    thread_uid_from = thread_id_to_uid(context['thread_id'], cpu_id)
    thread_uid_to = thread_id_to_uid(thread_id_to, cpu_id)
    return TraceEvent('sched_switch',
                      context,
                      thread_uid_from=thread_uid_from,
                      thread_name_from=thread_name_from,
                      thread_uid_to=thread_uid_to,
                      thread_name_to=thread_name_to)


def mk_syscall_entry_exit(type_, context, syscall_name):
    return TraceEvent(type_, context, call_name=syscall_name)


def mk_syscall_enter(context, syscall_name):
    return mk_syscall_entry_exit('sys_enter', context, syscall_name)


def mk_syscall_exit(context, syscall_name):
    return mk_syscall_entry_exit('sys_exit', context, syscall_name)
