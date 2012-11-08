Syslog Processor
================

A framework for processing syslog messages using Python


Handlers
--------

Handlers are created by subclassing handler.LogEntryHandler and placing a
module in the handlers directory. Each subclass of LogEntryHandler in this
directory is instanciated once.

Handlers pass filters for the entries they are interested to their parent class
in their constructor. See the example handlers and handler.py for more
information.


Configuration
-------------

Run syslogprocessor -h for argument information

