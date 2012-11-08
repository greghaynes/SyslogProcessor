from setuptools import setup

setup(name='SyslogProcessor',
    version='0.1.0',
    description='Syslog processing framework',
    author='Gregory Haynes',
    author_email='greg@greghaynes.net',
    url='http://github.com/greghaynes/SyslogProcessor',
    license='MIT',
    py_modules=['syslogprocessor', 'handler', 'handlers'],
    install_requires=['argparse>=1.2.1',
              'loggerglue>=1.0',
              'pyparsing>=1.5.6',
              'sspps>=0.1.3'],
    scripts=['syslogprocessor']
    )
