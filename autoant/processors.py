from __future__ import unicode_literals
import io
import re, os, pickle, shutil, sys
import logging
import copy
from threading import Thread
from Queue import Queue
from ftplib import FTP, FTP_TLS
from sys import platform
from .utilslinux import is_file_open
from .utils import boolstr, sub_list
from .providers import BaseProvider, register_processor, register_property, PROP_HIDDEN_PREFIX

try:
    import paramiko
except:
    paramiko = None

try:
    from smb.SMBConnection import SMBConnection
except:
    SMBConnection = None


log = logging.getLogger(__name__)

DEFAULT_CONNECT_TIMEOUT = 10
DEFAULT_CHANNEL_TIMEOUT = 10
DEFAULT_FTP_PORT = 21
save_file_extension = 'sav'


def assert_file_locked(file_item):
    if platform == 'linux2':
        if is_file_open(file_item.full_path):
            raise Exception("File is open")


class ProcessThread(Thread):
    """
        Process thread
    """
    def __init__(self, thread_id, processor, p_state):
        super(ProcessThread, self).__init__()
        self.thread_id = thread_id
        self.processor = processor
        self.p_state = p_state
        self.processor.pre_process()

    def run(self):
        while True:
            if not self.p_state.queue.empty():
                item = self.p_state.queue.get()
                if item not in self.p_state.processed:
                    self.processor.pre_run(item)
                    success = self.processor.run(item)
                    if not success:
                        self.p_state.process_fails.append(item)
                    else:
                        self.p_state.processed.append(item)
                    self.processor.post_run(item)
                self.p_state.queue.task_done()

    def __del__(self):
        self.processor.post_process()



class ProcessState(object):
    """
        Keeps process data between threads.
        Holds Queue with work, processed items and failed items
    """
    def __init__(self, name):
        self.name = name
        self.processed = list()
        self.process_fails = list()
        self.queue = Queue(0)

    def _get_filename(self):
        return self.name + '.' + save_file_extension

    def save(self):
        try:
            with open(self._get_filename(), 'wb') as f:
                pickle.dump(self.processed, f)
        except Exception as e:
            log.error("{0}: Save state file error {1}".format(self.name, e))

    def load(self):
        try:
            if os.path.isfile(self._get_filename()):
                with open(self._get_filename(), 'rb') as f:
                    self.processed = pickle.load(f)
        except Exception as e:
            log.error("{0}: Load state file error {1}".format(self.name, e))


class ProcessSequence(object):
    """
        Holds and runs a process sequence with items
        from a consumer.
    """
    sequence = None
    threads = []

    def __init__(self):
        self.sequence = []

    def add_process(self, processor):
        self.sequence.append(processor)

    def run(self, generator):
        for process, i in zip(self.sequence, range(0, len(self.sequence))):
            process_state = ProcessState(process.name)
            if process.state:
                process_state.load()
            for thread_id in range(0, process.threads):
                process_c = copy.deepcopy(process)
                thread = ProcessThread(thread_id, process_c, process_state)
                thread.setDaemon(True)
                thread.start()
                self.threads.append(thread)
            for item in generator():
                if process.depends:
                    # This process depends on the previous, will only process successful items
                    if item not in previous_state.process_fails:
                        process_state.queue.put(item)
                else:
                    process_state.queue.put(item)
            process_state.queue.join()
            if process.state:
                process_state.save()
            # keep previous state for process dependency
            previous_state = process_state

    def list(self):
        for item in self.sequence:
            item.list()


@register_property('state', 'Keeps processing state, will not repeat items', boolstr, False, "True")
@register_property('depends', 'If True will only process previous processing successes', boolstr, False, "False")
@register_property('threads', 'Number of threads the process will use', int, False, "1")
class BaseProcessor(BaseProvider):
    """
        This is the base class of all processors
    """
    _prod_name = None
    _name = None

    def __init__(self, **kwargs):
        BaseProvider.__init__(self, **kwargs)
        try:
            self._prod_name = kwargs['mon_name']
            self._name = kwargs['name']
        except:
            log.critical("Missing unique name process identifier")
            exit(1)
        log.debug("Config Processor {0} with {1}".format(self.__class__.__name__, kwargs))


    @property
    def name(self):
        return self._prod_name + '.' + self._name

    @property
    def producer_name(self):
        return self._prod_name

    @property
    def process_name(self):
        return self._name

    def list(self):
        print("Process ID {0}".format(self.name))
        print("--------------------------")
        if self.state:
            self.load()
        for item in self.processed:
            print("{0}".format(item))

    def pre_process(self):
        log.debug("{0}: Begin Pre Process".format(self.name))
        return True

    def post_process(self):
        log.debug("{0}: Begin Post Process".format(self.name))
        return True

    def pre_run(self, item):
        log.debug("{0}: Begin Pre Run {1}".format(self.name, item))
        return True

    def post_run(self, item):
        log.debug("{0}: Begin Post Run {1}".format(self.name, item))
        return True

    def run(self, item):
        log.debug("{0}: Begin Processing {1}".format(self.name, item))
        return True

    def __repr__(self):
        return self.name


