"""
Syslog server which allows handler methods to subscribe to syslog entries based
on regular expressions.

Author: Gregory Haynes <greg@idealist.org> (2012)
"""

from multiprocessing import Pool, Queue
from loggerglue.rfc5424 import SyslogEntry
from Queue import Empty as QueueEmpty
import asyncore
import socket
import os
import sys
import time
import pyparsing
import argparse
import sspps
import handler
import rsyslog_fix

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
        ppid = os.getppid()
        while True:
            try:
                line = self.work_queue.get(timeout=0.5).decode('utf-8').encode('ASCII', 'ignore')
            except KeyboardInterrupt:
                break
            except QueueEmpty:
                if os.getppid() != ppid:
                    break
                continue
            try:
                entry = SyslogEntry.from_line(line)
            except pyparsing.exceptions.Exception:
                continue
            self.process_entry(entry)

    def process_entry(self, entry):
        handlers = self.entryhandler_map.handlers_for(entry)
        for handler in handlers:
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
    parser.add_argument('-m', '--handlersdir',
        help='Director containing handler modules',
        type=str,
        default='/var/lib/syslogprocessor/handlers')

    args = parser.parse_args()

    rsyslog_fix.fix()

    pl = sspps.PluginLoader(args.handlersdir, parent_class=handler.LogEntryHandler)
    try:
        pl.load_all()
    except OSError:
        print 'Invalid plugin path \'%s\'.' % args.handlersdir
        print 'Please specify a valid handlers directory'
        sys.exit(os.EX_OSERR)

    # Add handlers for syslog entries
    handler_map = LogEntryHandlerMap(pl.plugins)

    # Create the work queue
    work_queue = Queue(args.queuesize)

    # Create the worker pool
    pool = Pool(processes=args.numworkers,
                initializer=start_worker,
                initargs=(work_queue, handler_map))

    server = SyslogServer((args.listen, args.port), work_queue)

    try:
        while True:
                asyncore.loop()
    except KeyboardInterrupt:
        print 'ctrl+c detected, exiting.'
        pool.close()
        sys.exit(os.EX_OSERR)
    except Exception:
        print 'Error, exiting'
        pool.close()

if __name__ == '__main__':
    main()

