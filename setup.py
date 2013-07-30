from setuptools import setup

setup(name='SyslogProcessor',
    version='0.1.1',
    description='Syslog processing framework',
    author='Gregory Haynes',
    author_email='greg@greghaynes.net',
    url='http://github.com/greghaynes/SyslogProcessor',
    license='MIT',
    py_modules=['syslogprocessor', 'handler', 'rsyslog_fix', 'logwriter'],
    install_requires=['argparse>=1.2.1',
              'loggerglue>=1.0',
              'pyparsing>=1.5.6',
              'sspps>=0.1.4',
              'python-daemon>=1.5.5'],
    scripts=['scripts/syslogprocessor']
    )
