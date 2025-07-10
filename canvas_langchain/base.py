from typing import List, Dict
from dataclasses import dataclass
from bs4 import BeautifulSoup

from canvasapi import Canvas
from canvasapi.course import Course
from langchain.docstore.document import Document
from canvas_langchain.utils.logging import Logger

@dataclass
class BaseSectionLoaderVars:
    canvas : Canvas
    course: Course
    indexed_items: set
    mivideo_loader: int
    logger: Logger


class BaseSectionLoader:
    """Contains member variables and functions required across all loading classes"""
    def __init__(self, baseSectionVars: BaseSectionLoaderVars):
        self.canvas = baseSectionVars.canvas
        self.course = baseSectionVars.course
        self.indexed_items = baseSectionVars.indexed_items
        self.mivideo_loader = baseSectionVars.mivideo_loader
        self.logger = baseSectionVars.logger


    def parse_html(self, html):
        """Extracts text and a list of embedded urls from HTML content"""
        bs = BeautifulSoup(html, 'lxml')
        doc_text = bs.text.strip()
        # Urls will be embedded in iframe tags
        return doc_text
    
    def process_data(self, metadata: Dict) -> List[Document]:
        """Process metadata on a single 'page'"""
        document_arr = []    
        # Format metadata
        if metadata['content']:
            document_arr.append(Document(
                page_content=metadata['content'],
                metadata=metadata['data']
            ))
        return document_arr
