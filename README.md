# Hackathon

Welkom bij de hackathon! In deze README zet je stap voor stap alles klaar op je laptop. Dit duurt ongeveer 15 minuten.

Lees elke stap helemaal voordat je begint. Loop je ergens vast? Steek je hand op, dan helpt een begeleider je.

---

## Stap 0. Voordat je begint

Controleer dat je het volgende hebt:

1. **Een GitHub-account.** Heb je er nog geen? Maak er een aan op [github.com](https://github.com).
2. **Toegang tot deze repository.** Je hebt een uitnodiging gekregen per e-mail. Klik in die e-mail op **View invitation** en daarna op **Accept invitation**. Kun je de e-mail niet vinden? Ga naar [github.com/notifications](https://github.com/notifications).
3. **VS Code**, met de extensies **Python** en **Jupyter**. Je installeert extensies via het blokjes-icoon in de linkerbalk van VS Code.
4. **Je teamnummer.** Dit hoor je van de begeleider. Je zit in team 1, 2, 3 of 4.

### Kies hoe je met Git werkt

Je kunt op twee manieren met Git werken. Kies er **één** en volg in de rest van deze README alleen de stappen voor jouw keuze.

| | **Route A: GitHub Desktop** | **Route B: Terminal** |
|---|---|---|
| Wat is het? | Een programma met knoppen voor Git | Je typt Git-commando's in de terminal van VS Code |
| Wat heb je nodig? | [GitHub Desktop](https://desktop.github.com) geïnstalleerd | Git geïnstalleerd op je laptop |
| Geschikt voor | Je hebt nog nooit met Git gewerkt | Je hebt al eens met Git gewerkt |

**Route A: log in bij GitHub Desktop.** Open GitHub Desktop en log in met je GitHub-account. Op Windows: **File → Options → Accounts**. Op Mac: **GitHub Desktop → Settings → Accounts**. Klik op **Sign in** en volg de stappen in je browser.

**Route B: controleer of Git geïnstalleerd is.** Open VS Code, klik bovenin op **Terminal → New Terminal** en typ:

```bash
git --version
```

Zie je iets als `git version 2.45.0`? Dan is Git geïnstalleerd. Zie je een foutmelding? Installeer Git via [git-scm.com](https://git-scm.com/downloads), sluit VS Code helemaal af en open het opnieuw.

---

## Stap 1. Haal de repository naar je laptop (clonen)

Met clonen maak je een kopie van de repository op je eigen laptop.

> **Heb je al een venv uit de Python-lessen?** Zet de repository dan *naast* je venv-map, niet erin.

### Route A: GitHub Desktop

1. Open GitHub Desktop.
2. Klik op **File → Clone repository**.
3. Klik bovenin op het tabblad **GitHub.com**.
4. Klik in de lijst op **<repo-naam>**. Staat hij er niet tussen? Dan heb je de uitnodiging nog niet geaccepteerd (zie stap 0).
5. Onder **Local path** zie je waar de map komt. Onthoud dit pad.
6. Klik op **Clone**.

### Route B: Terminal

1. Open VS Code en open een terminal: **Terminal → New Terminal**.
2. Ga naar de map waar je het project wilt hebben. Bijvoorbeeld je map Documenten:

   ```bash
   cd ~/Documents
   ```

3. Clone de repository:

   ```bash
   git clone https://github.com/<gebruikersnaam>/<repo-naam>.git
   ```

4. Ga de nieuwe map in:

   ```bash
   cd <repo-naam>
   ```

5. Voer dit commando één keer uit. Het zorgt ervoor dat `git pull` later altijd goed werkt:

   ```bash
   git config --global pull.rebase false
   ```

---

## Stap 2. Ga naar de branch van je team

Elk team werkt op een eigen **branch**: een eigen versie van het project. De branches heten `team-1`, `team-2`, `team-3` en `team-4`.

Je werkt **nooit** op de branch `main`. Daar staat alleen de startversie.

In de voorbeelden hieronder staat `team-1`. **Vervang `1` door jouw teamnummer.**

### Route A: GitHub Desktop

1. Klik bovenin op **Current branch**.
2. Klik in de lijst op **team-1**.
3. Controleer: bovenin bij **Current branch** staat nu `team-1`.

### Route B: Terminal

1. Typ in de terminal (je zit nog in de map `<repo-naam>`):

   ```bash
   git switch team-1
   ```

2. Controleer of het gelukt is:

   ```bash
   git status
   ```

   Op de eerste regel moet staan: `On branch team-1`.

---

## Stap 3. Open de repository in VS Code

### Route A: GitHub Desktop

1. Klik in GitHub Desktop op **Repository → Open in Visual Studio Code**.

### Route B: Terminal

1. Klik in VS Code op **File → Open Folder…**
2. Ga naar de map `<repo-naam>` die je in stap 1 hebt gemaakt en klik op **Openen** (Mac: **Open**).

### Controleer (beide routes)

Links in VS Code (de **Explorer**) zie je nu de mappen van het project, waaronder `casus_afkalving` en `casus_waterdiepte`. Zie je de Explorer niet? Klik op het bovenste icoon in de linkerbalk (twee papiertjes).

---

## Stap 4. Koppel een virtual environment (venv)

Een venv is een afgeschermde Python-omgeving met alle packages die je nodig hebt.

- **Was je bij een van de Python-lessen?** Dan heb je al een werkende venv. Volg **4A**.
- **Was je niet bij de Python-lessen?** Dan maak je nu een venv aan. Volg **4B**.

### 4A. Je hebt al een venv

1. Druk in VS Code op `Ctrl+Shift+P` (Mac: `Cmd+Shift+P`). Bovenin opent een zoekbalk.
2. Typ `Select Interpreter` en klik op **Python: Select Interpreter**.
3. Klik op **Enter interpreter path…** en daarna op **Find…**
4. Ga naar je venv-map en kies het Python-bestand:
   - **Windows:** `venv\Scripts\python.exe`
   - **Mac:** `venv/bin/python`
5. **Sluit alle open terminals**: klik in het terminalvenster op het prullenbakje. Open daarna een nieuwe: **Terminal → New Terminal**.
6. Controleer: aan het begin van de regel in de terminal staat nu de naam van je venv tussen haakjes, bijvoorbeeld `(venv)`.

> ⚠️ Verplaats of kopieer je venv **niet** naar de projectmap. Een venv werkt niet meer als je hem verplaatst.

### 4B. Je maakt een nieuwe venv

1. Druk in VS Code op `Ctrl+Shift+P` (Mac: `Cmd+Shift+P`). Bovenin opent een zoekbalk.
2. Typ `Create Environment` en klik op **Python: Create Environment**.
3. Klik op **Venv**.
4. Kies de hoogste Python-versie uit de lijst.
5. VS Code vraagt welke dependencies je wilt installeren. Vink **requirements.txt** aan en klik op **OK**.
6. Wacht tot VS Code klaar is. Rechtsonder zie je de voortgang. Dit kan een paar minuten duren.
7. Controleer: in de Explorer staat nu een map `.venv`.
8. **Sluit alle open terminals**: klik in het terminalvenster op het prullenbakje. Open daarna een nieuwe: **Terminal → New Terminal**.
9. Controleer: aan het begin van de regel in de terminal staat nu `(.venv)`.

---

## Stap 5. Installeer de Rijnland-library

In deze repository zit een eigen Python-library: `rijnland_core`. Die installeer je één keer in je venv. Daarna kun je hem in elk notebook gebruiken.

1. Open in de Explorer het bestand `installeer.ipynb`. Het staat in de hoofdmap, niet in een casusmap.
2. Klik rechtsboven in het notebook op **Select Kernel**. Kies **Python Environments** en daarna dezelfde venv als in stap 4.
3. Klik in de cel met `import sys` en druk op `Shift+Enter`.
4. Controleer: er staat `Goed: je zit in een venv.` Staat er `Let op`? Kies dan opnieuw de kernel, zoals in 2.
5. Klik in de cel met `%pip install -e .` en druk op `Shift+Enter`.
6. Wacht tot de cel klaar is. Dit kan even duren.
7. Controleer: onderaan staat `Successfully installed rl-library-0.1.0`.

---

## Stap 6. Controleer of alles werkt

1. Klik in de Explorer met de rechtermuisknop op de map `casus_afkalving`, dan op de map van je team (bijvoorbeeld `team_1`), en kies **New File…**
2. Noem het bestand `test.ipynb` en druk op Enter. Er opent een notebook.
3. Klik rechtsboven in het notebook op **Select Kernel**. Kies **Python Environments** en daarna dezelfde venv als in stap 4.
4. Typ in de eerste cel:

   ```python
   import sys
   print(sys.executable)
   import rijnland_core
   ```

5. Druk op `Shift+Enter` om de cel uit te voeren.
6. Controleer: het pad dat verschijnt moet naar **jouw venv** wijzen (er staat `venv` of `.venv` in). Staat er iets anders? Herhaal stap 4 en kies daarna opnieuw de kernel.
7. Controleer: onder het pad staat geen foutmelding. Zie je `ModuleNotFoundError: No module named 'rijnland_core'`? Herhaal dan stap 5. Let op dat je daar dezelfde venv kiest als hier.
8. Werkt het? Verwijder `test.ipynb` weer: rechtermuisknop op het bestand → **Delete**.

---

## Stap 7. Klaar met de setup!

Ga nu naar je eerste opdracht. Open in de Explorer het teambestand van jouw team:

`casus_afkalving` → `team_<jouw nummer>` → `TEAM_<jouw nummer>.md`

Zit je in team 3? Dan open je `casus_afkalving` → `team_3` → `TEAM_3.md`.

Daar staat wat je samen met je team gaat doen. Ook als je straks met casus waterdiepte begint, start je met dit bestand.

---

## Mappenstructuur

```
<repo-naam>/
├── casus_afkalving/
│   ├── data/              # data voor casus afkalving (niet aanpassen)
│   ├── team_1/
│   │   └── TEAM_1.md      # teambestand met eerste opdracht voor team 1
│   ├── team_2/
│   │   └── TEAM_2.md
│   ├── team_3/
│   │   └── TEAM_3.md
│   └── team_4/
│       └── TEAM_4.md
├── casus_waterdiepte/
│   ├── data/              # data voor casus waterdiepte (niet aanpassen)
│   ├── team_1/
│   ├── team_2/
│   ├── team_3/
│   └── team_4/
├── installeer.ipynb       # installeert de Rijnland-library (stap 5)
├── requirements.txt
└── README.md              # dit bestand
```
