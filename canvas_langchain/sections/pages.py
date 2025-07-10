from typing import List
from urllib.parse import urljoin
from canvasapi.exceptions import CanvasException
from langchain.docstore.document import Document

from canvas_langchain.base import BaseSectionLoader, BaseSectionLoaderVars
from canvasapi.paginated_list import PaginatedList

class PageLoader(BaseSectionLoader):
    def __init__(self, BaseSectionVars: BaseSectionLoaderVars, course_api):
        super().__init__(BaseSectionVars)
        self.course_api = course_api

    def load_pages(self) -> List[Document]:
        self.logger.logStatement(message='Loading pages...\n', level="INFO")
        page_documents = []

        try:
            pages = self.course.get_pages(published=True,
                                            include=['body'])
            for page in pages:
                page_documents.extend(self.load_page(page))

        except CanvasException:
            self.logger.logStatement(message=f"Canvas exception loading pages", level="WARNING")
        
        return page_documents


    def load_page(self, page: PaginatedList) -> List[Document]:
        """Loads and formats a single page and its embedded URL(s) content """
        page_docs = []
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
            page_docs = self.process_data(metadata=metadata)
        return page_docs
