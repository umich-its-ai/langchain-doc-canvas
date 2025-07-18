from urllib.parse import urljoin
from canvasapi.exceptions import CanvasException
from langchain.docstore.document import Document

from canvas_langchain.base import BaseSectionLoader, BaseSectionLoaderVars
from canvasapi.page import Page

class PageLoader(BaseSectionLoader):
    def __init__(self, baseSectionVars: BaseSectionLoaderVars, course_api: str):
        super().__init__(baseSectionVars)
        self.course_api = course_api

    def load_section(self) -> list[Document]:
        self.logger.logStatement(message='Loading pages...\n', level="INFO")
        page_documents = []

        try:
            pages = self.canvas_client_extractor.get_pages()
            for page in pages:
                page_documents.extend(self._load_item(page))

        except CanvasException:
            self.logger.logStatement(message=f"Canvas exception loading pages", level="WARNING")
        
        return page_documents

    def _load_item(self, page: Page) -> list[Document]:
        """Loads and formats a single page and its embedded URL(s) content """
        if not page.locked_for_user and page.body and f"Page:{page.page_id}" not in self.indexed_items:
            self.logger.logStatement(message=f"Loading page: {page.title}", level="DEBUG")
            self.indexed_items.add(f"Page:{page.page_id}")                      

            page_body = self.parse_html(html=page.body)
           
            page_url = urljoin(self.course_api, f'pages/{page.url}')
            metadata={"content": page_body,
                    "data": {"filename": page.title,
                             "source": page_url,
                             "kind": "page",
                             "id": page.page_id}
                    }
            return self.process_data(metadata=metadata)
        return []

    def load_from_module(self, item: Page) -> list[Document]:
        """Loads page from module item"""
        self.logger.logStatement(message=f"Loading page {item.page_url} from module.", 
                                    level="DEBUG")
        page = self.canvas_client_extractor.get_page(url=item.page_url)
        return self._load_item(page)
