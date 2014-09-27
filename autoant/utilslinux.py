"""
    Copyright (c) 2009, Jay Loden, Dave Daeschler, Giampaolo Rodola'
"""

import os
import errno
import sys
import stat

PY3 = sys.version_info[0] == 3

if PY3:
    def u(s):
        return s

    def b(s):
        return s.encode("latin-1")
else:
    def u(s):
        return unicode(s, "unicode_escape")

    def b(s):
        return s


def pids():
    """Returns a list of PIDs currently running on the system."""
    return [int(x) for x in os.listdir(b('/proc')) if x.isdigit()]


def isfile_strict(path):
    """Same as os.path.isfile() but does not swallow EACCES / EPERM
    exceptions, see:
    http://mail.python.org/pipermail/python-dev/2012-June/120787.html
    """
    try:
        st = os.stat(path)
    except OSError:
        err = sys.exc_info()[1]
        if err.errno in (errno.EPERM, errno.EACCES):
            raise
        return False
    else:
        return stat.S_ISREG(st.st_mode)


def open_files(pid):
        retlist = []
        files = os.listdir("/proc/%s/fd" % pid)
        hit_enoent = False
        for fd in files:
            file = "/proc/%s/fd/%s" % (pid, fd)
            if os.path.islink(file):
                try:
                    file = os.readlink(file)
                except OSError:
                    # ENOENT == file which is gone in the meantime
                    err = sys.exc_info()[1]
                    if err.errno in (errno.ENOENT, errno.ESRCH):
                        hit_enoent = True
                        continue
                    raise
                else:
                    # If file is not an absolute path there's no way
                    # to tell whether it's a regular file or not,
                    # so we skip it. A regular file is always supposed
                    # to be absolutized though.
                    if file.startswith('/') and isfile_strict(file):
                        retlist.append(str(file))
        if hit_enoent:
            # raise NSP if the process disappeared on us
            os.stat('/proc/%s' % pid)
        return retlist


def is_file_open(full_path):
    for pid in pids():
        try:
            files = open_files(pid)
            if full_path in files:
                return True
        except Exception as e:
            continue
    return False
