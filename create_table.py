# {
#   "einrichtung": "International Psychoanalytic University Berlin",
#   "software": "Moodle",
#   "usage_found": true,
#   "reasoning": "Es wird erwähnt, dass Prof. Dr. Phil C. Langer im Jahr 2022 an einer Fortbildung teilgenommen hat, bei der es um 'Teaching Competence – Lehren mit Moodle: Kollaboratives Arbeiten' ging. Dies deutet darauf hin, dass Moodle oder eine auf Moodle basierende Software in der Einrichtung International Psychoanalytic University Berlin genutzt wird, da der Professor an dieser Universität tätig ist und die Fortbildung seine Fähigkeiten im Bereich der Hochschuldidaktik erweitern sollte."
# }
# {
#   "einrichtung": "International Psychoanalytic University Berlin",
#   "software": "Ilias",
#   "usage_found": false,
#   "reasoning": "(No usage found in any document)"
# }
# {
#   "einrichtung": "International Psychoanalytic University Berlin",
#   "software": "OpenOLAT",
#   "usage_found": false,
#   "reasoning": "(No usage found in any document)"
# }

import os
import pandas as pd
from collections import defaultdict

from utils import parse_json_objects

def main():
    filename = "results2.jsonlines"

    # nested dict
    # data[einrichtung][software] = {
    #     "usage_found": "no",
    #     "reasoning": ""
    # }
    data = defaultdict(lambda: defaultdict(lambda: {
        "usage_found": "",
        "reasoning": ""
    }))

    # Parse JSON-Objekte aus der Datei
    json_objects = list(parse_json_objects(filename))
    print(f"Gefundene JSON-Objekte: {len(json_objects)}")
    
    for entry in json_objects:
        print(f"Processing entry: {entry}")
        einrichtung = entry.get("einrichtung", "")
        software = entry.get("software", "")
        usage_found = entry.get("usage_found", False)
        reasoning = entry.get("reasoning", "")

        if einrichtung and software:
            data[einrichtung][software]["usage_found"] = "yes" if usage_found else "no"
            data[einrichtung][software]["reasoning"] = reasoning


    for item in list(data.items())[:5]:
        einrichtung, software_data = item
        print(f"Einrichtung: {einrichtung}")
        for software, details in software_data.items():
            print(f"  Software: {software}, Nutzung: {details['usage_found']}, Begründung: {details['reasoning']}")
        print()

    # Excel-Export
    create_excel_report(data)

def create_excel_report(data):
    """Erstellt eine Excel-Tabelle mit Einrichtungen als Zeilen und Software-Programmen als Spalten"""
    
    # Sammle alle einzigartigen Software-Programme
    all_software = set()
    for einrichtung_data in data.values():
        all_software.update(einrichtung_data.keys())
    
    all_software = sorted(list(all_software))
    
    # Erstelle DataFrame
    rows = []
    for einrichtung in sorted(data.keys()):
        row = {"Einrichtung": einrichtung}
        
        # Für jede Software füge sowohl Nutzung als auch Begründung hinzu
        for software in all_software:
            if software in data[einrichtung]:
                row[f"{software}"] = data[einrichtung][software]["usage_found"]
                row[f"{software}_Begründung"] = data[einrichtung][software]["reasoning"]
            else:
                row[f"{software}"] = "no"
                row[f"{software}_Begründung"] = "(No usage found in any document)"
        
        rows.append(row)
    
    df = pd.DataFrame(rows)
    
    # Speichere als Excel-Datei
    output_filename = "software_usage_report.xlsx"
    df.to_excel(output_filename, index=False, engine='openpyxl')
    print(f"Excel-Bericht erstellt: {output_filename}")
    
    # Zeige eine Vorschau der ersten paar Zeilen
    print("\nVorschau der ersten 3 Zeilen:")
    print(df.head(3).to_string(index=False))

if __name__ == "__main__":
    main()