import asyncio
import json
import os
import time

import dotenv
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.processors.pdf import (PDFContentScrapingStrategy,
                                     PDFCrawlerStrategy)
from googleapiclient.discovery import build
from langchain_openai import ChatOpenAI
from openai import OpenAI
from pydantic import SecretStr
import pdfplumber
import requests


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
        max_tokens=200,
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

if __name__ == "__main__":
    asyncio.run(main())
