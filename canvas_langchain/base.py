from abc import ABC, abstractmethod
from dataclasses import dataclass

from canvas_langchain.client_getters import CanvasClientGetters
from canvas_langchain.sections.mivideo import MiVideoLoader
from canvas_langchain.utils.embedded_media import parse_html_for_text_and_urls
from canvas_langchain.utils.logging import Logger
from canvas_langchain.utils.process_data import load_embed_urls
from canvasapi.assignment import Assignment
from canvasapi.discussion_topic import DiscussionTopic
from canvasapi.file import File
from canvasapi.module import ModuleItem
from canvasapi.page import Page
from langchain.docstore.document import Document


@dataclass
class BaseSectionLoaderVars:
    canvas_client_extractor: CanvasClientGetters
    indexed_items: set
    logger: Logger
    mivideo_loader: MiVideoLoader
    load_mivideo: bool


class BaseSectionLoader(ABC):
    """Abstract base class for loading sections of a Canvas course"""

    def __init__(self, baseSectionVars: BaseSectionLoaderVars):
        self.canvas_client_extractor = baseSectionVars.canvas_client_extractor
        self.indexed_items = baseSectionVars.indexed_items
        self.logger = baseSectionVars.logger
        self.mivideo_loader = baseSectionVars.mivideo_loader
        self.load_mivideo = baseSectionVars.load_mivideo

    @abstractmethod
    def load_section(self) -> list[Document]:
        """Load section data and return a list of Document objects"""
        pass

    def _load_item(
        self,
        item: File | Assignment | Page | DiscussionTopic | ModuleItem,
        description: str | None,
    ) -> list[Document]:
        """Load a single section item and return a list of Document objects"""
        raise NotImplementedError(
            "This optional method should be implemented in subclass"
        )

    def load_from_module(
        self,
        item: File | Assignment | Page,
        module_name: str | None = None,
        locked: bool | None = None,
        formatted_datetime: str | None = None,
    ) -> list[Document]:
        """Load a section item from a module"""
        raise NotImplementedError(
            "This optional method should be implemented in subclass"
        )

    def parse_html(self, html: str) -> str:
        """Extracts text and a list of embedded urls from HTML content"""
        return parse_html_for_text_and_urls(
            canvas_client_extractor=self.canvas_client_extractor,
            html=html,
            logger=self.logger,
            load_mivideo=self.load_mivideo,
        )

    def process_data(
        self, metadata: dict, embed_urls: list[str] = []
    ) -> list[Document]:
        """Process metadata on a single 'page'"""
        document_arr = []
        if metadata["content"]:
            document_arr.append(
                Document(
                    page_content=self._remove_null_bytes(metadata["content"]),
                    metadata=self._remove_null_bytes(metadata["data"]),
                )
            )
        if embed_urls and self.load_mivideo:
            document_arr.extend(
                load_embed_urls(
                    metadata=metadata,
                    embed_urls=embed_urls,
                    mivideo_loader=self.mivideo_loader,
                )
            )
        return document_arr

    def _remove_null_bytes(self, metadata_item: str | dict) -> str | dict:
        """Recursively remove NUL bytes from string or dict of strings"""
        if isinstance(metadata_item, str):
            return metadata_item.replace("\x00", "")
        elif isinstance(metadata_item, dict):
            return {
                key: self._remove_null_bytes(value)
                for key, value in metadata_item.items()
            }
        return metadata_item
