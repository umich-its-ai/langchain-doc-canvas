from datetime import date
from typing import List
from canvasapi.exceptions import CanvasException
from canvasapi.paginated_list import PaginatedList
from langchain.docstore.document import Document
from canvas_langchain.base import BaseSectionLoader, BaseSectionLoaderVars

class AnnouncementLoader(BaseSectionLoader):
    def __init__(self, baseSectionVars: BaseSectionLoaderVars):
        super().__init__(baseSectionVars)

    def load_section(self) -> List[Document]:
        """Load all announcements for a Canvas course"""
        self.logger.logStatement(message='Loading announcements...\n', level="INFO")

        announcement_documents = []
        try:
            announcements = self.canvas.get_announcements(context_codes=[self.course],
                                                            start_date="2016-01-01",
                                                            end_date=date.today().isoformat())

            for announcement in announcements:
                announcement_documents.extend(self._load_one(announcement=announcement))

        except CanvasException as error:
            self.logger.logStatement(message=f"Canvas exception loading announcements {error}",
                                     level="WARNING")

        return announcement_documents

    def _load_item(self, announcement: PaginatedList) -> List[Document]:
        """Loads a single announcement"""
        self.logger.logStatement(message=f"Loading announcement: {announcement.title}", level="DEBUG")
        
        announcement_text = self.parse_html(html=announcement.message)
        metadata={"content": announcement_text,
        "data": {"filename": announcement.title,
                 "source": announcement.html_url,
                 "kind": "announcement",
                 "id": announcement.id}
        }
        return self.process_data(metadata=metadata)
