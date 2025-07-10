from typing import List
from requests import HTTPError
from langchain.docstore.document import Document
from LangChainKaltura.KalturaCaptionLoader import KalturaCaptionLoader
from LangChainKaltura.MiVideoAPI import MiVideoAPI
# compatible with isolated and integrated testing
try:
    from django.conf import settings
except ImportError as err:
        import settings

class MiVideoLoader():
    def __init__(self, canvas, course, indexed_items, logger):
        self.canvas = canvas
        self.course = course
        self.indexed_items = indexed_items
        self.logger = logger
        self.caption_loader = None
        self.mivideo_api = MiVideoAPI(host=settings.MIVIDEO_API_HOST,
                                      authId=settings.MIVIDEO_API_AUTH_ID,
                                      authSecret=settings.MIVIDEO_API_AUTH_SECRET)
        self.mivideo_authorized = True


    def load(self, mivideo_id: str | None) -> List[Document]:
        """Load MiVideo media captions"""
        mivideo_docuements = []
        self.logger.logStatement(message=f"Loading MiVideo for {mivideo_id}...\n", level="INFO")
        
        if not self.mivideo_authorized:
            self.logger.logStatement(message="MiVideo API prior request unauthorized; skipping caption load", level='INFO')
            return []
        
        try:
            if not self.caption_loader:
                self.caption_loader = self._get_caption_loader()
            
            # Load entire media gallery
            if mivideo_id is None:
                mivideo_docuements = self.caption_loader.load()

            # Load single media post embedded in another Canvas section
            elif f"MiVideo:{mivideo_id}" not in self.indexed_items:
                mivideo_docuements = self.caption_loader.fetchMediaCaption({
                    'id': mivideo_id,
                    'name': 'unidentified embedded media'
                })

            course_url_template = settings.CANVAS_COURSE_URL_TEMPLATE
            for doc in mivideo_docuements:
                # add formatted course source url for this video
                if course_url_template:
                    doc.metadata['course_context'] = course_url_template.format(courseId=self.course.id)

                self.indexed_items.add("MiVideo:"+doc.metadata['media_id'])
       
       # don't attempt to load MiVideo again if user is unauthorized
        except HTTPError as ex:
            self.logger.logStatement(message=f"HTTP {ex.response.status_code} error loading MiVideo captions: {ex}", level="INFO")
            if ex.response.status_code == 401:
                self.mivideo_authorized = False
                self.logger.logStatement(message="MiVideo caption request unauthorized. Skipping subsequent requests.", level="INFO")
        except Exception:
            self.logger.logStatement(message=f"Error loading MiVideo content", level="WARNING")

        return mivideo_docuements
    

    def _get_caption_loader(self) -> KalturaCaptionLoader:
        try: 
            languages = KalturaCaptionLoader.LANGUAGES_DEFAULT
            caption_loader = KalturaCaptionLoader(
                apiClient=self.mivideo_api,
                courseId=str(int(self.course.id)),
                userId=str(int(getattr(settings, 'CANVAS_USER_ID_OVERRIDE_DEV_ONLY', self.canvas.get_current_user().id))),
                languages=languages,
                urlTemplate=getattr(settings, 'MIVIDEO_SOURCE_URL_TEMPLATE'),
                chunkSeconds=int(getattr(settings, 'MIVIDEO_CHUNK_SECONDS', KalturaCaptionLoader.CHUNK_SECONDS_DEFAULT)),
            )
        except Exception:
            self.logger.logStatement(message=f"Error loading Kaltura Caption Loader", level="WARNING")

        return caption_loader
