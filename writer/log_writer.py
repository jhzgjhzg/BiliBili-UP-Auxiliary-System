"""
Custom log output and output format.
"""


import datetime
from writer import abnormal_monitor as am


class Handler:
    """
    Log output configuration class. Set the destination for log output and what level of log to output.
    """
    def __init__(self, output_mode: str) -> None:
        self.output_mode: str = output_mode
        self.log_file: str = None
        self.levels: list[str] = ["INFO", "WARNING", "ERROR"]

    def set_level(self, *levels: str) -> None:
        """
        Set what level of log will be output.

        Args:
            levels: "INFO" represents running information, "WARNING" represents running warnings, and "ERROR" represents running errors. The default is all.
        """
        temp_levels: list[str] = []
        for level in levels:
            temp_levels.append(level)
        self.levels = temp_levels

    def set_file(self, log_file: str) -> None:
        """
        Set log output file.

        Args:
             log_file: the log file
        """
        self.log_file = log_file

    def log_print(self, level: str, message: str) -> None:
        """
        Output log.

        Args:
            level: log level
            message: log content
        """
        now_time: str = str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        if self.output_mode == "sys":
            if level in self.levels:
                if level == "INFO":
                    print(f"INFO: {message}")
                elif level == "WARNING":
                    print("\033[33m" + f"[{now_time}] WARNING: {message}" + "\033[0m")
                else:
                    print("\033[31m" + f"[{now_time}] ERROR: {message}" + "\033[0m")
        else:
            if self.log_file is None:
                raise am.FileMissError("Require log to be written to file but no log file specified!")
            else:
                if level in self.levels:
                    if level == "INFO":
                        with open(self.log_file, "a") as f:
                            f.write(f"INFO: {message}\n")
                    elif level == "WARNING":
                        with open(self.log_file, "a") as f:
                            f.write(f"[{now_time}] WARNING: {message}\n")
                    else:
                        with open(self.log_file, "a") as f:
                            f.write(f"[{now_time}] ERROR: {message}\n")


class Logger:
    """
    Log class.
    """
    def __init__(self) -> None:
        self.config: list[Handler] = []

    def add_config(self, handler: Handler) -> None:
        """
        Adds the specified handler to this logger.
        """
        self.config.append(handler)

    def info(self, message: str) -> None:
        """
        Logs a message with level INFO.

        Args:
            message: log information
        """
        for handler in self.config:
            handler.log_print("INFO", message)

    def warning(self, message: str) -> None:
        """
        Logs a message with level WARNING.

        Args:
            message: log information
        """
        for handler in self.config:
            handler.log_print("WARNING", message)

    def error(self, message: str) -> None:
        """
        Logs a message with level ERROR.

        Args:
            message: log information
        """
        for handler in self.config:
            handler.log_print("ERROR", message)
