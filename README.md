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


Filters:
* privals - A bitmask of priotity flags. See syslog documentation. This is bitmasked against the message prival to determine if the handler should be called.
* timestamp - ISO formatted timestamp
* hostname - Name of host which created the message
* app_name - Name of app which created the message
* procid - ID (numeral) of process which created the message
* msgid - A numeric ID for the message
* msg - Message data


Configuration
-------------

Run syslogprocessor -h for argument information

