
# Scraper für Offenheitskritierien

Dieses Repo enthält eine erste version des Scrapers, welches das Kriterium "Wird eine offene Lernplattform verwendet?" für Hochschulen abfragt. Dazu wird eine Liste der Hochschulen durchgegangen, und für jede Hochschule und Lernplattform (Beispielhaft Moodle, OpenOLAT, Ilias) eine Google-Suche gestartet. Die Top 5 Suchergebnisse werden dann mittels eines LLMs nach hinweisen auf die Lernplattform analysisert. Die anderen Kritieren können in analoger Weise abgefragt werden.

Das Skript benötigt eine Liste der Institutionen, welche in einem gesonderten Repository gepflegt wird (TODO: wird noch hochgeladen).

Verwendung:

    # generiert results_new.jsonlines
    uv run handwritten_crawler.py
    
    # generiert results_new_report.xlsx
    uv run create_table.py
