import os
import re


def sub_list(x, y):
    return [item for item in x if item not in y]


def boolstr(str):
    return str == 'True'


def walklevel(some_dir, level=-1):
    if some_dir != '/':
        some_dir = some_dir.rstrip(os.path.sep)
    #assert os.path.isdir(some_dir)
    num_sep = some_dir.count(os.path.sep)
    for root, dirs, files in os.walk(some_dir):
        yield root, dirs, files
        num_sep_this = root.count(os.path.sep)
        if num_sep + level <= num_sep_this and level != -1:
            del dirs[:]


def walkfiles(directory, file_filter=".*", level=-1):
    for root, dirs, files in walklevel(directory, level):
        for file_name in files:
            file_name = os.path.join(root, file_name)
            if re.match(file_filter, file_name) and \
                    not os.path.islink(file_name):
                yield file_name

