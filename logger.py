"""
Logger interface class

Sets up a logger to use with your project

Created: 2020 05

Usage:
    Init: Set a variable equal to the Interface. Pass arguments:
        logname=<name of project-scope log>
        filename=<filename for log>
        level=<a valid logger level> (all caps)
            Typical level values are DEBUG and INFO
        LogInterface = clsLogger.Interface(logname=logname, filename='md3.log', level='DEBUG')

    Set a variable equal to the start() method:
        log = LogInterface.start()

    Now you're ready to log your events:
        log.debug('some detailed information here')
        log.info('hello, world!')
        log.critical('something bad happened!')

"""

import logging

class Interface:

    def __init__(self, **kw):

        from sys import exit

        try:
            self._filename = kw.get('filename')
            self._name = kw.get('logname')
            self._level = kw.get('level')
            if not (self._filename and self._name and self._level):
                raise
        except Exception:
            print('Error in %s:' % __name__)
            print('clsLogger interface requires filename=, logname=, and level= arguments.')
            exit()
        else:
            logging.basicConfig(
                filename=self._filename,
                datefmt='%Y-%m-%d %H:%M:%S',
                format='%(asctime)s %(levelname)s line %(lineno)d: %(message)s',
                level=logging.getLevelName(self._level))


    def start(self):
        return logging.getLogger(self._name)


    def prune(self, **kw):
        """
        Prune the log to <keep> lines when it exceeds <threshold> lines
        """
        threshold = kw.get('threshold')
        keep = kw.get('keep')
        filename = self._filename
        with open(filename, 'r') as f:
            log_data = f.read().split('\n')
        if len(log_data) > threshold:
            with open(filename, 'w') as f:
                for row in log_data[-keep:-1]:
                    f.write(f'{row}\n')
