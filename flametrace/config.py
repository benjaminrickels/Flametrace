# Default CPU frequency in GHz
CPU_GHZ = 2.0

# Default functions that should be ignored when building the flamegraph
IGNORED_FUNS = ['registerThread', 'unregisterThread',
                'start_pthread',
                'requeue_task_rt',
                'get_event', 'send_event',
                'signal_que_enq', 'signal_que_enq_data', 'signal_que_enq_notify',
                'signal_que_deq', 'signal_que_deq_data', 'signal_que_deq_notify',
                'pool_allocate_message', 'pool_free_message',
                'pool_read_message', 'pool_write_message']

# Colors for SVG generation.
# 'fixed' is a map from thread_uid to hex color
# 'random' is an array of colors that can be chosen from randomly (must not be empty)
COLORS = {'fixed': {},
          'random': ['#622500',
                     '#6d3ae6',
                     '#9cf81e',
                     '#0131cc',
                     '#00e153',
                     '#ab38eb',
                     '#00ca4a',
                     '#730084',
                     '#5eb700',
                     '#026ef4',
                     '#eafb56',
                     '#202085',
                     '#1ea000',
                     '#b37aff',
                     '#81b500',
                     '#3188ff',
                     '#b4b600',
                     '#99007e',
                     '#00f899',
                     '#ff5ccb',
                     '#218400',
                     '#ff91fa',
                     '#00c170',
                     '#ed001a',
                     '#1cfff1',
                     '#bb1300',
                     '#8fffff',
                     '#fa7200',
                     '#027ccb',
                     '#ffed6a',
                     '#282b5f',
                     '#d7ff82',
                     '#a40064',
                     '#9cffac',
                     '#cd005e',
                     '#01ae85',
                     '#ff567b',
                     '#008142',
                     '#9a003b',
                     '#c6ffae',
                     '#750033',
                     '#f4f69c',
                     '#442547',
                     '#c09c00',
                     '#83b3ff',
                     '#ff9832',
                     '#0096d4',
                     '#7c1600',
                     '#c8b1ff',
                     '#5a6800',
                     '#f7d3f1',
                     '#033a0b',
                     '#ffa3a5',
                     '#003e2e',
                     '#ffc6ce',
                     '#4d4800',
                     '#809abb',
                     '#914900',
                     '#01567a',
                     '#eff5be',
                     '#48290e',
                     '#ffcba0',
                     '#859471',
                     '#ffb99b']}

# Change the default for the option --no-trace-convert-to-cycles, so it does not
# have to be specified each time
TRACE_CONVERT_TO_CYCLES = True
