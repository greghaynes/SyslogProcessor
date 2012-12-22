import handler

class AllMsgHandler(handler.LogEntryHandler):

    def __init__(self, log_write_queue):
        super(AllMsgHandler, self).__init__(self.got_entry, log_write_queue, msg='.*')

    def got_entry(self, entry):
        print 'Got entry(2): %s' % entry

