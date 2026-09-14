# Run on macOS

```bash
cd ~/Downloads
unzip -o Home_Energy_Upgrade_Recommender_LATEST_ONLY.zip
cd Home_Energy_Upgrade_Recommender
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

Do not type the `%` or `$` shell prompt characters.
