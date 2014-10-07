
import logging
import os, re
from threading import Thread
from .utils import boolstr, walkfiles
from .items import FileItem
from .processors import ProcessSequence
from .providers import BaseProvider, register_producer, register_property
log = logging.getLogger(__name__)


class BaseProducer(BaseProvider, Thread):
    """
        All Consumer objects classes inherit from this
    """
    process_sequence = None

    def __init__(self, thread=False, **kwargs):
        Thread.__init__(self)
        BaseProvider.__init__(self, **kwargs)
        self.is_thread = boolstr(thread)
        self._process_sequence = ProcessSequence()

    @property
    def process_sequence(self):
        return self._process_sequence

    def add_process(self, processor):
        self._process_sequence.add_process(processor)

    def get_items(self):
        """
            Override this method to write your own producer.
            Return a list of produced items.
        """
        return []

    def run(self):
        self.process_sequence.run(self.generator)

    def list(self):
        self.process_sequence.list()


@register_property('file_name', 'File name to read', str, True, "")
@register_producer('read', 'Reads file')
class Read(BaseProducer):
    def __init__(self, **kwargs):
        super(Read, self).__init__(**kwargs)

    def generator(self):
        pass


@register_property('basedir', 'Directory to monitor', str, True, "")
@register_property('recursive', 'Is monitor recursive', boolstr, False, "True")
@register_property('filter', 'RegEx filter to filenames', str, False, ".*")
@register_property('mtime', 'Filter files with modified TS', int, False, "0")
@register_property('atime', 'Filter files with accessed TS', int, False, "0")
@register_property('ctime', 'Filter files with creation TS', int, False, "0")
@register_producer('dir_mon', 'Monitors directory changes between runs')
class DirMon(BaseProducer):
    """
        Consumer that recursively walks a directory structure
        and collects files do deliver to a process sequence
    """
    def __init__(self, **kwargs):
        super(DirMon, self).__init__(**kwargs)


    def generator(self):
        if not os.path.exists(self.basedir):
            log.error("Path does not exist {0}".format(self.basedir))
            yield []
        if not self.recursive:
            level = 0
        else:
            level = -1
        for file_name in walkfiles(self.basedir, self.filter, level):
                # filter file name
                    if FileItem.check_mtime(file_name, self.mtime) and \
                        FileItem.check_atime(file_name, self.atime) and \
                        FileItem.check_ctime(file_name, self.ctime):
                        yield FileItem(file_name, self.basedir)

    def __repr__(self):
        return "Base Dir:{0}, Recursive: {1}, Filter: {2}".format(self.basedir, self.recursive, self.filter)

