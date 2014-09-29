import os
import datetime
import ntpath
from _compat import as_unicode

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

    def __init__(self, file_name, basedir=''):
        self.basedir = basedir
        # TODO use os.path.join
        file_name = file_name.decode('utf-8')
        self.full_path = file_name
        (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(self.full_path)
        self.name = ntpath.basename(file_name)
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

    @classmethod
    def check_time(cls, value, ftime):
        t1 = datetime.datetime.now()
        t2 = datetime.datetime.fromtimestamp(ftime)
        if value >= 0:
            t3 = t1 - datetime.timedelta(minutes=value)
            return t2 < t3
        else:
            t3 = t1 + datetime.timedelta(minutes=value)
            return t2 > t3

    @classmethod
    def check_mtime(cls, file_name, value):
        if value == 0:
            return True
        (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(file_name)
        return cls.check_time(value, mtime)

    @classmethod
    def check_atime(cls, file_name, value):
        if value == 0:
            return True
        (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(file_name)
        return cls.check_time(value, atime)

    @classmethod
    def check_ctime(cls, file_name, value):
        if value == 0:
            return True
        (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(file_name)
        return cls.check_time(value, ctime)

    def __repr__(self):
        return self.full_path

    def set_processed_ts(self):
        # Timestamps file item when processed
        self.processed_time = datetime.datetime.now()

    def get_relative_path(self):
        return self.full_path.replace(self.basedir, '').replace(self.name, '')

