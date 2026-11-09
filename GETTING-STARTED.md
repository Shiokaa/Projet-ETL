1. Copier le .env.example
```bash
cp .env.example .env
```

2. Remplacer le token
```bash
PANDASCORE_TOKEN = TON_TOKEN
```

3. Créer un .venv
```bash
python -m venv .venv
```

4. Installer les dépendances
```bash
.venv/Scripts/activate
pip install -r requirements.txt
```

5. Lancer le pipeline, puis l'interface
```bash
python -m etl.run
python -m streamlit run web/app.py
```
