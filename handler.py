import re
import sspps

class LogEntryHandler(sspps.Plugin):

    def __init__(self, handler,
                 privals=0,
                 timestamp=None,
                 hostname=None,
                 app_name=None,
                 procid=None,
                 msgid=None,
                 msg=None):
        super(LogEntryHandler, self).__init__()
        self.handler = handler
        self.privals = privals
        self.timestamp = timestamp and re.compile(timestamp)
        self.hostname = hostname and re.compile(hostname)
        self.app_name = app_name and re.compile(app_name)
        self.procid = procid and re.compile(procid)
        self.msgid = msgid and re.compile(msgid)
        self.msg = msg and re.compile(msg)

    def handles_entry(self, entry):
        check_pairs = (
            (self.timestamp, entry.timestamp),
            (self.hostname, entry.hostname),
            (self.app_name, entry.app_name),
            (self.procid, entry.procid),
            (self.msgid, entry.msgid),
            (self.msg, entry.msg) )

        if self.privals & entry.prival:
            return True

        for pair in check_pairs:
            if pair[0] and pair[0].match(str(pair[1])):
                return True
        return False

    def trigger(self, entry):
        self.handler(entry)



