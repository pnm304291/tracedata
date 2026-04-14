# Cong cu loc dong tu file Excel/CSV

## 1) Cai dat thu vien

```powershell
pip install -r requirements.txt
```

## 2) Chay ung dung web

```powershell
python app.py
```

## 3) Mo tren trinh duyet

Go to:

```text
http://127.0.0.1:5000
```

## Cach su dung

1. Tai len file (`.csv`, `.xlsx`, `.xls`).
2. Nhap gia tri/ky tu can loc (moi dong 1 gia tri, hoac cach nhau boi dau phay).
3. Chon che do:
   - `Chua bat ky gia tri nao (OR)`: dong khop neu chua it nhat 1 gia tri.
   - `Chua tat ca gia tri (AND)`: dong khop chi khi chua day du tat ca gia tri.
4. Bam **Loc Du Lieu** de xem cac dong khop.
5. Bam **Tai CSV** hoac **Tai Excel** de tai ket qua.

Luu y:
- Gioi han kich thuoc file: 30 MB.
- Trang chi hien toi da 1000 dong khop de dam bao toc do.
- Ma xuat file duoc luu trong bo nho khoang 1 gio. Neu het han, hay loc lai.

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
