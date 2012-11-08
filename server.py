"""
Syslog server which allows handler methods to subscribe to syslog entries based
on regular expressions.

Author: Gregory Haynes <greg@idealist.org> (2012)
"""

from multiprocessing import Pool, Queue
from loggerglue.rfc5424 import SyslogEntry
import asyncore
import socket
import os
import time
import pyparsing
import re
import argparse

class LogEntryHandler(object):

    def __init__(self, handler,
                 privals=0,
                 timestamp=None,
                 hostname=None,
                 app_name=None,
                 procid=None,
                 msgid=None,
                 msg=None):
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


class LogEntryHandlerMap(object):

    def __init__(self, handlers=()):
        self.handlers = handlers

    def handlers_for(self, entry):
        ret = []
        for handler in self.handlers:
            if handler.handles_entry(entry):
                ret.append(handler)
        return ret


class LogEntryWorker(object):

    def __init__(self, work_queue, entryhandler_map):
        self.work_queue = work_queue
        self.entryhandler_map = entryhandler_map

    def run(self):
        while True:
            try:
                line = self.work_queue.get()
            except KeyboardInterrupt:
                break
            try:
                entry = SyslogEntry.from_line(line)
            except pyparsing.exceptions.Exception:
                continue
            self.process_entry(entry)

    def process_entry(self, entry):
        handlers = self.entryhandler_map.handlers_for(entry)
        for handler in handlers:
            print handler
            handler.trigger(entry)
            

def start_worker(work_queue, entryhandler_map):
    worker = LogEntryWorker(work_queue, entryhandler_map)
    worker.run()


class SyslogClient(asyncore.dispatcher_with_send):

    def __init__(self, sock, work_queue):
        asyncore.dispatcher_with_send.__init__(self, sock)
        self.work_queue = work_queue
        self.buff = ''

    def handle_read(self):
        data = self.recv(1024)
        if data:
            self.buff += data
            lines = self.buff.split('\n')
            self.buff = lines[-1]
            for line in lines[:-1]:
                start_pos = line.find('<')
                if start_pos != -1:
                    line = line[start_pos:]
                    self.work_queue.put(line)
        

class SyslogServer(asyncore.dispatcher):

    def __init__(self, address, work_queue):
        asyncore.dispatcher.__init__(self)
        self.work_queue = work_queue
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind(address)
        self.listen(5)

    def handle_accept(self):
        pair = self.accept()
        if pair is None:
            pass
        else:
            sock, addr = pair
            print 'Incoming connection from %s' % repr(addr)
            handler = SyslogClient(sock, self.work_queue)

def dontprint(entry):
    print 'THIS SHOULD NOT PRINT'

def gotmsg(entry):
    print 'I just got an entry!'

def main():
    # Argument parsing
    parser = argparse.ArgumentParser(description='Framework to process syslog'\
                                     ' entries')
    parser.add_argument('-n', '--numworkers',
        help='Numer of worker processes',
        type=int,
        default=4)
    parser.add_argument('-q', '--queuesize',
        help='Size of entry queue',
        type=int,
        default=100)
    parser.add_argument('-p', '--port',
        help='Syslog server port',
        type=int,
        default=6514)
    parser.add_argument('-l', '--listen',
        help='Syslog listen address',
        type=str,
        default='localhost')

    args = parser.parse_args()

    # Add handlers for syslog entries
    handler_map = LogEntryHandlerMap((
        LogEntryHandler(gotmsg, msg='.*'),
        LogEntryHandler(dontprint),))

    # Create the work queue
    work_queue = Queue(args.queuesize)

    # Create the worker pool
    pool = Pool(processes=args.numworkers,
                initializer=start_worker,
                initargs=(work_queue, handler_map))

    server = SyslogServer((args.listen, args.port), work_queue)
    while True:
        try:
            asyncore.loop()
        except KeyboardInterrupt:
            print 'ctrl+c detected, exiting.'
            break

if __name__ == '__main__':
    main()

