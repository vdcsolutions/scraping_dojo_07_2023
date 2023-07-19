import logging

class Logger:
    def __init__(self, format):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        self.formatter = logging.Formatter(format)
        console_handler.setFormatter(self.formatter)
        self.logger.addHandler(console_handler)

        error_file_handler = logging.FileHandler('error.log')
        debug_file_handler = logging.FileHandler('debug.log')
        error_file_handler.setLevel(logging.ERROR)
        debug_file_handler.setLevel(logging.DEBUG)
        error_file_handler.setFormatter(self.formatter)
        debug_file_handler.setFormatter(self.formatter)
        self.logger.addHandler(error_file_handler)
        self.logger.addHandler(debug_file_handler)

    def debug(self, message):
        self.logger.debug(message)

    def error(self, message):
        self.logger.error(message)

    def info(self, message):
        self.logger.info(message)
