# -*- coding: utf-8 -*-
import atexit
import os
import sys
import signal
import time

from lib.core import Master
from lib.twitter.api import Api

def settings_loader(settings):
    daemon = getattr(settings, "DAEMON", False)
    
    log_settings = {}
    logging = getattr(settings, "LOGGING", True)
    if logging:
        log_dir = getattr(settings, "LOG_DIR", None)
        # ログディレクトリの設定がなければ, Boxnya/logを設定
        if not log_dir:
            log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),"log")
        
        if not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir)
            except os.error:
                sys.exit("Error : Cannot make log directory.")
        
        log_settings = {"LOG_OUT":getattr(settings, "LOG_OUT", []),
                        "LOG_MOD":getattr(settings, "LOG_MOD", []),
                        "LOG_DIR":log_dir
                        }
    
    if getattr(settings, "INOUT", {}) == {}:
        sys.exit("Error : No Input-to-Output matrix.")
    return {"DAEMON":daemon,
            "LOGGING":logging,
            "LOG_SETTINGS":log_settings,
            "ENABLE_MODULES":getattr(settings, "ENABLE_MODULES", []),
            "INOUT":settings.INOUT,
            "MODULE_SETTINGS":getattr(settings, "MODULE_SETTINGS", {}),
            }

try:
    import settings as settings__
    settings = settings_loader(settings__)
except ImportError:
    sys.exit("Error : Cannot import settings module.")

def twitterinitializer(account_number=0):
    if account_number == 0:
        global settings
        # settings - twitter内の辞書の数を数える
        twitter_setting = settings.get("MODULE_SETTINGS").get("twitter",[])
        if isinstance(twitter_setting, dict):
            twitter_setting = [twitter_setting]
        account_number = len(twitter_setting)
    
    tokens = ['\n"twitter":[']
    api = Api()
    for i in range(account_number):
        print "\n\n---> Authorize %dth account." % i + 1
        tokens.append("\n%s," % str(api.initializer()))
    tokens.append('],')
    
    with open(os.path.dirname(os.path.abspath(__file__)) + "/settings.py", "a") as f:
        f.writelines(tokens)
    
    print tokens
    
class Daemon(object):
    def __init__(self):
        global settings
        log = settings["LOG_SETTINGS"]["LOG_DIR"] + "/system.log"
        self.pidfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), "boxnya.pid")
        self.stdin = '/dev/null'
        self.stdout = log
        self.stderr = log
    
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
        if pid is None:
            message = "pidfile %s does not exist. Daemon not running?¥n"
            sys.stderr.write(message % self.pidfile)
            return # not an error in a restart
        try:
            while True:
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

def handler(signum, frame):
    pass
signal.signal(signal.SIGTERM, handler)
signal.signal(signal.SIGINT, handler)

def main():
    global settings
    master = Master(settings)
    master.start()
    if os.name != "nt":
        signal.pause()
        master.join()
    else:
        try:
            while True:
                raw_input()
        except KeyboardInterrupt:
            master.join()

if __name__ == "__main__":
    # initコマンド. 例 : $ python boxnya.py init 2
    if 2 <= len(sys.argv) <= 3 and sys.argv[1] == 'init':
        try:
            account_number = int(sys.argv[2]) if sys.argv[2:] else 0
        except ValueError:
            sys.exit("Error : Please input a number.")
        twitterinitializer(account_number)
        sys.exit(0)
    
    if settings.get("DAEMON", False):
        if len(sys.argv) == 2:
            daemon = Daemon()
            if sys.argv[1] == 'start':
                daemon.start()
            elif sys.argv[1] == 'stop':
                daemon.stop()
            elif sys.argv[1] == 'restart':
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