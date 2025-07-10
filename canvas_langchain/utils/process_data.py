"""Utility functions to load and format embedded urls, extract module metadata"""
from datetime import datetime, timezone
from typing import List, Tuple, Dict
from urllib.parse import urlparse
from langchain.docstore.document import Document
from canvas_langchain.sections.mivideo import MiVideoLoader
from canvas_langchain.utils.logging import Logger
# compatible with isolated and integrated testing
try:
    from django.conf import settings
except ImportError as err:
    import settings

def process_data(metadata: Dict, embed_urls: List, mivideo_loader: MiVideoLoader) -> List[Document]:
    """Process metadata and embed_urls on a single 'page'"""
    document_arr = []    
    # Format metadata
    if metadata['content']:
        document_arr.append(Document(
            page_content=metadata['content'],
            metadata=metadata['data']
        ))
    # Load content from embed urls
    document_arr.extend(_load_embed_urls(metadata=metadata, embed_urls=embed_urls, mivideo_loader=mivideo_loader))
    return document_arr


def _load_embed_urls(metadata: Dict, 
                     embed_urls: List, 
                     mivideo_loader: MiVideoLoader) -> List[Document]:
    """Load MiVideo content from embed urls"""
    docs = []
    for url in embed_urls:
        mivideo_loader.logger.logStatement(message=f"Loading embed url {url}", level="DEBUG")
        # extract media_id from each url + load captions
        if (mivideo_media_id := _get_media_id(url, logger=mivideo_loader.logger)):
            docs.extend(mivideo_loader.load(mivideo_id=mivideo_media_id))
        
    for doc in docs:
        doc.metadata.update({'filename': str(metadata['data']['filename']), 
                                'course_context': str(metadata['data']['source'])})
    return docs


def _get_media_id(url: str, logger: Logger) -> str | None:
    """Extracts unique media id from each URL to load mivideo"""
    parsed=urlparse(url)
    if parsed.netloc == getattr(settings, 'MIVIDEO_KAF_HOSTNAME', 'aakaf.mivideo.it.umich.edu'):
        path_parts = parsed.path.split('/')
        try:
            return path_parts[path_parts.index('entryid')+1]
        except ValueError:
            logger.logStatement(message =f"Embed URL for {url} is not MiVideo", level="WARNING")
    return None


def get_module_metadata(unlock_time: str) -> Tuple[bool, str]:
    """Returns if module is locked and corresponding unlock time ("" if unlocked)"""
    locked=False
    formatted_datetime=""
    if unlock_time:
        # get formatted unlock time
        formatted_datetime = datetime.strptime(unlock_time, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        current_time = datetime.now(timezone.utc)
        # determine if locked
        locked = current_time < formatted_datetime

    return locked, formatted_datetime
