import asyncio
import json
import os
import time

import dotenv
import pdfplumber
import requests
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.processors.pdf import (PDFContentScrapingStrategy,
                                     PDFCrawlerStrategy)
from googleapiclient.discovery import build
from langchain_openai import ChatOpenAI
from openai import OpenAI
from pydantic import SecretStr

import asyncio

from crawl4ai import BrowserConfig, CacheMode, LLMConfig, LLMExtractionStrategy
from pydantic import BaseModel

def google_search(query):
    api_key = dotenv.get_key(".env", "GOOGLE_API_KEY")
    cse_id = dotenv.get_key(".env", "GOOGLE_CSE_ID")
    service = build("customsearch", "v1", developerKey=api_key)
    res = service.cse().list(q=query, cx=cse_id, num=10).execute()
    print(res)
    print("---")
    #

    for item in res.get('items', []):
        print(json.dumps(item, indent=2))
        break
        #print(item['title'], item['link'])
    print("---")

    return [item['link'] for item in res.get('items', [])]

async def main():
    # results = google_search("site:hfm-wuerzburg.de Moodle")
    # for url in results:
    #     print(url)

    pdf_url = "https://hfm-wuerzburg.de/admin/QM/pdf/HfM_Wegweiser_fuer_Lehrende_Stand_21.08.2024.docx.pdf"

    base_url = "https://chat-ai.academiccloud.de/v1"
    # model = "llama-3.3-70b-instruct"
    # model = 'meta-llama-3.1-8b-instruct'
    model = 'llama-3.1-sauerkrautlm-70b-instruct'
    model = 'deepseek-r1'
    api_key = dotenv.get_key(".env", "LLM_API_KEY")
    assert api_key is not None, "LLM_API_KEY must be set in .env file"
    # llm = ChatOpenAI(base_url=base_url,
    #              model=model,
    #              api_key=SecretStr(api_key))
    
    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )

    # Frage die KI ob aus dem PDF hervorgeht, ob Moodle genutzt wird
    # HIER
    # PDF herunterladen und Text extrahieren
    pdf_path = "temp.pdf"

    if not os.path.exists(pdf_path):
        response = requests.get(pdf_url)
        with open(pdf_path, "wb") as f:
            f.write(response.content)
    with pdfplumber.open(pdf_path) as pdf:
        text = "".join([page.extract_text() or "" for page in pdf.pages])

    prompt = (
        "Geht aus folgendem Text hervor, dass Moodle, oder eine auf Moodle basierende Software genutzt wird? "
        "Antworte mit Ja oder Nein und gib eine kurze Begründung.\n\n"
        f"{text}"
    )
    print("calling LLM:")
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        # max_tokens=200,
        max_completion_tokens=400,
        temperature=0
    )
    print(response.choices[0].message.content)
    # os.remove(pdf_path)


    # # Create crawler with PDF strategy
    # async with AsyncWebCrawler(crawler_strategy=PDFCrawlerStrategy()) as crawler:
    #     print("\n🚀 Starting PDF processing...")
        
    #     start_time = time.perf_counter()
    #     result = await crawler.arun(
    #         pdf_url,
    #         config=CrawlerRunConfig(scraping_strategy=PDFContentScrapingStrategy())
    #     )
    #     duration = time.perf_counter() - start_time
        
    #     print(f"\n✅ Processed PDF in {duration:.2f} seconds")
        
    #     # Show metadata
    #     print("\n📄 PDF Metadata:")
    #     if result.metadata:
    #         for key, value in result.metadata.items():
    #             if key not in ["html", "text", "markdown"] and value:
    #                 print(f"  - {key}: {value}")
    #     else:
    #         print("  No metadata available")
        
    #     # Show sample of content
    #     if result.markdown:
    #         print("\n📝 PDF Content Sample:")
    #         content_sample = result.markdown[:500] + "..." if len(result.markdown) > 500 else result.markdown
    #         print(f"---\n{content_sample}\n---")
    #     else:
    #         print("\n⚠️ No content extracted")


# import litellm
# litellm._turn_on_debug()

class LMSResult(BaseModel):
    moodle_usage_found: bool
    reasoning: str


async def main_crawl4ai():
    api_key = dotenv.get_key(".env", "LLM_API_KEY")
    base_url = "https://chat-ai.academiccloud.de/v1"
    model = "llama-3.1-sauerkrautlm-70b-instruct"
    # 1. Define the LLM extraction strategy
    llm_strategy = LLMExtractionStrategy(
        llm_config = LLMConfig(provider="openai/llama-3.3-70b-instruct",
                               base_url=base_url, api_token=api_key),
        schema=LMSResult.model_json_schema(),
        extraction_type="schema",
        instruction="Finde heraus ob aus dem Text hervorgeht, dass Moodle oder eine auf Moodle basierende Software in der Einrichtung 'Universität Würzburg' genutzt wird. Antworte mit Wahr oder Falsch und gib eine kurze Begründung.",
        chunk_token_threshold=2000,
        overlap_rate=0.1,
        apply_chunking=True,
        input_format="markdown",   # or "html", "fit_markdown"
        extra_args={"temperature": 0.0, "max_tokens": 800}
    )

    # 2. Build the crawler config
    crawl_config = CrawlerRunConfig(
        scraping_strategy=PDFContentScrapingStrategy(),
        extraction_strategy=llm_strategy,
        cache_mode=CacheMode.DISABLED
    )

    # 3. Create a browser config if needed
    browser_cfg = BrowserConfig(headless=True)


    pdf_url = "https://hfm-wuerzburg.de/admin/QM/pdf/HfM_Wegweiser_fuer_Lehrende_Stand_21.08.2024.docx.pdf"


    async with AsyncWebCrawler(crawler_strategy=PDFCrawlerStrategy()) as crawler:
        # 4. Let's say we want to crawl a single page
        result = await crawler.arun(
            url=pdf_url,
            config=crawl_config
        )

        data = json.loads(result.extracted_content)
        print("Extracted items:", data)
        for item in data:
            if item.get('moodle_usage_found', False):
                print(f"Moodle usage found: {item.get('reasoning', '')}")
                break
        else:
            print("No Moodle usage found in the document.")
            

        # if result.success:
        #     # 5. The extracted content is presumably JSON
        #     data = json.loads(result.extracted_content)
        #     print("Extracted items:", data)

        #     # 6. Show usage stats
        #     # llm_strategy.show_usage()  # prints token usage
        # else:
        #     print("Error:", result.error_message)
        #     print(result)


if __name__ == "__main__":
    asyncio.run(main_crawl4ai())
