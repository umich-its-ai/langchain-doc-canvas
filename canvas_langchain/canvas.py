from typing import Literal
from langchain.document_loaders.base import BaseLoader
from langchain.docstore.document import Document
from pydantic import BaseModel

from canvas_langchain.client import CanvasClient
from canvas_langchain.utils.logging import Logger

# Prevents conflicts with other classes in UMGPT - Happy to refactor as needed
class LogStatement(BaseModel):
    """INFO can be user-facing statements, non-technical and perhaps very high-level"""
    message: str
    level: Literal['INFO', 'DEBUG', 'WARNING']

    def __json__(self):
        return {
            'message': self.message,
            'level': self.level,
        }

class CanvasLoader(BaseLoader):
    def __init__(self,
                 api_url: str,
                 api_key: str,
                 course_id: int, 
                 index_external_urls: bool=False):
        self.logger = Logger()
        self.canvas_client = CanvasClient(api_url, api_key, course_id)
        self.index_external_urls = index_external_urls
        self.course_id = course_id

    def load(self) -> list[Document]:
        """Loads all available content from Canvas course"""
        self.logger.logStatement(message="Starting document loading process. \n", level="INFO")
        docs = []
        try:
            available_tabs = self.canvas_client.get_available_tabs()
            loaders = self.canvas_client.get_loaders(index_external_urls=self.index_external_urls, 
                                                     logger=self.logger)

            for tab_name in available_tabs:
                if tab_name in loaders:
                    docs.extend(loaders[tab_name].load_section())

        except Exception as err:
                self.logger.logStatement(message=f"Error loading Canvas materials {err}", level="WARNING")
        self.logger.logStatement(message="Canvas course processing finished.", level="INFO")
        return docs


    def get_details(self, level='INFO') -> list:
        if level == 'INFO':
            return self.logger._filtered_statements_by_level(level=level)
        return self.logger.progress, self.logger.errors
