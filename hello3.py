import asyncio
import json
import logging
import os
import sys
import time
from typing import TYPE_CHECKING, cast

import dotenv
from crawl4ai import (AsyncWebCrawler, BrowserConfig, CacheMode,
                      CrawlerRunConfig, CrawlResult, LLMConfig,
                      LLMExtractionStrategy)
from crawl4ai import AsyncLogger
from crawl4ai.processors.pdf import (PDFContentScrapingStrategy,
                                     PDFCrawlerStrategy)
from googleapiclient.discovery import build
from pydantic import BaseModel, TypeAdapter

from cache_results import cache_results

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
# hide litellm and httpx logging
logging.getLogger("LiteLLM").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)

logging.getLogger('cache_results').setLevel(logging.DEBUG)

def record_results(func):
    """
    Decorator to record the results of a function call.
    For a function like `google_search`, the results are of the form:
    {
        "cache_hit": false,
        "args": {
            "query": "site:example.com moodle"
        },
        "return": [
            "https://example.com/moodle",
            "https://example.com/moodle2"
        ]
    }
    For each run of the program, a new file is created:
    `results/<function_name>_<timestamp>.json`
    """
    # dummy value for cache hit for now
    #cache_hit = False

    # store the invocation time in the decorator object, if not set
    # we use this to create a unique time for each run
    if not hasattr(record_results, 'init_time'):
        record_results.init_time = time.strftime("%Y%m%d_%H%M%S")
    results_dir = "results"
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)

    def wrapper(*args, **kwargs):
        #nonlocal cache_hit
        # call the function
        kwargs['cache_return_info'] = True
        result, cache_hit = func(*args, **kwargs)

        # create a unique filename based on the function name and invocation time
        filename = f"{results_dir}/{func.__name__}_{record_results.init_time}.json"
        
        # prepare the result data
        result_data = {
            "cache_hit": cache_hit,
            "args": {k: v for k, v in zip(func.__code__.co_varnames, args)},
            "return": result
        }

        # write the result to a file
        with open(filename, 'a', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
            f.write("\n")

        return result
    return wrapper


@record_results
@cache_results(dummy_on_miss=[])
def google_search(query):
    api_key = dotenv.get_key(".env", "GOOGLE_API_KEY")
    cse_id = dotenv.get_key(".env", "GOOGLE_CSE_ID")
    service = build("customsearch", "v1", developerKey=api_key)
    res = service.cse().list(q=query, cx=cse_id, num=10).execute()

    if len(res.get('items', [])) == 0:
        log.warning(f"No results found for query: {query}")
        log.warning("response:", res)

    return [item['link'] for item in res.get('items', [])]

# TODO: in dem ergebnis das Dokument (URL) mitgeben
# TODO: auch die zwischenergebnisse irgendwo hin loggen

class LMSResult(BaseModel):
    reasoning: str
    software_usage_found: bool


async def main():
    # site = "www.uni-kassel.de"
    # einrichtung = "Universität Kassel"
    # software = "Moodle"

    filename = "../einrichtungen/data/hochschulen.csv"
    if not os.path.exists(filename):
        log.error(f"File {filename} does not exist.")
        return
    
    output_file = "results.jsonlines"
    
    # Hochschulname,Land,Hochschultyp,Trägerschaft,Promotionsrecht,Gründungsjahr(e),Anzahl Studierende,Mitgliedschaft HRK,website
    # Medical School Berlin – Hochschule für Gesundheit und Medizin (MSB),BE,Fachhochschule / HAW,privat,nein,2012,2488,nein,http://www.medicalschool-berlin.de/
    # Katholische Hochschule für Sozialwesen Berlin,BE,Fachhochschule / HAW,kirchlich,nein,1991,1235,"ja (Gruppe der Hochschulen für Angewandte Wissenschaften, Fachhochschulen)",https://www.khsb-berlin.de/
    # International Psychoanalytic University Berlin,BE,Universität,privat,nein,2009,894,nein,https://www.ipu-berlin.de/
    # IB Hochschule für Gesundheit und Soziales,BE,Fachhochschule / HAW,privat,nein,2006,776,nein,https://www.ib-hochschule.de/    

    # parse csv
    # get columns website and Hochschulname
    # remove http(s):// and www. from website
    import csv
    import re
    unis = []
    with open(filename, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=",")
        for row in reader:
            # Universität
            if row.get("Hochschultyp", "").strip() != "Universität":
                # print(f"Skipping row with Hochschultyp {row.get('Hochschultyp', '')}: {row}")
                continue
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
                results = google_search(f"site:{site} {software}", skip_cache=False)

                total_result = None
                for url in results[:5]:
                    log.debug("Scraping url: %s", url)
                    result = await scrape_url(url, software=software, einrichtung=einrichtung, skip_cache=True)
                    log.debug(result)
                    if result.software_usage_found:
                        log.debug(f"{software} usage found in {url}: {result.reasoning}")
                        total_result = result
                        break

                    log.debug(f"No {software} usage found in {url}: {result.reasoning}")

                if total_result is None:
                    total_result = LMSResult(
                        reasoning="(No usage found in any document)", software_usage_found=False)
                # print("Final result:", total_result)
                # print(f"{einrichtung} - {software} usage:",
                #       total_result.software_usage_found)
                log.info("%s - %s usage: %s", einrichtung, software, total_result.software_usage_found)
                
                item = {
                    "einrichtung": einrichtung,
                    "software": software,
                    "usage_found": total_result.software_usage_found,
                    "reasoning": total_result.reasoning
                }
                # print as json
                print(json.dumps(item, ensure_ascii=False, indent=2), file=f, flush=True)


@record_results
@cache_results
async def scrape_url(url: str, software: str = "Moodle", einrichtung: str = "HfM Würzburg") -> LMSResult:
    is_pdf = False
    if "dumpFile" in url or url.endswith(".pdf"):
        # hack hack hack
        is_pdf = True

    api_key = dotenv.get_key(".env", "LLM_API_KEY")
    base_url = "https://chat-ai.academiccloud.de/v1"
    model = "llama-3.1-sauerkrautlm-70b-instruct"
    # 1. Define the LLM extraction strategy
    llm_strategy = LLMExtractionStrategy(
        llm_config=LLMConfig(provider="openai/llama-3.3-70b-instruct",
                             base_url=base_url, api_token=api_key),
        schema=LMSResult.model_json_schema(),
        extraction_type="schema",
        instruction=f"Finde heraus ob aus dem Text hervorgeht, dass {software} oder eine auf {software} basierende Software in der Einrichtung {einrichtung} genutzt wird. Antworte mit Wahr oder Falsch und gib eine kurze Begründung.",
        chunk_token_threshold=2000,
        overlap_rate=0.1,
        apply_chunking=True,
        input_format="markdown",   # or "html", "fit_markdown"
        extra_args={"temperature": 0.0, "max_tokens": 800}
    )

    # 2. Build the crawler config
    scraping_strategy = PDFContentScrapingStrategy() if is_pdf else None
    crawl_config = CrawlerRunConfig(
        # scraping_strategy=PDFContentScrapingStrategy(),
        scraping_strategy=scraping_strategy,
        extraction_strategy=llm_strategy,
        cache_mode=CacheMode.DISABLED if is_pdf else CacheMode.ENABLED,
    )

    # 3. Create a browser config if needed
    browser_cfg = BrowserConfig(headless=True)

    # pdf_url = "https://hfm-wuerzburg.de/admin/QM/pdf/HfM_Wegweiser_fuer_Lehrende_Stand_21.08.2024.docx.pdf"

    # crawler_strategy = PDFCrawlerStrategy()
    crawler_strategy = PDFCrawlerStrategy() if is_pdf else None

    async with AsyncWebCrawler(crawler_strategy=crawler_strategy) as crawler:
        # cast(AsyncLogger, crawler.logger).console.file = sys.stderr

        # 4. Let's say we want to crawl a single page
        result = await crawler.arun(
            url=url,
            config=crawl_config
        )
        if TYPE_CHECKING:
            assert isinstance(result, CrawlResult)

        if not result.extracted_content:
            log.warning("⚠️ No content extracted")
            return LMSResult(reasoning="(No content extracted)", software_usage_found=False)

        try:
            data = TypeAdapter(list[LMSResult]).validate_json(
                result.extracted_content)
        except json.JSONDecodeError as e:
            log.warning(f"⚠️ JSON decoding error: {e}")
            log.warning("Extracted content:", result.extracted_content)
            return LMSResult(reasoning="(JSON decoding error)", software_usage_found=False)
        except Exception as e:
            log.warning(f"⚠️ Error validating JSON: {e}")
            log.warning("Extracted content:", result.extracted_content)
            return LMSResult(reasoning="(Error validating JSON)", software_usage_found=False)

        # if there is a positive result in any chunk, then we have a positive result
        for item in data:
            if item.software_usage_found:
                log.warning(f"{software} usage found: {item.reasoning}")
                return item

        if data:
            return data[0]  # return the first item if no positive result found
        else:
            log.warning("⚠️ No results found")
            return LMSResult(reasoning="(No results found)", software_usage_found=False)


if __name__ == "__main__":
    # main()
    asyncio.run(main())
