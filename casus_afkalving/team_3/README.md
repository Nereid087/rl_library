# Team 3

**Teamnaam:** 

**Teamleden:**

- Rojina
- Patrick
- Lars 

## Detectie afkalving waterkeringen (PoC)

Python-oplossing die locaties identificeert waar de waterzijde van een
watergang tussen twee leggerjaren dichter bij de keringsas is komen te
liggen (een technische indicatie voor mogelijke afkalving), gebouwd volgens
het implementatieplan "Detectie Afkalving Waterkeringen Rijnland".

### Architectuur

```text
casus_afkalving/team_3/
  config/config.yaml        configuratie (CRS, bronnen, analyseparameters)
  src/
    config.py                inlezen en valideren van config.yaml
    data_access/
      keringen.py             keringen ophalen via rijnland_core (ArcGIS)
      watergangen.py          lokale leggerjaren inlezen (shp/gpkg/gdb)
    analysis/
      matching.py              relevante watergangen per kering selecteren
      profiles.py              meetpunten en dwarsprofielen genereren
      shoreline.py             dichtstbijzijnde waterzijde per profiel bepalen
      changes.py               delta tussen twee leggerjaren berekenen
      hotspots.py              aaneengesloten negatieve meetpunten groeperen
    output/export.py           GeoPackage- en CSV-export
  main.py                      uitvoerpunt: doorloopt de volledige pipeline
  tests/                       unit- en integratietests (synthetische data)
```

Herbruikbare, generieke functies (ArcGIS-downloads, data-writer) staan in
`rijnland_core`; deze map bevat uitsluitend de project-specifieke logica
voor team 3.

### Configuratie

Pas [config/config.yaml](config/config.yaml) aan voordat je de pipeline
draait:

- `keringen.service`, `keringen.id_field`, `keringen.type_field`: nog
  **PLACEHOLDER**-waarden. Zoek de juiste laag op in de
  [Rijnland ArcGIS REST-directory](https://rijnland.enl-mcs.nl/arcgis/rest/services)
  en vul de echte servicenaam en veldnamen in.
- `watergangen.jaren`: paden naar de lokale leggerbestanden per jaar
  (shapefile, GeoPackage of FileGDB). Paden zijn relatief aan deze
  projectmap (`casus_afkalving/team_3`), tenzij een absoluut pad is
  opgegeven.
- `watergangen.lagen`: alleen nodig als een bronbestand (bijvoorbeeld een
  `.gdb`) meerdere lagen bevat.
- `watergangen.jaar_datums` / `vigerend_peildatum`: nodig om
  `delta_per_jaar_m` te kunnen berekenen; zonder bruikbare datum blijft dit
  veld leeg.
- `analyse.*`: bufferafstand, meetpunt-interval, profiellengte en
  hotspot-parameters; startwaarden komen uit het implementatieplan.
- `output.gebruik_cache` / `output.forceer_herberekening` / `output.cache_directory`:
  zie "Tussenresultaten cachen" hieronder.

### Uitvoeren

```bash
python main.py
```

De pipeline stopt met een duidelijke foutmelding (en logregel) als een
verplicht bronbestand ontbreekt, een configuratieveld nog een PLACEHOLDER
is, of er geen bruikbare geometrieën overblijven. Resultaten komen terecht
in `output/afkalving_analyse.gpkg` (lagen `keringen`, `meetpunten`,
`dwarsprofielen`, `waterzijde_metingen`, `veranderingen`, `hotspots`) en in
`output/metingen.csv`, `output/veranderingen.csv`, `output/hotspots.csv`.
### Tussenresultaten cachen

Elke pipelinestap (keringen ophalen, watergangen inlezen, matching,
meetpunten, dwarsprofielen, waterzijdemetingen, veranderingen, hotspots)
schrijft zijn resultaat weg in `output.cache_directory` (standaard
`cache/`). Bestaat dat bestand al bij een volgende run, dan wordt het
ingelezen in plaats van opnieuw berekend — handig als een latere stap
faalt en je niet alles opnieuw wilt doorrekenen.

- Zet `output.gebruik_cache: false` om de cache volledig uit te schakelen.
- Zet `output.forceer_herberekening: true` (of verwijder de `cache/`-map)
  om na een configuratiewijziging alles opnieuw te berekenen; de nieuwe
  resultaten worden daarna weer gecached.
### Testen

```bash
pytest
```

Alle tests gebruiken synthetische geometrieën en zijn dus onafhankelijk van
de ArcGIS-service en lokale bronbestanden.

### Aannames

- Watergangen zijn aangeleverd als polygonen (watervlak); alleen dan kan de
  waterzijde als polygoonrand worden bepaald. Hartlijn-only bronnen worden
  niet ondersteund in deze PoC.
- Een watergang-identificatieveld heet `watergang_id`, `WATERGANGID`,
  `OBJECTID`, `OBJECTID2` of `ID`; ontbreekt dit, dan valt de code terug op
  de rijvolgorde als identificatie (met een waarschuwing in de log).
- Er wordt nog geen risicoclassificatie toegepast; hotspots zijn uitsluitend
  een technische samenvatting van aaneengesloten negatieve metingen.
