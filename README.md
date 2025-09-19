
# Scraper für Offenheitskritierien

> [!NOTE]  
> Die aktuelle Version des Crawlers befindet sich hier:
> https://github.com/jdmansour/openness-crawler-prefect

Dieser Scraper ist im Rahmen einer Studie der Wikimedia Deutschland zum Thema "Offenheit" entstanden. Die Fragestellung ist, wie offen sind öffentliche Einrichtungen in Deutschland wirklich?

Dazu wurde eine Liste von zu evaluierenden Einrichtungen erstellt, zusammen mit Kritieren für die verschiedenen Bereiche (Bildung, Kultur, Forschung, ...). Diese teilen sich in operative Kriterien (was ist die Praxis) und strategische Kriterien (z.B. was steht in einer Leitline).

Für die erste Version des Scrapers haben wir uns das operative Kriterium "Vorhandensein einer quelloffenen Kurs- bzw. Lernplattform" an Hochschulen angeschaut, das zum Faktor "Einsatz offener digitaler Werkzeuge für Lehre und Verwaltung" in der Dimension "Offener Zugang zu Wissen und Lehre" zählt. 

Der Scraper geht eine Liste der Hochschulen durch, wobei für jede Hochschule und Lernplattform (Beispielhaft Moodle, OpenOLAT, Ilias) eine Google-Suche gestartet wird. Die Top 5 Suchergebnisse werden dann mittels eines LLMs nach hinweisen auf die Lernplattform analysisert. Die anderen Kritieren können in analoger Weise abgefragt werden.

## Vorbereitung

Das Skript benötigt eine Liste der Institutionen, welche in einem gesonderten Repository gepflegt wird (TODO: wird noch hochgeladen).

API-Keys für Google und das LLM müssen in einer .env-Datei hinterlegt werden. Lege dazu eine `.env' mit folgendem Inhalt an:

```
GOOGLE_API_KEY=...
GOOGLE_CSE_ID=...
LLM_API_KEY=...
LLM_BASE_URL=https://api.openai.com/v1/
LLM_PROVIDER=gpt-5-mini
```

## Verwendung:

    # generiert results_new.jsonlines
    uv run handwritten_crawler.py
    
    # generiert results_new_report.xlsx
    uv run create_table.py

## Caveats:
- In dieser Fassung kann der Scraper nur sequenziell die Einrichtungsliste durchgehen, d.h. es wird nur eine Einrichtung auf einmal bearbeitet. Das Scrapen könnte stark beschleunigt werden, wenn dies parallelisiert würde. (TODO: parallele Version auf Basis von Prefect teilen).
- Wenn eine Seite sehr viel Text enthält, teilt der Scraper sie in Stücke (Chunks), und gibt diese dem LLM individuell zur Beurteilung. Dabei werden maximal 5 Chunks betrachtet, damit der Ressourcenverbrauch nicht aus dem Ruder läuft (z.B. wenn ein Vorlesungsverzeichnis mit mehreren hundert Seiten eingelesen wird). Die Chunks werden alle nacheinander betrachtet. Selbst wenn ein positives Ergebnis im ersten Chunk gefunden wird, werden alle Chunks an das LLM gegeben. Das ist eine Beschränkung von der eingesetzten Bibliothek crawl4ai. Eine mögliche Verbesserung wäre abzubrechen nachdem ein positives Ergebnis gefunden wurde.