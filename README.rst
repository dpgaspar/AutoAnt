Auto Ant
========

AutoAnt is a generic processing automation package. It's ideal for file processing, if you need
to process/syncronize/move files on several directories to different locations (local or remote)
and then renaming/moving/deleting or what ever you want. This is the answer.

It's extremely flexible and extensible, just describe your Sys Admin file/*something* processing nightmare
on a JSON file.

Documentation
=============

Take a look at installation, quick how to tutorials, API reference etc: `Documentation <http://autoant.readthedocs.org/en/latest/>`_

Features:
---------

  - Remote 'Copy' files using SMB(SAMBA), FTP, FTPS, SFTP(SSH).
  - Local process, move, copy and rename.
  - Filter and Rename files using regular expressions.
  - Open file detection (Linux only).
  - Optional, parallel (Threads) processing.
  - Differential processing, only process what has changed. (On directories, only new or modified files).
  - Highly extensible base, you can easily create your own **processors**, or **producers**

