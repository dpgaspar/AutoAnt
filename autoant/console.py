#!/usr/bin/env python

import argparse
import logging
import datetime
from autoant import AutoAnt
from .providers import providers
from .version import VERSION_STRING

log_level = {'INFO':logging.INFO,
             'DEBUG':logging.DEBUG,
             'CRITICAL':logging.CRITICAL,
             'ERROR':logging.ERROR}

def get_log_level(str_level):
    return log_level.get(str_level,logging.INFO)

parser = argparse.ArgumentParser(description='AutoAnt')
parser.add_argument('-c', '--config', type=str, default='config.json',
                    help='Your config JSON file')
parser.add_argument('-l', '--loglevel', type=str, default='INFO',
                    help='Adjust log level accepts {0}'.format(log_level.keys()))
parser.add_argument('-p', '--providers', action='store_true', help='Shows available providers')
parser.add_argument('-s', '--state', action='store_true', help='List the state of producers')
parser.add_argument('-d', '--describe', action='store_true', help='Shows a summary of the config')
parser.add_argument('-v', '--version', action='store_true', help='Shows AutoAnt version')
parser.add_argument('-m', '--measure', action='store_true', help='Will measure run time')

args = parser.parse_args()


logging.basicConfig(format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')
logging.getLogger().setLevel(get_log_level(args.loglevel))
logging.getLogger('paramiko').setLevel(logging.ERROR)

log = logging.getLogger(__name__)

def main():
    """Entry-point function."""
    if vars(args).get('providers'):
        print(providers)
    elif vars(args).get('state'):
        aa = AutoAnt(args.config)
        aa.list()
    elif vars(args).get('describe'):
        aa = AutoAnt(args.config)
        aa.describe()
    elif vars(args).get('version'):
        print("AutoAnt {0}".format(VERSION_STRING))
    else:
        aa = AutoAnt(args.config)
        t1 = datetime.datetime.now()
        aa.run()
        t2 = datetime.datetime.now()
        if vars(args).get('measure'):
            log.info("Time to Process {0}".format(t2 - t1))


if __name__ == '__main__':
    main()
