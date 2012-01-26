# -*- coding: utf-8 -*-
import time
from core import Master

if __name__ == "__main__":
    try:
        master = Master()
        master.start()
        time.sleep(15)
    except KeyboardInterrupt:
        pass
    master.join()
    quit()