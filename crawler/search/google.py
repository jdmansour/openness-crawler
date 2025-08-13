
from cache_results import cache_results
from record_results import record_results
import dotenv
import logging
from googleapiclient.discovery import build
log = logging.getLogger(__name__)


@record_results
@cache_results  # (dummy_on_miss=[])
def google_search(query: str, skip_cache=False) -> list[str]:
    api_key = dotenv.get_key(".env", "GOOGLE_API_KEY")
    cse_id = dotenv.get_key(".env", "GOOGLE_CSE_ID")
    if not api_key or not cse_id:
        log.error("Missing GOOGLE_API_KEY or GOOGLE_CSE_ID in .env file")
        return []
    service = build("customsearch", "v1", developerKey=api_key)
    res = service.cse().list(q=query, cx=cse_id, num=10).execute()

    if len(res.get('items', [])) == 0:
        log.warning(f"No results found for query: {query}")
        log.warning("response: %s", res)

    return [item['link'] for item in res.get('items', [])]