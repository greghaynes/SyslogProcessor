import handler

class AllMsgHandler(handler.LogEntryHandler):

    def __init__(self):
        super(AllMsgHandler, self).__init__(self.got_entry, msg='.*')

    def got_entry(self, entry):
        print 'Got entry: %s' % entry