class BaseProcessorRemoteCP(BaseProcessor):

    def pre_process(self):
        super(BaseProcessorRemoteCP, self).pre_process()
        return self.connect()

    def post_process(self):
        super(BaseProcessorRemoteCP, self).post_process()
        return self.disconnect()

    def connect(self):
        pass

    def disconnect(self):
        pass

    def __del__(self):
        pass

@register_property('stdout', 'Where will output go, blank is STDOUT', str, False, "")
@register_processor('echo', 'Writes produced items, default stdout')
class ProcessorEcho(BaseProcessor):
    fd = None

    def __init__(self, **kwargs):
        super(ProcessorEcho, self).__init__(**kwargs)

    def run(self, item):
        super(ProcessorEcho, self).run(item)
        try:
            self.fd.write("{0}\n".format(item.__repr__()))
            return True
        except Exception as e:
            log.error("{0}: Echo file error {1} :{2}".format(self.name, item, e))
            return False
        log.debug("End Processing {0}".format(item))


    def pre_process(self):
        super(ProcessorEcho, self).pre_process()
        if not self.stdout:
            self.fd = sys.stdout
            log.debug("{0}: Opened STDOUT".format(self.name))
        else:
            self.fd = io.open(self.stdout, 'w')
            log.debug("{0}: Opened {1}".format(self.name, self.stdout))
        return True

    def post_process(self):
        super(ProcessorEcho, self).post_process()
        if self.fd != sys.stdout:
            return self.fd.close()

@register_property('rule_origin', 'Regex origin for sub rule', str, True, "")
@register_property('rule_destination', 'Regex destination for sub rule', str, True, "")
@register_processor('rename', 'Rename local files')
class ProcessorRename(BaseProcessor):
    def __init__(self, **kwargs):
        super(ProcessorRename, self).__init__(**kwargs)

    def run(self, file_item):
        super(ProcessorRename, self).run(file_item)
        try:
            new_file_name = re.sub(r'{0}'.format(self.rule_origin), r'{0}'.format(self.rule_destination), file_item.name) 
            rel_path = file_item.get_relative_path()
            new_full_path = file_item.basedir + rel_path + new_file_name
            os.rename(file_item.full_path, new_full_path)
            log.info("{0}: Renamed file {1}".format(self.name, file_item))
        except Exception as e:
            log.error("{0}: Renamed file error file {1} :{2}".format(self.name,
                                                                       file_item, e))
            return False
        log.debug("End Processing {0}".format(file_item))
        return True


@register_property('dest_dir', 'Destination directory', str, True, "")
@register_processor('move', 'Move local files')
class ProcessorMove(BaseProcessor):
    def __init__(self, **kwargs):
        super(ProcessorMove, self).__init__(**kwargs)

    def create_path(self, remotepath):
        parts = remotepath.split('/')
        for n in range(2, len(parts)):
            path = '/'.join(parts[:n])
            try:
                os.mkdir(path)
            except:
                pass

    def run(self, file_item):
        print file_item
        super(ProcessorMove, self).run(file_item)
        try:
            assert_file_locked(file_item)
            rel_path = file_item.get_relative_path()
            dest_path = self.dest_dir + rel_path
            self.create_path(dest_path)
            shutil.move(file_item.full_path, dest_path)
            log.info("{0}: Moved file {1}".format(self.name, file_item))
        except Exception as e:
            log.error("{0}: Moved file error file {1} :{2}".format(self.name,
                                                                       file_item, e))
            return False
        log.debug("End Processing {0}".format(file_item))
        return True


@register_property('dest_dir', 'Destination directory', str, True, "")
@register_processor('cp', 'Copies local files')
class ProcessorCopy(BaseProcessor):
    def __init__(self, **kwargs):
        super(ProcessorCopy, self).__init__(**kwargs)

    def __repr__(self):
        return "{0}".format(self.dest_dir)

    def create_path(self, remotepath):
        parts = remotepath.split('/')
        for n in range(2, len(parts)):
            path = '/'.join(parts[:n])
            try:
                os.mkdir(path)
            except:
                pass

    def run(self, file_item):
        super(ProcessorCopy, self).run(file_item)
        try:
            assert_file_locked(file_item)
            rel_path = file_item.get_relative_path()
            self.create_path(self.dest_dir + rel_path)
            destination_path = self.dest_dir + rel_path + file_item.name
            shutil.copyfile(file_item.full_path, destination_path)
            log.info("{0}: Copy file {1}".format(self.name, file_item))
        except Exception as e:
            log.error("{0}: Copy file error {1} :{2}".format(self.name,
                                                                       file_item, e))
            return False
        log.debug("End Processing {0}".format(file_item))
        return True


