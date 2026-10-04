# Hackathon

Welcome! Follow the steps below to get set up. This takes about 5 minutes.

## 1. Clone the repository

Open a terminal (or the terminal in VS Code), go to the folder where you want the project, and run:

```bash
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>
```

> **Tip:** Clone the repo *next to* your existing venv folder, not inside it.

## 2. Open the folder in VS Code

**File → Open Folder…** and select the cloned `<repo-name>` folder.

## 3. Select your existing virtual environment

You already have a working venv. Point VS Code to it:

1. Press `Ctrl+Shift+P` (Mac: `Cmd+Shift+P`).
2. Choose **Python: Select Interpreter**.
3. Choose **Enter interpreter path… → Find…**
4. Browse to the Python executable inside your venv:
   - **Windows:** `...\venv\Scripts\python.exe`
   - **Mac/Linux:** `.../venv/bin/python`

Then **close any open terminals and open a new one** (`Terminal → New Terminal`). It should now show your venv name at the start of the prompt.

> ⚠️ Do **not** move or copy your venv into this folder. Venvs break when relocated.

## 4. Working in notebooks?

Notebooks have their own kernel picker. Open a `.ipynb` file, click **Select Kernel** in the top-right corner, and choose the same venv.

## 5. Install the required packages

With your venv active in the terminal, run:

```bash
pip install -r requirements.txt
```

## 6. Check your setup

Run this in a notebook cell or Python file:

```python
import sys
print(sys.executable)
```

The path should point to **your venv**. If it points somewhere else, repeat step 3 (or step 4 for notebooks).

---

## Working with Git during the hackathon

Each team works on its **own branch**. Never push directly to `main`.

**Once, at the start** (replace `team-name` with your team's name):

```bash
git switch -c team-name
git push -u origin team-name
```

**While working:**

```bash
git pull                     # get your teammates' latest changes
git add .
git commit -m "Short description of what you changed"
git push
```

Pull before you start working and before you push. That prevents most conflicts.

## Folder structure

```
<repo-name>/
├── data/          # datasets
├── notebooks/     # exploration notebooks
├── src/           # reusable Python code
├── requirements.txt
└── README.md
```

*(Adjust to match the actual structure.)*
