Syslog Processor
================

A framework for processing syslog messages using Python


How it works
------------

Syslog Processor acts as a syslog server, and accepts Syslog23 style syslog messages as input over tcp. The typical method of use is to forward all messages from a logging server to a syslog processor using this protocol.

The following line will forward all messages in rsyslog to a Syslog Procesor

<pre>
*.* @@(o)localhost:6514;RSYSLOG_SyslogProtocol23Format
</pre>


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
* app\_name - Name of app which created the message
* procid - ID (numeral) of process which created the message
* msgid - A numeric ID for the message
* msg - Message data

Additionally, filters can be marked as not disjunctive (making them conjunctive). By default filters are disjunctive. When in disjunctive form, the filters can be thought of as a list of boolean values (whether the filter matches the message) or'd together. When in conjunctive form the filters are combined using and's. When in disjunctive form a filter set to None represents a filter which matches no values. When in conjunctive form a filter set to none represents a filter that matches all values.


Configuration
-------------

Run syslogprocessor -h for argument information

