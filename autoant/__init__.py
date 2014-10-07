import logging
import os
from .producers import DirMon
from .providers import providers

try:
    from itsdangerous import simplejson as _json
except ImportError:
    from itsdangerous import json as _json

log = logging.getLogger(__name__)


class AutoAnt(object):

    _is_locked = False

    def __init__(self, config):
        if not os.path.exists(config):
            log.critical("No config file named {0} found.".format(config))
            exit(2)
        self.config_name = config
        self.make_lock()
        self.config = self._obj_from_json(config)
        self._config = []
        for config_item in self.config:
            for producer_args in config_item['producer_sequence']:
                producer_class = providers.get_class(producer_args['type_key'])
                producer = producer_class(**producer_args)
                for process in config_item['process_sequence']:
                    processor_class = providers.get_class(process['type_key'])
                    process['mon_name'] = producer_args['name']
                    processor = processor_class(**process)
                    producer.add_process(processor)

                self._config.append(producer)

    @property
    def _lock_name(self):
        return '_' + self.config_name

    def make_lock(self):
        if os.path.exists(self._lock_name):
            log.fatal("An instance is already running, exiting")
            self._is_locked = True
            exit(2)
        fd = open(self._lock_name, 'w')
        fd.close()

    def __del__(self):
        try:
            if not self._is_locked:
                os.remove(self._lock_name)
        except:
            pass

    def run(self):
        for item in self._config:
            thread_list = []
            if item.is_thread:
                thread_list.append(item)
                item.start()
            else:
                item.run()
        for thread_item in thread_list:
            thread_item.join()

    def list(self):
        """
            List the states of producers
        """
        for item in self._config:
            item.list()

    def describe(self):
        for item in self._config:
            print("{0} : {1}".format(providers.get_short_description(item.__class__), item))
            for process in item.process_sequence.sequence:
                print("-> {0} : {1}".format(providers.get_short_description(process.__class__), process))


    def _obj_from_json(self, filename):
        try:
            with open(filename) as json_file:
                obj = _json.loads(json_file.read())

        except Exception as e:
            log.critical('Unable to load configuration file (%s)' % e.message)
            exit(1)
        return obj
