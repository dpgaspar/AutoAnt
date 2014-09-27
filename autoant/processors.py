import re, os, pickle, shutil
import logging
from ftplib import FTP, FTP_TLS
from sys import platform
from .utilslinux import is_file_open
from .utils import boolstr, sub_list
from .providers import register_processor

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


class ProcessSequence(object):
    """
        Holds and runs a process sequence with items
        from a consumer.
    """
    sequence = None

    def __init__(self):
        self.sequence = []

    def add_process(self, processor):
        self.sequence.append(processor)

    def run(self, current):
        for process, i in zip(self.sequence, range(0, len(self.sequence))):
            if process.depends and i > 0:
                new_current = sub_list(current, self.sequence[i - 1].process_fails)
                process.run_all(new_current)
            else:
                process.run_all(current)

    def list(self):
        for item in self.sequence:
            item.list()


class BaseProcessor(object):
    """
        This is the base class of all processors
    """
    processed = None
    process_fails = None
    _prod_name = None
    _name = None
    
    def __init__(self, **kwargs):
        try:
            self._prod_name = kwargs['mon_name']
            self._name = kwargs['name']
        except:
            log.exception("Missing unique name process identifier")
        self.state = boolstr(kwargs.get('state', "True"))
        self.depends = boolstr(kwargs.get('depends', "False"))
        self.processed = []
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

    def _get_filename(self):
        return self.name + '.' + save_file_extension

    def run_all(self, current):
        if self.state:
            self.load()
        process = sub_list(current, self.processed)
        self.process_fails = []
        if self.pre_process():
            for file_item in process:
                self.pre_run(file_item)
                success = self.run(file_item)
                if not success:
                    self.process_fails.append(file_item)
                self.post_run(file_item)
            self.post_process()
            self.processed = sub_list(current, self.process_fails)
        else:
            self.process_fails = process
        if self.state:
            self.save()

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



@register_processor('rename', 'Rename local files')
class ProcessorRename(BaseProcessor):
    def __init__(self, **kwargs):
        super(ProcessorRename, self).__init__(**kwargs)
        try:
            self.rule_origin = kwargs['rule_origin']
            self.rule_destination = kwargs['rule_destination']
        except:
            log.exception("Missing rule parameter")

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


@register_processor('move', 'Move local files')
class ProcessorMove(BaseProcessor):
    def __init__(self, **kwargs):
        super(ProcessorMove, self).__init__(**kwargs)
        try:
            self.dest_dir = kwargs['dest_dir']
        except:
            log.exception("Missing dest_dir parameter")

    def create_path(self, remotepath):
        parts = remotepath.split('/')
        for n in range(1, len(parts)):
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


@register_processor('cp', 'Copies local files')
class ProcessorCopy(BaseProcessor):
    def __init__(self, **kwargs):
        super(ProcessorCopy, self).__init__(**kwargs)
        try:
            self.dest_dir = str(kwargs['dest_dir'])
        except:
            log.exception("Missing dest_dir parameter")

    def __repr__(self):
        return "{0}".format(self.dest_dir)

    def create_path(self, remotepath):
        parts = remotepath.split('/')
        for n in range(1, len(parts)):
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


@register_processor('smb', 'Copies files using SMB')
class ProcessorSMB(BaseProcessorRemoteCP):
    smb_conn = None

    def __init__(self, **kwargs):
        super(ProcessorSMB, self).__init__(**kwargs)
        self.remote_host = kwargs.get('remote_host')
        self.remote_name = str(kwargs.get('remote_name'))
        self.local_name = str(kwargs.get('local_name'))
        self.remote_dir = kwargs.get('remote_dir')
        self.username = kwargs.get('username')
        self.password = kwargs.get('password')
        self.debug_level = int(kwargs.get('debug_level', 0))
        self.timeout = float(kwargs.get('timeout', DEFAULT_CONNECT_TIMEOUT))
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
        for n in range(1, len(parts)):
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


@register_processor('ftp', 'Copies files using FTP')
class ProcessorFTP(BaseProcessorRemoteCP):
    ftp = None

    def __init__(self, **kwargs):
        super(ProcessorFTP, self).__init__(**kwargs)
        self.remote_host = kwargs.get('remote_host')
        self.remote_port = int(kwargs.get('remote_port', DEFAULT_FTP_PORT))
        self.remote_dir = kwargs.get('remote_dir')
        self.is_ssl_auth = boolstr(kwargs.get('is_ssl_auth', "False"))
        self.is_ssl_data = boolstr(kwargs.get('is_ssl_data', "False"))
        self.username = kwargs.get('username')
        self.password = kwargs.get('password')
        self.key_filename = kwargs.get('key_filename')
        self.debug_level = int(kwargs.get('debug_level', 0))
        self.timeout = float(kwargs.get('timeout', DEFAULT_CONNECT_TIMEOUT))

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
        for n in range(1, len(parts)):
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


@register_processor('scp', 'Copies files using SFTP')
class ProcessorSCP(BaseProcessorRemoteCP):
    sftp = None

    def __init__(self, **kwargs):
        super(ProcessorSCP, self).__init__(**kwargs)
        self.remote_host = kwargs.get('remote_host')
        self.remote_dir = kwargs.get('remote_dir')
        self.username = kwargs.get('username')
        self.password = kwargs.get('password')
        self.key_filename = kwargs.get('key_filename')
        self.timeout = float(kwargs.get('timeout', DEFAULT_CONNECT_TIMEOUT ))
        self.channel_timeout = float(kwargs.get('channel_timeout', DEFAULT_CHANNEL_TIMEOUT))
        try:
            self.ssh = paramiko.SSHClient()
        except:
            log.error("No paramiko package please install")

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
        for n in range(1, len(parts)):
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




processor_providers = {'baseprocessor': BaseProcessor,
                       'scp': ProcessorSCP,
                       'ftp': ProcessorFTP}
