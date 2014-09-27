import sys
import logging
from datetime import datetime
from autoant import DirsProcessor


logging.basicConfig(format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger('paramiko').setLevel(logging.ERROR)

dp = DirsProcessor('config.json')
t1 = datetime.now()
dp.run()
t2 = datetime.now()
t3 = t2-t1
print("TIME: {0}".format(t3))
#dp.list()
