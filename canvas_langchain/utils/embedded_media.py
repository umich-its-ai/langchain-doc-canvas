"""Utility functions to extract text and embedded URLs from HTML content in Canvas"""
from bs4 import BeautifulSoup
from urllib.parse import parse_qs, urlparse
from canvasapi.exceptions import CanvasException
# compatible with isolated and integrated testing
try:
    from django.conf import settings
except ImportError as err:
    import settings

def parse_html_for_text_and_urls(canvas, course, html, logger):
    """Extracts text and a list of embedded URLs from HTML content"""
    bs = BeautifulSoup(html, 'lxml')
    doc_text = bs.text.strip()

    # Urls will be embedded in iframe tags
    embed_urls = []
    iframes = bs.find_all('iframe')
    for iframe in iframes:
        iframe_src_url = iframe.get('src')

        # In LTI 1.3, embed URLS protected by UUID - Must extract 
        if (embed_url := _get_embed_url_via_uuid(canvas, course, iframe_src_url, logger)):
            embed_urls.append(embed_url)
        
        # In LTI 1.1 embed URLS are linked directly
        elif (embed_url := _get_embed_url_direct(iframe_src_url)):
            embed_urls.append(embed_url)

    return doc_text, embed_urls


def _get_embed_url_via_uuid(canvas, course, url: str, logger):
    """Extracts embed url from Canvas iframe URL via UUID"""    
    # Extract UUID (unique identifier) - tagged with 'resource_link_lookup_uuid'
    uuid = parse_qs(urlparse(url).query).get('resource_link_lookup_uuid',[None]).pop()
    url = None
    # Get embed URL via UUID
    if (uuid):
        endpoint = f'courses/{course.id}/lti_resource_links/lookup_uuid:{uuid}'
        try: 
            response = canvas._Canvas__requester.request('GET', endpoint)
            url = response.json().get('url')
        except CanvasException:
            logger.logStatement(message=f"Canvas exception loading UUID for {url}", level="WARNING")

    return url


def _get_embed_url_direct(url: str) -> str | None:
    """Extracts embedded resource URL from Canvas (LTI 1.1 styling)"""
    parsed_url = urlparse(url)
    # Verify url matches Canvas LTI 1.1 format:
    # `https://<canvas_ui_hostname>/courses/<course_id>/external_tools/retrieve?url=<embed_url>`
    canvas_ui_hostname = getattr(settings, 'CANVAS_UI_HOSTNAME', 'umich.instructure.com')

    netloc_matches = parsed_url.netloc.lower() == canvas_ui_hostname
    path_starts_correctly = parsed_url.path.lower().startswith('/courses/')
    path_ends_correctly = parsed_url.path.lower().endswith('/external_tools/retrieve')

    if netloc_matches and path_starts_correctly and path_ends_correctly:
        return parse_qs(parsed_url.query).get('url', [None]).pop()
    return None
