from typing import List, Dict
from dataclasses import dataclass
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod

from canvasapi import Canvas
from canvasapi.course import Course
from langchain.docstore.document import Document
from canvas_langchain.utils.logging import Logger

@dataclass
class BaseSectionLoaderVars:
    canvas : Canvas
    course: Course
    indexed_items: set
    logger: Logger


class BaseSectionLoader(ABC):
    """Abstract base class for loading sections of a Canvas course"""
    def __init__(self, baseSectionVars: BaseSectionLoaderVars):
        self.canvas = baseSectionVars.canvas
        self.course = baseSectionVars.course
        self.indexed_items = baseSectionVars.indexed_items
        self.logger = baseSectionVars.logger

    @abstractmethod
    def load_section(self) -> List[Document]:
        """Load section data and return a list of Document objects"""
        pass

    def _load_item(self, item) -> List[Document]:
        """Load a single section item and return a list of Document objects"""
        raise NotImplementedError("This optional method should be implemented in subclass")

    def load_from_module(self, item: any, 
                         module_name: str | None, 
                         locked: bool | None, 
                         formatted_datetime: str | None) -> List[Document]:
        """Load a section item from a module"""
        raise NotImplementedError("This optional method should be implemented in subclass")

    def parse_html(self, html):
        """Extracts text and a list of embedded urls from HTML content"""
        bs = BeautifulSoup(html, 'lxml')
        doc_text = bs.text.strip()
        return doc_text
    
    def process_data(self, metadata: Dict) -> List[Document]:
        """Process metadata on a single 'page'"""
        document_arr = []    
        if metadata['content']:
            document_arr.append(Document(
                page_content=metadata['content'],
                metadata=metadata['data']
            ))
        return document_arr
