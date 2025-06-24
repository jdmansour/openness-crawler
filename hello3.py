import asyncio
import json
from typing import TYPE_CHECKING

import dotenv
from crawl4ai import (AsyncWebCrawler, BrowserConfig, CacheMode,
                      CrawlerRunConfig, CrawlResult, LLMConfig,
                      LLMExtractionStrategy)
from crawl4ai.processors.pdf import (PDFContentScrapingStrategy,
                                     PDFCrawlerStrategy)
from googleapiclient.discovery import build
from pydantic import BaseModel, TypeAdapter


def google_search(query):
    api_key = dotenv.get_key(".env", "GOOGLE_API_KEY")
    cse_id = dotenv.get_key(".env", "GOOGLE_CSE_ID")
    service = build("customsearch", "v1", developerKey=api_key)
    res = service.cse().list(q=query, cx=cse_id, num=10).execute()

    if len(res.get('items', [])) == 0:
        print(f"No results found for query: {query}")
        print("response:", res)

    return [item['link'] for item in res.get('items', [])]


class LMSResult(BaseModel):
    reasoning: str
    software_usage_found: bool

async def main():
    # site = "www.uni-kassel.de"
    # einrichtung = "Universität Kassel"
    # software = "Moodle"

    unis = [
        # ("www.uni-kassel.de", "Universität Kassel"),
        # ("www.hfm-wuerzburg.de", "Hochschule für Musik Würzburg"),
        # ("www.fh-aachen.de", "FH Aachen"),
        # ("www.rwth-aachen.de", "RWTH Aachen"),
        # ("www.hs-aalen.de", "Hochschule Aalen"),
        ("www.uni-goettingen.de", "Universität Göttingen"),
    ]

    for site, einrichtung in unis:
        for software in ["Moodle", "Ilias"]: # , "OpenOLAT", "Canvas", "Stud.IP"]:
            results = google_search(f"site:{site} {software}")

            total_result = None
            for url in results[:5]:
                print(url)
                result = await scrape_url(url, software=software, einrichtung=einrichtung)
                #print(result)
                if result.software_usage_found:
                    print(f"{software} usage found in {url}: {result.reasoning}")
                    total_result = result
                    break

                print(f"No {software} usage found in {url}: {result.reasoning}")

            if total_result is None:
                total_result = LMSResult(reasoning="(No usage found in any document)", software_usage_found=False)
            print("Final result:", total_result)


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
        llm_config = LLMConfig(provider="openai/llama-3.3-70b-instruct",
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
        cache_mode=CacheMode.DISABLED
    )

    # 3. Create a browser config if needed
    browser_cfg = BrowserConfig(headless=True)


    # pdf_url = "https://hfm-wuerzburg.de/admin/QM/pdf/HfM_Wegweiser_fuer_Lehrende_Stand_21.08.2024.docx.pdf"

    # crawler_strategy = PDFCrawlerStrategy()
    crawler_strategy = PDFCrawlerStrategy() if is_pdf else None

    async with AsyncWebCrawler(crawler_strategy=crawler_strategy) as crawler:
        # 4. Let's say we want to crawl a single page
        result = await crawler.arun(
            url=url,
            config=crawl_config
        )
        if TYPE_CHECKING:
            assert isinstance(result, CrawlResult)

        if not result.extracted_content:
            print("⚠️ No content extracted")
            return LMSResult(reasoning="(No content extracted)", software_usage_found=False)
        
        try:
            data = TypeAdapter(list[LMSResult]).validate_json(result.extracted_content)
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON decoding error: {e}")
            print("Extracted content:", result.extracted_content)
            return LMSResult(reasoning="(JSON decoding error)", software_usage_found=False)
        except Exception as e:
            print(f"⚠️ Error validating JSON: {e}")
            print("Extracted content:", result.extracted_content)
            return LMSResult(reasoning="(Error validating JSON)", software_usage_found=False)

        # if there is a positive result in any chunk, then we have a positive result
        for item in data:
            if item.software_usage_found:
                print(f"{software} usage found: {item.reasoning}")
                return item

        if data:
            return data[0]  # return the first item if no positive result found
        else:
            print("⚠️ No results found")
            return LMSResult(reasoning="(No results found)", software_usage_found=False)



if __name__ == "__main__":
    # main()
    asyncio.run(main())
