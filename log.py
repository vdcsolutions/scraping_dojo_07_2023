import logging


class Logger:
    def __init__(self, format: str) -> None:
        """
        Initialize the Logger instance. Set console logs for all levels and saves errors to errors.log

        Args:
            format (str): The format for log messages.
            debug (bool, optional): If True, enables debug mode and logs to 'debug.log'.
        """
        self.logger = logging.getLogger(__name__)
        console_handler = logging.StreamHandler()
        self.formatter = logging.Formatter(format)
        console_handler.setFormatter(self.formatter)
        self.logger.addHandler(console_handler)



        self.logger.setLevel(logging.INFO)
        console_handler.setLevel(logging.INFO)

        error_file_handler = logging.FileHandler('error.log')
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(self.formatter)
        self.logger.addHandler(error_file_handler)


    def enable_debug_mode(self, console_hander):
        self.logger.setLevel(logging.DEBUG)
        console_handler.setLevel(logging.DEBUG)

        debug_file_handler = logging.FileHandler('debug.log')
        debug_file_handler.setLevel(logging.DEBUG)
        debug_file_handler.setFormatter(self.formatter)
        self.logger.addHandler(debug_file_handler)
        self.logger.debug('RUNNING IN DEBUG MODE')

    def debug(self, message: str) -> None:
        """
        Log a debug level message.

        Args:
            message (str): The message to be logged.
        """
        self.logger.debug(message)

    def error(self, message: str) -> None:
        """
        Log an error level message.

        Args:
            message (str): The message to be logged.
        """
        self.logger.error(message)

    def info(self, message: str) -> None:
        """
        Log an info level message.

        Args:
            message (str): The message to be logged.
        """
        self.logger.info(message)

logger = Logger('%(asctime)s - %(levelname)s - %(message)s')
