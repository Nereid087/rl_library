# Kernzones Streamlit-dashboard

## Bestanden in dezelfde map

- app.py
- requirements.txt
- Kernzones_2013_vs_Vigerend.csv
- Kernzones_2013_vs_Vigerend.geojson
- Kernzones_2013_vs_Vigerend.html (optioneel)

## Installeren

Open Anaconda Prompt, PowerShell of de terminal van VS Code in deze map:

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Starten

```powershell
streamlit run app.py
```

Als `streamlit` niet als opdracht wordt gevonden:

```powershell
python -m streamlit run app.py
```

De browser opent meestal automatisch. Anders toont de terminal een Local URL.

## Werking

De app gebruikt GeoJSON voor de polygonen. CSV-attributen worden via `Wijziging_ID` gekoppeld. Nieuwe CSV-kolommen worden automatisch behouden en staan op het tabblad Data. Het HTML-bestand is optioneel en wordt als download aangeboden.
