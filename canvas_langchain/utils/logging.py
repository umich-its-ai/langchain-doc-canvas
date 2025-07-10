from typing import List
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
# Quiet noisy libraries
logging.getLogger("canvasapi").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("LangChainKaltura").setLevel(logging.WARNING)

class Logger():
    def __init__(self):
        self.progress = []
        self.errors = []

    def logStatement(self, message: str, level: str):
        """Log messages and track progress"""
        match level:
            case "INFO":
                logger.info(message)
            case "DEBUG":
                logger.debug(message)
            case "WARNING":
                logger.warning(message)
                self.errors.append({"message": message, "level": level})
        self.progress.append({"message": message, "level": level})


    def _filtered_statements_by_level(self, level: str) -> List:
        """Returns statements corresponding to desired output level"""
        return [statement for statement in self.progress if statement.level == level]
