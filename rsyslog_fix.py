from loggerglue import rfc5424 as loggerglue
import pyparsing

def fix():
    loggerglue.syslog_msg = pyparsing.LineStart() + loggerglue.header +\
        pyparsing.Optional(loggerglue.structured_data) +\
        pyparsing.Optional(loggerglue.sp+loggerglue.msg) + pyparsing.LineEnd()

