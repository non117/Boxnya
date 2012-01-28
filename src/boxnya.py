# -*- coding: utf-8 -*-
import atexit, os, signal, sys, time

from core import Master
try:
    import settings
except ImportError:
    sys.exit("Error : Cannot import settings module.")

class Daemon(object):
    def __init__(self):
        self.pidfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), "boxnya.pid")
        logdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log", "system.log")
        self.stdin = '/dev/null'
        self.stdout = logdir
        self.stderr = logdir
    def daemonize(self):
        try: 
            pid = os.fork() 
            if pid > 0:
                sys.exit(0) 
        except OSError, e: 
            sys.stderr.write("fork #1 failed: %d (%s)¥n" % (e.errno, e.strerror))
            sys.exit(1)
        os.chdir("/") 
        os.setsid() 
        os.umask(0) 

        try: 
            pid = os.fork() 
            if pid > 0:
                sys.exit(0) 
        except OSError, e: 
            sys.stderr.write("fork #2 failed: %d (%s)¥n" % (e.errno, e.strerror))
            sys.exit(1) 

        sys.stdout.flush()
        sys.stderr.flush()
        si = file(self.stdin, 'r')
        so = file(self.stdout, 'a+')
        se = file(self.stderr, 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())
    
        atexit.register(self.delpid)
        pid = str(os.getpid())
        file(self.pidfile,'w+').write("%s" % pid)
    def delpid(self):
        os.remove(self.pidfile)
    def start(self):
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None
        if pid:
            message = "pidfile %s already exist. Daemon already running?¥n"
            sys.stderr.write(message % self.pidfile)
            sys.exit(1)
        self.daemonize()
        self.run()
    def stop(self):
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None
        if not pid:
            message = "pidfile %s does not exist. Daemon not running?¥n"
            sys.stderr.write(message % self.pidfile)
            return # not an error in a restart
        try:
            while 1:
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.1)
        except OSError, err:
            err = str(err)
            if err.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                print str(err)
                sys.exit(1)
    def restart(self):
        self.stop()
        self.start()
    def run(self):
        global main
        main()

def main():
    master = Master(settings)
    master.start()
    signal.pause()
    master.join()

def handler(signum, frame):
    pass
signal.signal(signal.SIGTERM, handler)
signal.signal(signal.SIGINT, handler)

if __name__ == "__main__":
    if settings.DAEMON:
        if len(sys.argv) == 2:
            daemon = Daemon()
            if 'start' == sys.argv[1]:
                daemon.start()
            elif 'stop' == sys.argv[1]:
                daemon.stop()
            elif 'restart' == sys.argv[1]:
                daemon.restart()
            else:
                print "Unknown command"
                sys.exit(2)
            sys.exit(0)
        else:
            print "usage: %s start|stop|restart" % sys.argv[0]
            sys.exit(2)
    else:
        print "---> Boxnya service start."
        main()
        print "\n---> see you !"
        sys.exit(0)