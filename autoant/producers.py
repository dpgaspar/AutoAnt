
import logging
import datetime
import os, time, re
from _compat import as_unicode
from threading import Thread
from .utils import boolstr
from .processors import ProcessSequence
from .providers import register_producer
log = logging.getLogger(__name__)


class FileItem(object):
    """
        File item holds info about a file to be processed
    """
    basedir = ''
    full_path = ''
    name = ''
    size = 0
    ctime = None
    mtime = None
    atime = None
    processed_time = None

    def __init__(self, path, file_name, basedir=''):
        self.basedir = basedir
        # TODO use os.path.join
        self.full_path = os.path.join(path, file_name)
        #self.full_path = "{0}/{1}".format(path, file_name)
        (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(self.full_path)
        self.name = file_name
        self.size = size
        self.mtime = mtime
        self.ctime = ctime
        self.atime = atime

    def __eq__(self, other):
        if type(other) is type(self):
            return (self.full_path == other.full_path) and \
                    (self.size == other.size) and \
                    (self.mtime == other.mtime)
        return False

    def __repr__(self):
        return "{0} size:{1}".format(self.full_path.encode('utf-8'), self.size)

    def set_processed_ts(self):
        # Timestamps file item when processed
        self.processed_time = datetime.datetime.now()

    def get_relative_path(self):
        return self.full_path.replace(self.basedir, '').replace(self.name, '')



class BaseProducer(Thread):
    """
        All Consumer objects classes inherit from this
    """
    process_sequence = None

    def __init__(self, thread=False, **kwargs):
        super(BaseProducer, self).__init__()
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
        self.process_sequence.run(self.get_items())

    def list(self):
        self.process_sequence.list()



@register_producer('dir_mon', 'Monitors directory changes between runs')
class DirMon(BaseProducer):
    """
        Consumer that recursively walks a directory structure
        and collects files do deliver to a process sequence
    """
    basedir = ''
    recursive = False

    def __init__(self, basedir='./', recursive="True", filter=".*", **kwargs):
        super(DirMon, self).__init__(**kwargs)
        self.basedir = basedir
        self.recursive = boolstr(recursive)
        self.filter = filter

    def get_items(self):
        ret = []
        if not os.path.exists(self.basedir):
            log.error("Path does not exist {0}".format(self.basedir))
            return []
        if not self.recursive:
            for file_name in os.listdir(self.basedir):
                file_full_path = os.path.join(self.basedir, file_name)
                if re.match(self.filter, file_name) and os.path.isfile(file_full_path):
                    ret.append(FileItem(self.basedir, file_name, self.basedir))
            return ret
        for root, dirs, files in os.walk(self.basedir):
            os.path.basename(root)
            for file_name in files:
                if re.match(self.filter, file_name):
                    ret.append(FileItem(root, file_name, self.basedir))
        return ret

    def __repr__(self):
        return "Base Dir:{0}, Recursive: {1}, Filter: {2}".format(self.basedir, self.recursive, self.filter)

