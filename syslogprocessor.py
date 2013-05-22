"""
Syslog server which allows handler methods to subscribe to syslog entries based
on regular expressions.

Author: Gregory Haynes <greg@idealist.org> (2012)
"""

from multiprocessing import Pool, Queue, Process
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
import signal
import rsyslog_fix
import logwriter
import unixtools

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

    def __init__(self, work_queue, args, log_write_queue):
        self.work_queue = work_queue
        self.log_write_queue = log_write_queue
        self.init_handler_map(args.handlersdir)
        self.uid = unixtools.get_uid(args.workuser)
        self.gid = unixtools.get_gid(args.workgroup)

    @property
    def runable(self):
        return self.entryhandler_map != None

    def init_handler_map(self, handlersdir):
        self.plugin_loader = sspps.PluginLoader(handlersdir,
                                                parent_class=handler.LogEntryHandler,
                                                init_args=(self.log_write_queue,))
        try:
            self.plugin_loader.load_all()
        except OSError:
            print 'Invalid plugin path \'%s\'.' % handlersdir
            return None

        self.entryhandler_map = LogEntryHandlerMap(self.plugin_loader.plugins)

    def run(self):
        if not self.runable:
            print 'Process not runable, returning'
            return False

        # Drop privileges
        os.setgroups([])
        os.setgid(self.gid)
        os.setuid(self.uid)

        ppid = os.getppid()
        while True:
            try:
                line = self.work_queue.get(timeout=0.5)
                if not line:
                    'Parent process is asking us to exit'
                    return True
                line = line.decode('utf-8').encode('ASCII', 'ignore')
            except KeyboardInterrupt:
                return False
            except UnicodeDecodeError:
                print 'Unicode Error, skipping entry'
                continue
            except QueueEmpty:
                if os.getppid() != ppid:
                    return False
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


def start_worker(work_queue, entryhandler_map, log_write_queue):
    worker = LogEntryWorker(work_queue, entryhandler_map, log_write_queue)
    return worker.run()


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
                    self.work_queue.put(line, block=False)


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


do_reload = False

def main():
    global do_reload
    # Argument parsing
    parser = argparse.ArgumentParser(description='Framework to process syslog'\
                                     ' entries')
    parser.add_argument('-n', '--numworkers',
        help='Numer of worker processes',
        type=int,
        default=4)
    parser.add_argument('-w', '--workqueuesize',
        help='Size of worker queue',
        type=int,
        default=100)
    parser.add_argument('-q', '--workuser',
        help='User for worker processes to run as',
        type=str,
        default='nobody')
    parser.add_argument('-r', '--workgroup',
        help='Group for worker processes to run as',
        type=str,
        default='nogroup')
    parser.add_argument('-c', '--logqueuesize',
        help='Size of log write queue',
        type=int,
        default=100)
    parser.add_argument('-f', '--maxfds',
        help='Maximum number of file descriptors to open',
        type=int,
        default=1020)
    parser.add_argument('-d', '--logdir',
        help='Root directory for log files',
        type=str,
        default='/var/log')
    parser.add_argument('-u', '--loguser',
        help='User for log writer to run as',
        type=str,
        default='syslog')
    parser.add_argument('-x', '--loggroup',
        help='Group for log writer to run as',
        type=str,
        default='syslog')
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
    parser.add_argument('-D', '--daemonize',
        help='Run as a daemon',
        action="store_true")

    args = parser.parse_args()

    # Daemonize
    if args.daemonize:
        unixtools.daemonize()

    rsyslog_fix.fix()

    # Create the work queue
    work_queue = Queue(args.workqueuesize)

    # log write queue
    log_write_queue = Queue(args.logqueuesize)

    # Start log writer process
    log_writer = Process(target=logwriter.run_writer,
                         args=(log_write_queue, args))
    log_writer.start()

    # Our reload signal handler
    def sigusr1_handler(signum, frame):
        global do_reload
        do_reload = True

    signal.signal(signal.SIGUSR1, sigusr1_handler)

    # Create the worker pool
    pool = Pool(processes=args.numworkers,
                initializer=start_worker,
                initargs=(work_queue, args, log_write_queue))

    server = SyslogServer((args.listen, args.port), work_queue)

    try:
        while True:
                asyncore.loop(timeout=.2, count=1)
                if do_reload:
                    print 'Starting reload'

                    # Cause children to exit
                    for i in range(args.numworkers):
                        work_queue.put(None)

                    # No more swimming
                    pool.close()
                    pool.join()

                    # Restart children
                    pool = Pool(processes=args.numworkers,
                                initializer=start_worker,
                                initargs=(work_queue, args))

                    print 'Reload complete'
                    do_reload = False

    except KeyboardInterrupt:
        print 'ctrl+c detected, exiting.'
        pool.close()
        sys.exit(os.EX_OSERR)
    except Exception, e:
        print 'Error, closing the pool'
        pool.close()
        raise e

if __name__ == '__main__':
    main()

