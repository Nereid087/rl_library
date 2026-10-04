# Hackathon

Welkom! Volg de stappen hieronder om alles klaar te zetten. Dit duurt ongeveer 5 tot 10 minuten.

## 1. Clone de repository

Open een terminal (of de terminal in VS Code), ga naar de map waar je het project wilt hebben en voer uit:

```bash
git clone https://github.com/<jouw-gebruikersnaam>/<repo-naam>.git
cd <repo-naam>
```

> **Tip:** Heb je al een venv? Clone de repo dan *naast* je bestaande venv-map, niet erin.

## 2. Open de map in VS Code

**File → Open Folder…** en selecteer de gecloonde map `<repo-naam>`.

## 3. Koppel een virtual environment

Kies de situatie die bij jou past:

- **Je was bij een van de Python-lessen** → je hebt al een werkende venv. Volg **3A**.
- **Je was niet bij de Python-lessen** → je maakt zelf een venv aan. Volg **3B**.

### 3A. Je hebt al een venv

Laat VS Code naar je bestaande venv verwijzen:

1. Druk op `Ctrl+Shift+P` (Mac: `Cmd+Shift+P`).
2. Kies **Python: Select Interpreter**.
3. Kies **Enter interpreter path… → Find…**
4. Navigeer naar het Python-bestand in je venv:
   - **Windows:** `...\venv\Scripts\python.exe`
   - **Mac/Linux:** `.../venv/bin/python`

**Sluit daarna alle open terminals en open een nieuwe** (`Terminal → New Terminal`). Aan het begin van de regel zie je nu de naam van je venv.

> ⚠️ Verplaats of kopieer je venv **niet** naar deze map. Een venv werkt niet meer als je hem verplaatst.

Ga verder naar stap 4.

### 3B. Je maakt zelf een venv aan

Je maakt de venv aan via VS Code. VS Code koppelt hem dan meteen aan het project en installeert de benodigde packages.

1. Druk op `Ctrl+Shift+P` (Mac: `Cmd+Shift+P`).
2. Kies **Python: Create Environment**.
3. Kies **Venv**.
4. Kies de hoogste Python-versie uit de lijst.
5. Vink **requirements.txt** aan als VS Code vraagt welke dependencies je wilt installeren, en klik op **OK**.

Wacht tot VS Code klaar is (rechtsonder zie je de voortgang). Er staat nu een map `.venv` in je project.

**Sluit daarna alle open terminals en open een nieuwe** (`Terminal → New Terminal`). Aan het begin van de regel zie je nu `(.venv)`.

## 4. Werk je in notebooks?

Notebooks hebben een eigen kernelkeuze. Open een `.ipynb`-bestand, klik rechtsboven op **Select Kernel** en kies dezelfde venv als in stap 3.

## 5. Controleer je setup

Voer dit uit in een notebookcel of Python-bestand:

```python
import sys
print(sys.executable)
```

Het pad moet naar **jouw venv** wijzen. Wijst het ergens anders naartoe? Herhaal dan stap 3 (of stap 4 voor notebooks).

---

## Werken met Git tijdens de hackathon

Elk team werkt op een **eigen branch**. Push nooit rechtstreeks naar `main`.

**Eenmalig, aan het begin.** Eén teamlid maakt de branch aan (vervang `teamnaam` door de naam van je team):

```bash
git switch -c teamnaam
git push -u origin teamnaam
```

De andere teamleden halen de branch op:

```bash
git fetch
git switch teamnaam
```

Controleer met `git status` of je op de goede branch zit. Op de eerste regel moet `On branch teamnaam` staan.

**Tijdens het werken:**

```bash
git pull                                   # haal de laatste wijzigingen van je teamgenoten op
git add .
git commit -m "Korte beschrijving van je wijziging"
git push
```

Doe altijd eerst een `git pull` voordat je begint en voordat je pusht. Zo voorkom je de meeste conflicten.

## Mappenstructuur

```
<repo-naam>/
├── data/          # datasets
├── notebooks/     # verkennende notebooks
├── src/           # herbruikbare Python-code
├── requirements.txt
└── README.md
```

*(Pas aan naar de daadwerkelijke structuur.)*
