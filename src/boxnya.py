# -*- coding: utf-8 -*-
from master import Master

if __name__ == "__main__":
    master = Master()
    master.start()
    import time
    time.sleep(10)
    master.join()
    quit()