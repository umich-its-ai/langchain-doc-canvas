from dataclasses import dataclass
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod

from langchain.docstore.document import Document
from canvas_langchain.utils.logging import Logger

from canvasapi.discussion_topic import DiscussionTopic
from canvasapi.assignment import Assignment
from canvasapi.file import File
from canvasapi.module import ModuleItem
from canvasapi.page import Page
from canvas_langchain.client import CanvasClient


@dataclass
class BaseSectionLoaderVars:
    canvas_client: CanvasClient
    indexed_items: set
    logger: Logger


class BaseSectionLoader(ABC):
    """Abstract base class for loading sections of a Canvas course"""
    def __init__(self, baseSectionVars: BaseSectionLoaderVars):
        self.canvas_client = baseSectionVars.canvas_client
        self.indexed_items = baseSectionVars.indexed_items
        self.logger = baseSectionVars.logger

    @abstractmethod
    def load_section(self) -> list[Document]:
        """Load section data and return a list of Document objects"""
        pass

    def _load_item(self, item: File | Assignment | Page | DiscussionTopic | ModuleItem) -> list[Document]:
        """Load a single section item and return a list of Document objects"""
        raise NotImplementedError("This optional method should be implemented in subclass")

    def load_from_module(self, item: File | Assignment | Page, 
                         module_name: str | None, 
                         locked: bool | None, 
                         formatted_datetime: str | None) -> list[Document]:
        """Load a section item from a module"""
        raise NotImplementedError("This optional method should be implemented in subclass")

    def parse_html(self, html: str) -> str:
        """Extracts text and a list of embedded urls from HTML content"""
        bs = BeautifulSoup(html, 'lxml')
        doc_text = bs.text.strip()
        return doc_text
    
    def process_data(self, metadata: dict) -> list[Document]:
        """Process metadata on a single 'page'"""
        document_arr = []    
        if metadata['content']:
            document_arr.append(Document(
                page_content=metadata['content'],
                metadata=metadata['data']
            ))
        return document_arr
    
    def _remove_null_bytes(self, metadata_item: str | dict) -> str | dict:
        """Recursively remove NUL bytes from string or dict of strings"""
        if isinstance(metadata_item, str):
            return metadata_item.replace("\x00", '')
        elif isinstance(metadata_item, dict):
            return {key: self._remove_null_bytes(value) for key, value in metadata_item.items()}
        return metadata_item

