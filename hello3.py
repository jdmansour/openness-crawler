import asyncio
import csv
import json
import logging
import os
import re
from typing import TYPE_CHECKING, Literal

import dotenv
from crawl4ai import (AsyncWebCrawler, CacheMode,
                      CrawlerRunConfig, CrawlResult, LLMConfig,
                      LLMExtractionStrategy)
from crawl4ai.processors.pdf import (PDFContentScrapingStrategy,
                                     PDFCrawlerStrategy)
from googleapiclient.discovery import build
from pydantic import BaseModel, TypeAdapter

from cache_results import cache_results
from record_results import record_results
from utils import parse_json_objects


import litellm
litellm._turn_on_debug()

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)
# hide litellm and httpx logging
logging.getLogger("LiteLLM").setLevel(logging.DEBUG)
# logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)
# logging.getLogger('cache_results').setLevel(logging.DEBUG)



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

# TODO: in dem ergebnis das Dokument (URL) mitgeben
# TODO: auch die zwischenergebnisse irgendwo hin loggen


class LMSResult(BaseModel):
    reasoning: str
    software_usage_found: bool
    error: Literal[False] = False

class ErrorBlock(BaseModel):
    index: int
    error: Literal[True] = True
    tags: list[str]
    content: str
    # {
    #     "index": 11,
    #     "error": true,
    #     "tags": [
    #         "error"
    #     ],
    #     "content": "litellm.RateLimitError: RateLimitError: OpenAIException - API rate limit exceeded"
    # },

async def main():

    # url = "https://www.ub.tu-clausthal.de/en/publishing-open-access/publish-open-access/open-access-policy-and-strategy-of-the-technischen-universitaet-clausthal"
    # software = "OpenOLAT" 
    # uni = "Technische Universität Clausthal"

    # result = await scrape_url(url, software=software, einrichtung=uni, skip_cache=True)
    # log.info("Result: %s", result)

    # return

    # site = "www.uni-kassel.de"
    # einrichtung = "Universität Kassel"
    # software = "Moodle"

    filename = "../einrichtungen/data/hochschulen.csv"
    if not os.path.exists(filename):
        log.error(f"File {filename} does not exist.")
        return

    output_file = "results.jsonlines"

    combos_done = set()
    if os.path.exists(output_file):
        objs = parse_json_objects(output_file)
        for obj in objs:
            einrichtung = obj.get("einrichtung", "")
            software = obj.get("software", "")
            if einrichtung and software:
                combos_done.add((einrichtung, software))

    # return
    # Hochschulname,Land,Hochschultyp,Trägerschaft,Promotionsrecht,Gründungsjahr(e),Anzahl Studierende,Mitgliedschaft HRK,website
    # Medical School Berlin – Hochschule für Gesundheit und Medizin (MSB),BE,Fachhochschule / HAW,privat,nein,2012,2488,nein,http://www.medicalschool-berlin.de/
    # Katholische Hochschule für Sozialwesen Berlin,BE,Fachhochschule / HAW,kirchlich,nein,1991,1235,"ja (Gruppe der Hochschulen für Angewandte Wissenschaften, Fachhochschulen)",https://www.khsb-berlin.de/
    # International Psychoanalytic University Berlin,BE,Universität,privat,nein,2009,894,nein,https://www.ipu-berlin.de/
    # IB Hochschule für Gesundheit und Soziales,BE,Fachhochschule / HAW,privat,nein,2006,776,nein,https://www.ib-hochschule.de/

    # parse csv
    # get columns website and Hochschulname
    # remove http(s):// and www. from website
    unis = []
    with open(filename, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=",")
        for row in reader:
            # Universität
            if row.get("Hochschultyp", "").strip() != "Universität":
                continue
            # if "Hannover" not in row.get("Hochschulname", ""):
            #     # if not "Göttingen" in row.get("Hochschulname", ""):
            #     continue

            website = row["website"].strip()
            if not website:
                log.warning(f"Skipping row with empty website: {row}")
                continue
            # remove http(s):// and www.
            website = re.sub(r"^https?://(www\.)?", "", website)
            # remove trailing slash
            website = website.rstrip("/")
            # add to list
            unis.append((website, row["Hochschulname"]))

    log.info(f"Found {len(unis)} universities in {filename}")

    # unis = [
    #     ("uni-kassel.de", "Universität Kassel"),
    #     ("hfm-wuerzburg.de", "Hochschule für Musik Würzburg"),
    #     ("fh-aachen.de", "FH Aachen"),
    #     ("rwth-aachen.de", "RWTH Aachen"),
    #     ("hs-aalen.de", "Hochschule Aalen"),
    #     ("uni-goettingen.de", "Universität Göttingen"),
    # ]

    with open(output_file, "a", encoding="utf-8") as f:
        for site, einrichtung in unis:
            # , "OpenOLAT", "Canvas", "Stud.IP"]:
            for software in ["Moodle", "Ilias", "OpenOLAT"]:
                if (einrichtung, software) in combos_done:
                    log.info(f"Skipping {einrichtung} - {software}, already done")
                    continue

                # Step 1: Google search
                results = google_search(
                    f"site:{site} {software}", skip_cache=False)

                combined_verdict = False
                scraping_results = []
                # For each result...
                for url in results[:5]:
                    log.debug("Scraping url: %s", url)
                    # Step 2: Scrape the URL and apply LLM
                    result = await scrape_url(url, software=software, einrichtung=einrichtung, skip_cache=True)
                    scraping_results.append(result)
                    # log.debug(result)
                    if result.software_usage_found:
                        log.debug(
                            f"{software} usage found in {url}: {result.reasoning}")
                        combined_verdict = True
                        # exit early
                        break

                    log.debug(
                        f"No {software} usage found in {url}: {result.reasoning}")

                if not combined_verdict:
                    summary = f"Found no evidence of {software} usage in documents"
                else:
                    summary = f"Found evidence of {software} usage in documents"

                combined_inputs = [
                    {'url': url, 'reasoning': r.reasoning}
                    for url, r in zip(results[:5], scraping_results)
                ]

                combined_reasoning = {
                    'summary': summary,
                    'inputs': combined_inputs
                }

                log.info("%s - %s usage: %s", einrichtung,
                         software, combined_verdict)

                item = {
                    "einrichtung": einrichtung,
                    "software": software,
                    "usage_found": combined_verdict,
                    "reasoning": combined_reasoning
                }

                # print as json
                print(json.dumps(item, ensure_ascii=False, indent=2), file=f, flush=True)


