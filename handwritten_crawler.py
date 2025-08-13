import asyncio
import csv
import json
import logging
import os
import re
from typing import TypedDict


from crawler.scraper import scrape_url
from crawler.search.google import google_search
from utils import parse_json_objects

# For unpickling the cached results
from crawler.scraper import LMSResult

# import litellm
# litellm._turn_on_debug()

logging.basicConfig(level=logging.WARNING)
log = logging.getLogger(__name__)
# hide litellm and httpx logging
logging.getLogger("LiteLLM").setLevel(logging.WARNING)
# logging.getLogger("LiteLLM").setLevel(logging.DEBUG)
# logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)
# logging.getLogger('cache_results').setLevel(logging.DEBUG)





def get_done_combos(output_file: str, keys: tuple[str, str]) -> set[tuple[str, str]]:
    combos_done = set()
    if os.path.exists(output_file):
        objs = parse_json_objects(output_file)
        for obj in objs:
            einrichtung = obj.get("einrichtung", "")
            software = obj.get("software", "")
            if einrichtung and software:
                combos_done.add((einrichtung, software))
    return combos_done



class UniversityDict(TypedDict):
    website: str
    name: str


def read_universities(filename: str) -> list[UniversityDict]:

    if not os.path.exists(filename):
        raise FileNotFoundError(f"File {filename} does not exist.")

    # parse csv
    # get columns website and Hochschulname
    # remove http(s):// and www. from website
    unis: list[UniversityDict] = []
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
            unis.append(dict(website=website, name=row["Hochschulname"]))
            # unis.append((website, row["Hochschulname"]))

    return unis

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

    input_file = '../einrichtungen/data/hochschulen.csv'
    output_file = "results_new.jsonlines"

    unis = read_universities('../einrichtungen/data/hochschulen.csv')
    combos_done = get_done_combos(output_file, ("einrichtung", "software"))



    # return
    # Hochschulname,Land,Hochschultyp,Trägerschaft,Promotionsrecht,Gründungsjahr(e),Anzahl Studierende,Mitgliedschaft HRK,website
    # Medical School Berlin – Hochschule für Gesundheit und Medizin (MSB),BE,Fachhochschule / HAW,privat,nein,2012,2488,nein,http://www.medicalschool-berlin.de/
    # Katholische Hochschule für Sozialwesen Berlin,BE,Fachhochschule / HAW,kirchlich,nein,1991,1235,"ja (Gruppe der Hochschulen für Angewandte Wissenschaften, Fachhochschulen)",https://www.khsb-berlin.de/
    # International Psychoanalytic University Berlin,BE,Universität,privat,nein,2009,894,nein,https://www.ipu-berlin.de/
    # IB Hochschule für Gesundheit und Soziales,BE,Fachhochschule / HAW,privat,nein,2006,776,nein,https://www.ib-hochschule.de/


    log.info(f"Found {len(unis)} universities in {input_file}")

    # unis = [
    #     ("uni-kassel.de", "Universität Kassel"),
    #     ("hfm-wuerzburg.de", "Hochschule für Musik Würzburg"),
    #     ("fh-aachen.de", "FH Aachen"),
    #     ("rwth-aachen.de", "RWTH Aachen"),
    #     ("hs-aalen.de", "Hochschule Aalen"),
    #     ("uni-goettingen.de", "Universität Göttingen"),
    # ]

    prompt_template = "Finde heraus ob aus dem Text hervorgeht, dass {software} oder eine auf {software} basierende Software in der Einrichtung {einrichtung} genutzt wird. Antworte mit Wahr oder Falsch und gib eine kurze Begründung."


    for index, item in enumerate(unis):
        print(f"Processing {index + 1}/{len(unis)}: {item['name']} ({item['website']})")
        site = item["website"]
        einrichtung = item["name"]

        # , "OpenOLAT", "Canvas", "Stud.IP"]:
        for software in ["Moodle", "Ilias", "OpenOLAT"]:
            if (einrichtung, software) in combos_done:
                log.info(f"Skipping {einrichtung} - {software}, already done")
                continue

            # Step 1: Google search
            results = google_search(f"site:{site} {software}", skip_cache=False)

            combined_verdict = False
            scraping_results = []
            # For each result...
            for index, url in enumerate(results[:5]):
                log.debug("--> Scraping url #%d: %s", index, url)

                # Step 2: Scrape the URL and apply LLM
                arguments = {
                    "software": software,
                    "einrichtung": einrichtung,
                    "url": url
                }
                result = await scrape_url(url, prompt_template=prompt_template, arguments=arguments, skip_cache=False)
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

            log.info("==> combined result for %s / %s: %s", einrichtung, software, combined_verdict)

            res_item = {
                "einrichtung": einrichtung,
                "software": software,
                "usage_found": combined_verdict,
                "reasoning": combined_reasoning
            }

            # print as json
            with open(output_file, "a", encoding="utf-8") as f:
                print("==" * 20, "adding result for", einrichtung, software, "==")
                print(json.dumps(res_item, ensure_ascii=False), file=f, flush=True)



if __name__ == "__main__":
    # main()
    asyncio.run(main())
