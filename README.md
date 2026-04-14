# Trace rows from uploaded file

## 1) Install dependencies

```powershell
pip install -r requirements.txt
```

## 2) Run web app

```powershell
python app.py
```

## 3) Open in browser

Go to:

```text
http://127.0.0.1:5000
```

## How to use

1. Upload a file (`.csv`, `.xlsx`, `.xls`).
2. Paste values to trace (one value per line, or separated by comma).
3. Choose:
   - `Any value (OR)`: row matches if it contains at least one value.
   - `All values (AND)`: row matches only if it contains all values.
4. Click **Trace** to see matching rows.
5. Click **Export CSV** or **Export Excel** to download the matched result.

Notes:
- File size is limited to 30 MB.
- The page shows up to 1000 matched rows for performance.
- Export token is kept in memory for about 1 hour. If expired, run trace again.

## Deploy online (Render)

Project is already prepared for deployment with these files:
- `Procfile`
- `render.yaml`
- `gunicorn` in `requirements.txt`

Steps:

1. Push this folder to a GitHub repository.
2. Go to Render and create a new **Web Service** from your GitHub repo.
3. Render should detect Python automatically.
4. Use these settings if needed:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
5. Click Deploy.
6. After build is done, open the generated public URL and use it normally.

Important note:
- Current export cache is in-memory of a single server instance, so if service restarts, export token is reset.