@record_results
@cache_results
async def scrape_url(url: str, software: str = "Moodle", einrichtung: str = "HfM Würzburg", skip_cache=False) -> LMSResult:
    log.info(f"Scraping URL: {url} for {software} usage in {einrichtung}")
    is_pdf = False
    if "dumpFile" in url or url.endswith(".pdf"):
        # hack hack hack
        is_pdf = True

    api_key = dotenv.get_key(".env", "LLM_API_KEY")
    base_url = "https://chat-ai.academiccloud.de/v1"

    llm_strategy = LLMExtractionStrategy(
        llm_config=LLMConfig(provider="openai/llama-3.3-70b-instruct",
                             base_url=base_url, api_token=api_key),
        schema=LMSResult.model_json_schema(),
        verbose=True,
        extraction_type="schema",
        instruction=f"Finde heraus ob aus dem Text hervorgeht, dass {software} oder eine auf {software} basierende Software in der Einrichtung {einrichtung} genutzt wird. Antworte mit Wahr oder Falsch und gib eine kurze Begründung.",
        chunk_token_threshold=1000,
        overlap_rate=0.05,
        apply_chunking=True,
        input_format="markdown",   # or "html", "fit_markdown"
        extra_args={"temperature": 0.0, "max_tokens": 800}
    )

    # 2. Build the crawler config
    scraping_strategy = PDFContentScrapingStrategy() if is_pdf else None
    crawl_config = CrawlerRunConfig(
        scraping_strategy=scraping_strategy,  # type: ignore
        extraction_strategy=llm_strategy,
        cache_mode=CacheMode.DISABLED if is_pdf else CacheMode.WRITE_ONLY,
        verbose=True,
        log_console=True,
    )

    # Create a browser config if needed
    # browser_cfg = BrowserConfig(headless=True)

    crawler_strategy = PDFCrawlerStrategy() if is_pdf else None
    
    async with AsyncWebCrawler(crawler_strategy=crawler_strategy) as crawler:  # type: ignore
        # cast(AsyncLogger, crawler.logger).console.file = sys.stderr
        log.info("Scraping URL: %s", url)
        result = await crawler.arun(
            url=url,
            config=crawl_config
        )
        log.info("URL scraped: %s", url)
        if TYPE_CHECKING:
            assert isinstance(result, CrawlResult)

        # log.info("LLM usage: %s", llm_strategy.usages)
        # log.info("LLM usage: %s", llm_strategy.total_usage)
        # llm_strategy.show_usage()

        if not result.extracted_content:
            log.warning("⚠️ No content extracted")
            return LMSResult(reasoning="(No content extracted)", software_usage_found=False)


        log.info("result.error_message: %s", result.error_message)
        log.info("result.extracted_content: %s", result.extracted_content[:1000])

        try:
            data = TypeAdapter(list[LMSResult|ErrorBlock]).validate_json(
                result.extracted_content)
        except json.JSONDecodeError as e:
            log.warning(f"⚠️ JSON decoding error: {e}")
            log.warning("The extracted content might not be valid JSON.")
            log.warning("Extracted content: %s", result.extracted_content)
            raise
            return LMSResult(reasoning="(JSON decoding error)", software_usage_found=False)
        except Exception as e:
            log.warning(f"⚠️ Error validating JSON: {e}")
            log.warning("Extracted content: %s", result.extracted_content)
            raise
            return LMSResult(reasoning="(Error validating JSON)", software_usage_found=False)

        # # combine chunks into a single reasoning
        # chunks = []
        # for item in data:
        #     if isinstance(item, ErrorBlock):
        #         raise RuntimeError(
        #             f"Error in block {item.index}: {item.content}")
            
        #     chunks.append({
        #         "software_usage_found": item.software_usage_found,
        #         "reasoning": item.reasoning
        #     })

        positive: list[str] = []
        for item in data:
            if isinstance(item, ErrorBlock):
                raise RuntimeError(
                    f"Error in block {item.index}: {item.content}")
            if item.software_usage_found:
                positive.append(item.reasoning)

        usage_found = len(positive) > 0
        if usage_found:
            # reasoning = f"URL: {url};"
            reasoning = "; ".join(positive)
        else:
            # reasoning = f"URL: {url};"
            reasoning = "No mention found."

        return LMSResult(reasoning=reasoning, software_usage_found=usage_found)


if __name__ == "__main__":
    # main()
    asyncio.run(main())
