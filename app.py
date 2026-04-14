from __future__ import annotations

import io
import os
import re
import time
import uuid
from pathlib import Path
from typing import List, Tuple

import pandas as pd
from flask import Flask, abort, render_template, request, send_file

BASE_DIR = Path(__file__).resolve().parent
app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)
app.config["MAX_CONTENT_LENGTH"] = 30 * 1024 * 1024  # 30 MB

ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls"}
MAX_RENDER_ROWS = 1000
EXPORT_CACHE_TTL_SECONDS = 3600
EXPORT_CACHE_MAX_ITEMS = 30
EXPORT_CACHE: dict[str, dict[str, object]] = {}


def parse_terms(raw_text: str) -> List[str]:
    """Split terms by newline, comma, semicolon, or tab and remove duplicates."""
    parts = re.split(r"[\n,;\t]+", raw_text or "")
    cleaned: List[str] = []
    seen = set()

    for item in parts:
        value = item.strip()
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(value)

    return cleaned


def allowed_file(filename: str) -> bool:
    if "." not in filename:
        return False
    return filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def load_dataframe(file_bytes: bytes, filename: str) -> pd.DataFrame:
    ext = filename.rsplit(".", 1)[1].lower()
    stream = io.BytesIO(file_bytes)

    if ext in {"xlsx", "xls"}:
        df = pd.read_excel(stream, dtype=str)
    else:
        # Try UTF-8 first, then Windows-1258 fallback.
        try:
            df = pd.read_csv(stream, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        except UnicodeDecodeError:
            stream.seek(0)
            df = pd.read_csv(stream, dtype=str, keep_default_na=False, encoding="cp1258")

    return df.fillna("")


def prune_export_cache() -> None:
    now = time.time()
    expired = [
        token
        for token, payload in EXPORT_CACHE.items()
        if now - float(payload["created_at"]) > EXPORT_CACHE_TTL_SECONDS
    ]
    for token in expired:
        EXPORT_CACHE.pop(token, None)

    if len(EXPORT_CACHE) <= EXPORT_CACHE_MAX_ITEMS:
        return

    # Remove oldest entries if cache grows too much.
    ordered = sorted(EXPORT_CACHE.items(), key=lambda item: float(item[1]["created_at"]))
    overflow_count = len(EXPORT_CACHE) - EXPORT_CACHE_MAX_ITEMS
    for token, _ in ordered[:overflow_count]:
        EXPORT_CACHE.pop(token, None)


def cache_export_dataframe(df: pd.DataFrame, filename: str) -> str:
    prune_export_cache()
    token = uuid.uuid4().hex
    EXPORT_CACHE[token] = {
        "created_at": time.time(),
        "filename": filename.rsplit(".", 1)[0],
        "df": df.copy(),
    }
    return token


def build_mask(row_text: pd.Series, terms: List[str], mode: str, case_sensitive: bool) -> Tuple[pd.Series, List[str]]:
    mask = pd.Series(True if mode == "all" else False, index=row_text.index)
    missing_terms: List[str] = []

    for term in terms:
        lookup = term if case_sensitive else term.lower()
        contains_term = row_text.str.contains(re.escape(lookup), regex=True, na=False)
        has_any = bool(contains_term.any())

        if not has_any:
            missing_terms.append(term)

        if mode == "all":
            mask &= contains_term
        else:
            mask |= contains_term

    return mask, missing_terms


@app.route("/", methods=["GET", "POST"])
def index():
    context = {
        "error": None,
        "summary": None,
        "columns": [],
        "rows": [],
        "missing_terms": [],
        "search_terms_raw": "",
        "match_mode": "any",
        "case_sensitive": False,
        "export_token": None,
    }

    if request.method == "POST":
        uploaded_file = request.files.get("data_file")
        search_terms_raw = request.form.get("search_terms", "")
        match_mode = request.form.get("match_mode", "any")
        case_sensitive = request.form.get("case_sensitive") == "on"

        context["search_terms_raw"] = search_terms_raw
        context["match_mode"] = match_mode
        context["case_sensitive"] = case_sensitive

        if not uploaded_file or uploaded_file.filename == "":
            context["error"] = "Vui long chon file truoc."
            return render_template("index.html", **context)

        if not allowed_file(uploaded_file.filename):
            context["error"] = "Chi ho tro file CSV, XLSX, XLS."
            return render_template("index.html", **context)

        terms = parse_terms(search_terms_raw)
        if not terms:
            context["error"] = "Vui long nhap it nhat mot gia tri/ky tu can loc."
            return render_template("index.html", **context)

        try:
            file_bytes = uploaded_file.read()
            df = load_dataframe(file_bytes, uploaded_file.filename)
        except Exception as exc:  # pragma: no cover - user input dependent
            context["error"] = f"Khong the doc file nay: {exc}"
            return render_template("index.html", **context)

        if df.empty:
            context["error"] = "File tai len khong co dong du lieu nao."
            return render_template("index.html", **context)

        as_text = df.astype(str)
        row_text = as_text.agg(" | ".join, axis=1)
        if not case_sensitive:
            row_text = row_text.str.lower()

        mask, missing_terms = build_mask(row_text, terms, match_mode, case_sensitive)
        matched_df = as_text[mask]

        context["summary"] = {
            "file_name": uploaded_file.filename,
            "total_rows": len(df),
            "matched_rows": len(matched_df),
            "term_count": len(terms),
            "rendered_rows": min(len(matched_df), MAX_RENDER_ROWS),
        }
        context["export_token"] = cache_export_dataframe(matched_df, uploaded_file.filename)
        context["missing_terms"] = missing_terms
        context["columns"] = list(matched_df.columns)
        context["rows"] = matched_df.head(MAX_RENDER_ROWS).to_dict(orient="records")

    return render_template("index.html", **context)


@app.get("/export/<token>")
def export(token: str):
    prune_export_cache()
    payload = EXPORT_CACHE.get(token)
    if payload is None:
        abort(404, description="Phien xuat file da het han hoac khong hop le. Vui long loc lai.")

    export_format = request.args.get("format", "csv").lower()
    file_base = str(payload["filename"])
    df = payload["df"]
    if not isinstance(df, pd.DataFrame):
        abort(500, description="Du lieu xuat file khong hop le")

    if export_format == "csv":
        buffer = io.StringIO()
        df.to_csv(buffer, index=False)
        bytes_buffer = io.BytesIO(buffer.getvalue().encode("utf-8-sig"))
        bytes_buffer.seek(0)
        return send_file(
            bytes_buffer,
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"{file_base}_matched.csv",
        )

    if export_format == "xlsx":
        bytes_buffer = io.BytesIO()
        with pd.ExcelWriter(bytes_buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="matched_rows")
        bytes_buffer.seek(0)
        return send_file(
            bytes_buffer,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=f"{file_base}_matched.xlsx",
        )

    abort(400, description="Dinh dang xuat khong duoc ho tro")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
