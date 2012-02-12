# -*- coding: utf-8 -*-
import atexit
import os, sys, signal
import time
import re

from lib.core import Master
from lib.twitter.api import Api

def settings_loader(settings):
    daemon = getattr(settings, "DAEMON", False)
    
    logging = getattr(settings, "LOGGING", True)
    if logging:
        if not getattr(settings, "LOG_DIR", ""):
            # ログディレクトリの設定がなければ, Boxnya/logを設定
            log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),"log")
        else:
            log_dir = settings.LOG_DIR
        if not os.path.exists(log_dir): #フォルダが存在しなければ作る
            try:
                os.makedirs(log_dir)
            except os.error:
                sys.exit("Error : Cannot make log directory.")
        log_settings = {"LOG_OUT":getattr(settings, "LOG_OUT", []),
                        "LOG_MOD":getattr(settings, "LOG_MOD", []),
                        "LOG_DIR":log_dir
                        }
    else:
        log_settings = {}
    if not getattr(settings, "INOUT", {}):
        sys.exit("Error : No Input-to-Output matrix.")
    return {"DAEMON":daemon,
            "LOGGING":logging,
            "LOG_SETTINGS":log_settings,
            "ENABLE_MODULES":getattr(settings, "ENABLE_MODULES", []),
            "INOUT":settings.INOUT,
            "INPUT_SETTINGS":getattr(settings, "INPUT_SETTINGS", {}),
            "FILTER_SETTINGS":getattr(settings, "FILTER_SETTINGS", {}),
            "OUTPUT_SETTINGS":getattr(settings, "OUTPUT_SETTINGS", {}),
            }

try:
    import settings as settings__
    settings = settings_loader(settings__)
except ImportError:
    sys.exit("Error : Cannot import settings module.")

def setting_replacer(re_pattern, replace_list):
    settings_dir = os.path.dirname(os.path.abspath(__file__)) + "settings.py"
    with open(settings_dir,"r+w") as f:
        base_str = [part_s for part_s in re.split(re_pattern,f.read()) if part_s]
        setting_strs = []
        for i in range(len(base_str)+len(replace_list)):
            if i%2==0:
                setting_strs.append(base_str[i/2])
            else:
                setting_strs.append(str(replace_list[(i-1)/2]))
        f.seek(0)
        f.writelines(setting_strs)

def twitterinitializer():
    global settings
    twitter_setting = settings.get("INPUT_SETTINGS").get("twitter",[])
    if isinstance(twitter_setting, dict):
        twitter_setting = [twitter_setting]
    tokens = []
    api = Api()
    for i in range(len(twitter_setting)):
        print "\n\n---> Authorize %dth account." % i
        tokens.append(api.initializer())
    re_pattern = r'''{\s?["']atokensecret["']\s?:\s?["']([a-zA-Z0-9]+)?["']\s?,\s?["']atoken["']\s?:\s?["']([a-zA-Z0-9-]+)?["']\s?}'''
    setting_replacer(re_pattern, tokens)
    reload(settings__)
    settings = settings_loader(settings__)
    
class Daemon(object):
    def __init__(self):
        self.pidfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), "boxnya.pid")
        self.stdin = '/dev/null'
        self.stdout = 'dev/null'
        self.stderr = 'dev/null'
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

def handler(signum, frame):
    pass
signal.signal(signal.SIGTERM, handler)
signal.signal(signal.SIGINT, handler)

def main():
    global settings
    # ENABLE_MODULESが空なら全てのモジュールが有効なので, twitterは読み込まれる筈
    if not settings["ENABLE_MODULES"] or "twitter" in settings["ENABLE_MODULES"]:
        twitter_setting = settings["INPUT_SETTINGS"].get("twitter",{})
        if isinstance(twitter_setting,dict):
            twitter_setting = [twitter_setting]
        if not (twitter_setting[0].get("atokensecret") and twitter_setting[0].get("atoken")):
            twitterinitializer()
    
    master = Master(settings)
    master.start()
    signal.pause()
    master.join()

if __name__ == "__main__":
    if len(sys.argv) == 2 and 'init' == sys.argv[1]:
        twitterinitializer()
    if settings["DAEMON"]:
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