@register_property('remote_host', 'The remote hostname or IP', str, True, "")
@register_property('remote_name', 'The remote host SMB Name.', str, True, "")
@register_property('local_name', 'The local host SMB Name', str, True, "")
@register_property('remote_dir', 'The remote directory', str, True, "")
@register_property('username', 'The username to authenticate', str, True, "")
@register_property('password', 'The password to authenticate', str, True, "")
@register_property('debug_level', 'The debug level 0,1,2', int, False, "0")
@register_property('timeout', 'The connection timeout in seconds', float, False, DEFAULT_CONNECT_TIMEOUT)
@register_processor('smb', 'Copies files using SMB')
class ProcessorSMB(BaseProcessorRemoteCP):
    smb_conn = None

    def __init__(self, **kwargs):
        super(ProcessorSMB, self).__init__(**kwargs)
        if not SMBConnection:
            log.error("No pySMB package please install")

    def __repr__(self):
        return "{0}@{1}:{2}".format(self.username, self.remote_host, self.remote_dir)


    def connect(self):
        try:
            self.smb_conn = SMBConnection(self.username, self.password, self.local_name, self.remote_name)
            print self.remote_host
            self.smb_conn.connect(self.remote_host)
        except Exception as e:
            log.error("{0}: Connect error to {1} {2}".format(self.name, self.remote_host, e))
            return False
        log.info("{0}: SMB Connected to {1} with {2}".format(self.name, self.remote_host, self.username))
        return True

    def disconnect(self):
        try:
            self.smb_conn.close()
        except Exception as e:
            log.error("{0}: Disconnect error to {1} {2}".format(self.name, self.remote_host, e))
            return False
        log.info("{0}: SMB Disconnected from {1} with {2}".format(self.name, self.remote_host, self.username))

    def create_path(self, remotepath):
        parts = remotepath.split('/')
        for n in range(2, len(parts)):
            path = '/'.join(parts[:n])
            try:
                self.smb_conn.createDirectory(self.remote_dir, path)
            except:
                pass

    def run(self, file_item):
        super(ProcessorSMB, self).run(file_item)
        try:
            assert_file_locked(file_item)
            rel_path = file_item.get_relative_path()
            remote_path = self.remote_dir + rel_path + file_item.name
            self.create_path(remote_path)
            fd = open(file_item.full_path, 'r')
            self.smb_conn.storeFile(self.remote_dir, remote_path, fd)
            fd.close()
            log.info("{0}: SMB Put file {1}".format(self.name, file_item))
        except Exception as e:
            log.error("{0}: SMB Put error to {1} file {2} :{3}".format(self.name,
                                                                       self.remote_host,
                                                                       file_item, e))
            return False
        log.debug("End Processing {0}".format(file_item))
        return True


