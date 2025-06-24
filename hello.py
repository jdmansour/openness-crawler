from googleapiclient.discovery import build

from config import api_key, cse_id

def google_search(query):
    service = build("customsearch", "v1", developerKey=api_key)
    res = service.cse().list(q=query, cx=cse_id, num=10).execute()
    return [item['link'] for item in res.get('items', [])]

def main():
    results = google_search("Python web scraping")
    for url in results:
        print(url)


if __name__ == "__main__":
    main()
