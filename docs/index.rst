Auto Ant
========

AutoAnt is an object processing automation package. It's ideal for file processing, if you need
to process/syncronize/move files on several directories to different locations (local or remote)
and then renaming/moving/deleting or what ever you want. This is the answer.

It's extremely flexible and extensible, just describe your Sys Admin file/*something* processing nightmare
on a JSON file.

Fixes, bugs and contributions
-----------------------------

You're welcome to report bugs, propose new features, or even better contribute to this project.

`Issues, bugs and new features <https://github.com/dpgaspar/AutoAnt/issues/new>`_

`Contribute <https://github.com/dpgaspar/AutoAnt/fork>`_

The Idea
--------

AutoAnt contains two types of abstraction classes, **Producers** and **Processors**.

Producers - Will produce objects to be processed.
Processors - Will process the objects.

The config file is a list of objects containing the following structure::

    [
        {
            "producer_sequence": [
                {
                    "name": "SOME UNIQUE ID",
                    "producer_type": "KEY OF PRODUCER",
                    ...
                },
                ...
            ]
            "processor_sequence": [
                {
                    "name": "SOME UNIQUE ID",
                    "processor_type": "KEY OF PROCESSOR",
                    ...
                },
                ....
            ]
        },
        ....
    ]


Quick HowTo
-----------

Enough talk, let's go right into a quick example.

Let's say you have some file processing to do, and you need to automate it, probably you have already
made tons of similar scripts on file automation, but every time you have a new problem, you have to
write something new for the same abstract issue.

So, you have a database that generates data files, this files are supposed to be processed on a remote
server, for the first task you have to copy every new file to a remote FTP server.

We are going to write a JSON configuration file describing AutoAnt solution,
create a file named config.json::


    [
        {
            "producer_sequence": [
                {
                    "producer_type": dir_mon",
                    "name": "DBSOURCE",
                    "basedir": "/db/export/contacts",
                    "recursive": "True"
                }
            ]
            "process_sequence": [
                {
                    "name": "Remote",
                    "processor_type": "ftp",
                    "remote_dir": "/contacts",
                    "remote_host": "remoteserver.domain.com",
                    "username": "user",
                    "password": "password"
                }
            ]
        }
    ]

Know add to your scheduling system **crontab** on *NIX or **Schedule Tasks** on Windows.

crontab::

     5 * * * * autoant_console

AutoAnt will every 5 minutes look for new files on your local directory */db/exports/contacts/ every new
file will be sent to *remoteserver.domain.com*. This is ok, what will Auto add to this apparently simple task

- You will have a detailed and highly configurable log, using python's standard lib, logging.
- If something goes wrong on your file processing (remote server is down or something),
  the failed files will be reprocessed next time, without the use of moving/coping/renaming the succeeded ones.
- The copy is recursive and differential the directory structure will be created on the remote site.
- If a file is still open (being created by the database on this example), the file is not processed this time.
  (Linux only feature).
- Integrated extensible highly configurable system.
- Over loop prevention, autoant will not run if another instance using the same config is still processing.

Know your company wants to copy the same files to a different server this time using sftp protocol.
No problem, just edit your **config.json** file like this::

    [
        {
            "producer_sequence": [
                {
                    "producer_type": dir_mon",
                    "name": "DBSOURCE",
                    "basedir": "/db/export/contacts",
                    "recursive": "True"
                }
            ]
            "process_sequence": [
                {
                    "name": "Remote",
                    "processor_type": "ftp",
                    "remote_dir": "/contacts",
                    "remote_host": "remoteserver.domain.com",
                    "username": "user",
                    "password": "password"
                },
                {
                    "name": "Remote2",
                    "processor_type": "scp",
                    "remote_dir": "",
                    "remote_host": "remoteserver2.domain.com",
                    "username": "user2",
                    "password": "password"
                }

            ]
        }
    ]


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`






