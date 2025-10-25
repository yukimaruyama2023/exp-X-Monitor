import subprocess
import atexit
import time
import os
import itertools
import signal
import sys
# import numpy as np

num_memcacheds = [1,5,10]

conf_root = "../conf"

netdata_conf = f"{conf_root}/{str(num_memcacheds[0]).zfill(3)}mcd/netdata.conf"
subprocess.run(f"sudo netdata -c {netdata_conf} -D".split())

# for num_memcached in num_memcacheds:
# 	netdata_conf = f"{conf_root}/{str(num_memcached).zfill(3)}mcd/netdata.conf"
# 	subprocess.run(f"netdata -c {netdata_conf} -D".split())
#     subprocess.run("sudo pkill netdata".split())

	######################