@register_property('remote_host', 'The remote hostname or IP', str, True, "")
@register_property('remote_port', 'The remote FTP Port.', int, False, DEFAULT_FTP_PORT)
@register_property('remote_dir', 'The remote directory', str, True, "")
@register_property('username', 'The username to authenticate', str, True, "")
@register_property('password', 'The password to authenticate', str, False, "")
@register_property('is_ssl_auth', 'Is auth encrypted?', boolstr, False, "False")
@register_property('is_ssl_data', 'Is Data encrypted?', boolstr, False, "False")
@register_property('key_filename', 'Filename of key file for auth.', str, False, None)
@register_property('debug_level', 'The debug level 0,1,2', int, False, "0")
@register_property('timeout', 'The connection timeout in seconds', float, False, DEFAULT_CONNECT_TIMEOUT)
@register_processor('ftp', 'Copies files using FTP')
class ProcessorFTP(BaseProcessorRemoteCP):
    ftp = None

    def __init__(self, **kwargs):
        super(ProcessorFTP, self).__init__(**kwargs)

    def __repr__(self):
        return "{0}@{1}:{2}".format(self.username, self.remote_host, self.remote_dir)

    def connect(self):
        try:
            if self.is_ssl_auth or self.is_ssl_data:
                log.debug("{0}: FTP with SSL/TLS".format(self.name))
                self.ftp = FTP_TLS()
            else:
                log.debug("{0}: FTP no SSL".format(self.name))
                self.ftp = FTP()
            self.ftp.set_debuglevel(self.debug_level)
            self.ftp.connect(self.remote_host, self.remote_port, timeout=self.timeout)
            if self.is_ssl_auth:
                self.ftp.auth()
            self.ftp.login(user=self.username, passwd=self.password)
            if self.is_ssl_data:
                self.ftp.prot_p()
        except Exception as e:
            log.error("{0}: Connect error to {1} {2}".format(self.name, self.remote_host, e))
            return False
        log.info("{0}: FTP Connected to {1} with {2}".format(self.name, self.remote_host, self.username))
        return True

    def disconnect(self):
        try:
            self.ftp.close()
        except Exception as e:
            log.error("{0}: Disconnect error to {1} {2}".format(self.name, self.remote_host, e))
            return False
        log.info("{0}: FTP Disconnected from {1} with {2}".format(self.name, self.remote_host, self.username))

    def create_path(self, remotepath):
        parts = remotepath.split('/')
        for n in range(2, len(parts)):
            path = '/'.join(parts[:n])
            try:
                self.ftp.mkd(path)
            except:
                pass

    def run(self, file_item):
        super(ProcessorFTP, self).run(file_item)
        try:
            assert_file_locked(file_item)
            rel_path = file_item.get_relative_path()
            remote_path = self.remote_dir + rel_path + file_item.name
            self.create_path(remote_path)
            fd = open(file_item.full_path, 'r')
            self.ftp.storbinary("STOR " + remote_path, fd)
            fd.close()
            log.info("{0}: FTP Put file {1}".format(self.name, file_item))
        except Exception as e:
            log.error("{0}: FTP Put error to {1} file {2} :{3}".format(self.name,
                                                                       self.remote_host,
                                                                       file_item, e))
            return False
        log.debug("End Processing {0}".format(file_item))
        return True


@register_property('remote_host', 'The remote hostname or IP', str, True, "")
@register_property('remote_dir', 'The remote directory', str, True, "")
@register_property('username', 'The username to authenticate', str, True, "")
@register_property('password', 'The password to authenticate', str, False, "")
@register_property('key_filename', 'Filename of key file for auth.', str, False, None)
@register_property('channel_timeout', 'The channel timeout in seconds', float, False, DEFAULT_CHANNEL_TIMEOUT)
@register_property('timeout', 'The connection timeout in seconds', float, False, DEFAULT_CONNECT_TIMEOUT)
@register_processor('scp', 'Copies files using SFTP')
class ProcessorSCP(BaseProcessorRemoteCP):
    sftp = None

    def __init__(self, **kwargs):
        super(ProcessorSCP, self).__init__(**kwargs)
        try:
            self.ssh = paramiko.SSHClient()
        except:
            log.error("No paramiko package please install, run: pip install paramiko")

    def __repr__(self):
        return "{0}@{1}:{2}".format(self.username, self.remote_host, self.remote_dir)

    def connect(self):
        try:
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(self.remote_host,
                             username=self.username,
                             password=self.password,
                             key_filename=self.key_filename,
                             timeout=self.timeout)
        except Exception as e:
            log.error("{0}: Connect error to {1} {2}".format(self.name, self.remote_host, e))
            return False
        try:
            self.sftp = self.ssh.open_sftp()
            self.sftp.get_channel().settimeout(self.channel_timeout)
        except Exception as e:
            log.error("{0}: Open SFTP error to {1} {2}".format(self.name, self.remote_host, e))
            return False
        log.info("{0}: SFTP Connected to {1} with {2}".format(self.name, self.remote_host, self.username))
        return True

    def disconnect(self):
        try:
            self.sftp.close()
            self.ssh.close()
        except Exception as e:
            log.error("{0}: Disconnect error to {1} {2}".format(self.name, self.remote_host, e))
            return False
        log.info("{0}: SFTP Disconnected from {1} with {2}".format(self.name,
                                                                   self.remote_host,
                                                                   self.username))

    def create_path(self, remotepath):
        parts = remotepath.split('/')
        for n in range(2, len(parts)):
            path = '/'.join(parts[:n])
            try:
                self.sftp.stat(path)
            except:
                self.sftp.mkdir(path)

    def run(self, file_item):
        super(ProcessorSCP, self).run(file_item)
        try:
            assert_file_locked(file_item)
            rel_path = file_item.get_relative_path()
            remote_path = self.remote_dir + rel_path + file_item.name
            self.create_path(remote_path)
            self.sftp.put(file_item.full_path, remote_path)
            log.info("{0}: SFTP Put file {1}".format(self.name, file_item))
        except Exception as e:
            log.error("{0}: SFTP Put error to {1} file {2} :{3}".format(self.name,
                                                                        self.remote_host,
                                                                        file_item, e))
            return False
        log.debug("{0}: End Processing {1}".format(self.name, file_item))
        return True

