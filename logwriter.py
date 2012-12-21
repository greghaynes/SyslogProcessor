import time
import os
from Queue import Empty as QueueEmpty

class LogWriter(object):
    def __init__(self, writer_queue, args):
        self.writer_queue = writer_queue
        self.max_fds = args.maxfds
        self.log_root = args.logdir
        self.file_cache = {}
        self.last_fd_num = 2

    def run(self):
        # chroot into logdir
        os.chroot(self.log_root)

        while True:
            try:
                dest, data = self.writer_queue.get(timeout=1)
            except QueueEmpty:
                continue
            except KeyboardInterrupt:
                print 'LogWriter exiting'
                return
            try:
                f = self.fd_cache[dest][0]
            except KeyError:
                if self.last_fd_num >= self.max_fds:
                    'We need to expire something'
                    oldest = None
                    for dest, val in self.file_cache.items():
                        if oldest == None or val[1] <= self.fd_cache[oldest][1]:
                            oldest = dest
                    if oldest == None:
                        print 'Could not find file entry to expire, maxfds too low!'
                    else:
                        self.fd_cache[dest][0].close()
                        del self.fd_cache[dest]
                f = open(dest)
                self.fd_cache[dest] = (f, time.time())
            finally:
                f.write(data)
                self.fd_cache[dest][1] = time.time()

def run_writer(writer_queue, args):
    writer = LogWriter(writer_queue, args)
    writer.run()

