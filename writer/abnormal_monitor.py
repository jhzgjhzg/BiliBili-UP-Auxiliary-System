"""
Bili-UAS.writer.abnormal_monitor

All exception classes in the project.
"""


class ParameterInputError(Exception):
    """
    Raise when parameter input error or no parameter input.
    """
    def __init__(self, message: str) -> None:
        self.message = message


class FileMissError(Exception):
    """
    Raise when a file is missing or not specified.
    """
    def __init__(self, message: str) -> None:
        self.message = message
