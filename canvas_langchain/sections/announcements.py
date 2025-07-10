from datetime import date
from typing import List
from canvasapi.exceptions import CanvasException
from langchain.docstore.document import Document
from canvas_langchain.base import BaseSectionLoader

class AnnouncementLoader(BaseSectionLoader):
    def load(self) -> List[Document]:
        """Load all announcements for a Canvas course"""
        self.logger.logStatement(message='Loading announcements...\n', level="INFO")

        announcement_documents = []
        try:
            announcements = self.canvas.get_announcements(context_codes=[self.course],
                                                            start_date="2016-01-01",
                                                            end_date=date.today().isoformat())

            for announcement in announcements:
                self.logger.logStatement(message=f"Loading announcement: {announcement.title}", level="DEBUG")
                announcement_text = self.parse_html(html=announcement.message)
                
                metadata={"content": announcement_text,
                        "data": {"filename": announcement.title,
                                "source": announcement.html_url,
                                "kind": "announcement",
                                "id": announcement.id}
                        }
                
                formatted_data = self.process_data(metadata=metadata)
                                                                                                                    
                announcement_documents.extend(formatted_data)

        except CanvasException as error:
            self.logger.logStatement(message=f"Canvas exception loading announcements {error}",
                                     level="WARNING")

        return announcement_documents
