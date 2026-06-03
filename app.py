import os
import json
import glob
import zipfile
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

import pandas as pd
from flask import Flask, request, jsonify, render_template

BASE_DIR = Path(__file__).parent
app = Flask(__name__)

# ── Role groups ───────────────────────────────────────────────────────────────

ROLE_GROUPS = {
    "Software Engineer / Developer": [
        "software engineer", "software developer", "application developer",
        "application engineer", "systems engineer", "systems developer",
        "full stack engineer", "backend engineer", "frontend engineer",
    ],
    "Full Stack / Web": [
        "full stack", "fullstack", "react developer", "react engineer",
        "next.js", "nextjs", "angular developer", "vue developer",
        "web developer", "web engineer", "frontend developer", "ui developer",
        "ui engineer", "node.js developer", "nodejs developer",
    ],
    "Backend / Java / Spring / API": [
        "backend developer", "java developer", "java engineer",
        "spring boot", "spring developer", "j2ee", "rest api",
        "microservices developer", "microservices engineer",
        "api developer", "api engineer",
    ],
    "Python / AI / ML / GenAI": [
        "python developer", "python engineer", "machine learning",
        "ml engineer", "ai engineer", "nlp engineer",
        "llm engineer", "rag engineer", "generative ai", "genai",
        "deep learning", "computer vision", "artificial intelligence",
        "ai/ml",
    ],
    "Data / Analytics / BI": [
        "data scientist", "data analyst", "business intelligence",
        "bi developer", "bi engineer", "analytics engineer",
        "data warehouse", "etl developer", "etl engineer",
        "reporting analyst", "tableau", "power bi",
    ],
    "Cloud / DevOps": [
        "cloud engineer", "cloud architect", "devops", "devsecops",
        "aws engineer", "azure engineer", "gcp engineer",
        "site reliability", "sre", "platform engineer",
        "infrastructure engineer", "kubernetes", "terraform",
    ],
}

SOC_FALLBACK = {
    "Software Engineer / Developer": ["15-1252", "15-1253", "15-1254", "15-1256", "15-1299"],
    "Full Stack / Web":              ["15-1254", "15-1256"],
    "Backend / Java / Spring / API": ["15-1252", "15-1253"],
    "Python / AI / ML / GenAI":      ["15-2051", "15-2099", "15-1212", "15-1211"],
    "Data / Analytics / BI":         ["15-2051", "15-2099", "15-1211"],
    "Cloud / DevOps":                ["15-1244", "15-1299", "15-1241"],
}

STAFFING_KEYWORDS = [
    "staffing", "recruiting", "recruitment", "consulting", "consultancy",
    "it solutions", "outsourcing", "talent solutions", "manpower",
    "workforce solutions", "placement", "it services", "tech solutions",
    "global solutions", "resource group",
]

STAFFING_NAME_FRAGMENTS = [
    "cognizant", "wipro", "tata consultancy", " tcs ", "infosys", "hcl",
    "tech mahindra", "mastech", "kforce", "robert half", "randstad",
    "mindtree", "hexaware", "mphasis", "igate", "patni",
    "syntel", "birlasoft", "niit technologies", "persistent systems",
    "zensar", "ltimindtree", "l&t technology", "coforge",
    "capgemini", "accenture", "virtusa", "conduent",
    "apexon", "softpath", "genesis10", "insight global",
]

SENT_FILE   = BASE_DIR / "sent_emails.json"
CONFIG_FILE = BASE_DIR / "email_config.json"


# ── Startup ───────────────────────────────────────────────────────────────────

def _load_known_consultancies() -> set:
    names: set[str] = set()
    for path in glob.glob(str(BASE_DIR / "Investigation" / "*_Desi_Consultancy.csv")):
        try:
            df = pd.read_csv(path, sep="|", dtype=str, on_bad_lines="skip")
            if "employer_name" in df.columns:
                for name in df["employer_name"].dropna():
                    names.add(name.strip().upper())
        except Exception:
            pass
    return names


KNOWN_CONSULTANCIES = _load_known_consultancies()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_staffing(company: str) -> bool:
    if not company:
        return False
    upper = company.strip().upper()
    if upper in KNOWN_CONSULTANCIES:
        return True
    lower = company.lower()
    for kw in STAFFING_KEYWORDS:
        if kw in lower:
            return True
    for frag in STAFFING_NAME_FRAGMENTS:
        if frag in lower:
            return True
    return False


def _already_sent(email: str) -> bool:
    if not SENT_FILE.exists():
        return False
    try:
        with open(SENT_FILE) as f:
            return email.lower() in json.load(f)
    except Exception:
        return False


def _record_sent(email: str, company: str, job_title: str):
    log = {}
    if SENT_FILE.exists():
        try:
            with open(SENT_FILE) as f:
                log = json.load(f)
        except Exception:
            pass
    log[email.lower()] = {
        "email": email,
        "company": company,
        "job_title": job_title,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(SENT_FILE, "w") as f:
        json.dump(log, f, indent=2)


def _state_csv_path(state: str) -> Path | None:
    slug = state.replace(" ", "_") + "_H1B_Jobs"
    folder = BASE_DIR / "H1B_Jobs_By_State"
    for suffix in (".csv", ".csv.zip"):
        p = folder / f"{slug}{suffix}"
        if p.exists():
            return p
    return None


def _load_state_df(state: str) -> pd.DataFrame | None:
    path = _state_csv_path(state)
    if path is None:
        return None
    try:
        if path.suffix == ".zip":
            with zipfile.ZipFile(path) as zf:
                csv_name = next(n for n in zf.namelist() if n.endswith(".csv"))
                with zf.open(csv_name) as f:
                    return pd.read_csv(f, sep="|", dtype=str, on_bad_lines="skip")
        return pd.read_csv(path, sep="|", dtype=str, on_bad_lines="skip")
    except Exception:
        return None


def _detect_level(title: str) -> str:
    t = (title or "").lower()
    if any(w in t for w in ["senior", "sr.", " sr ", "lead", "principal", "staff", "architect", "director", "manager"]):
        return "senior"
    if any(w in t for w in ["junior", "jr.", " jr ", "associate", "entry", " i "]):
        return "entry"
    if any(w in t for w in ["mid", "intermediate", " ii "]):
        return "mid"
    return "mid"


def _role_matches(title: str, soc: str, role: str, all_roles: bool) -> bool:
    tl = (title or "").lower()
    if not all_roles:
        return any(kw in tl for kw in ROLE_GROUPS.get(role, []))
    for kws in ROLE_GROUPS.values():
        if any(kw in tl for kw in kws):
            return True
    prefix = (soc or "")[:7]
    for socs in SOC_FALLBACK.values():
        if any(prefix.startswith(s) for s in socs):
            return True
    return False


def _available_states() -> list[str]:
    folder = BASE_DIR / "H1B_Jobs_By_State"
    seen: set[str] = set()
    for p in folder.iterdir():
        for suffix in ("_H1B_Jobs.csv", "_H1B_Jobs.csv.zip"):
            if p.name.endswith(suffix):
                seen.add(p.name[: -len(suffix)].replace("_", " "))
    return sorted(seen)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/states")
def api_states():
    return jsonify(_available_states())


@app.route("/api/roles")
def api_roles():
    return jsonify(["All Relevant Roles"] + list(ROLE_GROUPS.keys()))


@app.route("/api/jobs", methods=["POST"])
def api_jobs():
    body     = request.get_json()
    state    = body.get("state", "")
    role     = body.get("role", "")
    level    = body.get("level", "all")
    keyword  = (body.get("keyword") or "").lower().strip()
    page     = max(1, int(body.get("page", 1)))
    per_page = 50

    df = _load_state_df(state)
    if df is None:
        return jsonify({"error": f"No data for {state}"}), 404

    df.columns = [c.strip().lower() for c in df.columns]

    # deduplicate employer_name column (appears twice in source)
    if "employer_name.1" in df.columns:
        df = df.drop(columns=["employer_name.1"])

    # require email
    df = df[df["employer_poc_email"].notna() & (df["employer_poc_email"].str.strip() != "")]

    # drop immigration / lca inboxes
    em = df["employer_poc_email"].str.lower()
    df = df[~(em.str.contains("immigration", na=False) | em.str.contains(r"\blca\b", na=False, regex=True))]

    # drop staffing / consulting
    df = df[~df["employer_name"].apply(lambda x: _is_staffing(str(x)))]

    # role filter
    all_roles = (not role or role == "All Relevant Roles")
    df = df[df.apply(
        lambda r: _role_matches(
            str(r.get("job_title", "")),
            str(r.get("soc_code", "")),
            role,
            all_roles,
        ),
        axis=1,
    )]

    # free-text keyword
    if keyword:
        df = df[
            df["job_title"].str.lower().str.contains(keyword, na=False)
            | df["employer_name"].str.lower().str.contains(keyword, na=False)
            | df["worksite_city"].str.lower().str.contains(keyword, na=False)
        ]

    # experience level
    if level and level != "all":
        df = df[df["job_title"].apply(lambda t: _detect_level(str(t))) == level]

    total   = len(df)
    start   = (page - 1) * per_page
    page_df = df.iloc[start : start + per_page]

    rows = []
    for _, r in page_df.iterrows():
        email = str(r.get("employer_poc_email", "")).strip()
        rows.append({
            "job_title":      str(r.get("job_title", "")),
            "employer_name":  str(r.get("employer_name", "")),
            "worksite_city":  str(r.get("worksite_city", "")),
            "employer_state": str(r.get("employer_state", "")),
            "poc_first":      str(r.get("employer_poc_first_name", "")),
            "poc_last":       str(r.get("employer_poc_last_name", "")),
            "email":          email,
            "phone":          str(r.get("employer_poc_phone", "")),
            "h1b_dependent":  str(r.get("h_1b_dependent", "")),
            "soc_code":       str(r.get("soc_code", "")),
            "level":          _detect_level(str(r.get("job_title", ""))),
            "already_sent":   _already_sent(email),
        })

    return jsonify({"total": total, "page": page, "per_page": per_page, "rows": rows})


@app.route("/api/send-email", methods=["POST"])
def api_send_email():
    body        = request.get_json()
    to_email    = (body.get("email") or "").strip()
    company     = body.get("company", "")
    job_title   = body.get("job_title", "")
    subject     = body.get("subject", "")
    html_body   = body.get("body", "")
    resume_path = body.get("resume_path", "")

    if not to_email:
        return jsonify({"status": "error", "reason": "no email address"}), 400

    if _already_sent(to_email):
        return jsonify({"status": "skipped", "reason": "already sent"})

    cfg = {}
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                cfg = json.load(f)
        except Exception:
            pass

    from_email = cfg.get("from_email", "")
    smtp_host  = cfg.get("smtp_host", "smtp.gmail.com")
    smtp_port  = int(cfg.get("smtp_port", 587))
    username   = cfg.get("username", "")
    password   = cfg.get("password", "")
    if not resume_path:
        resume_path = cfg.get("resume_path", "")

    if not (from_email and username and password):
        return jsonify({"status": "error", "reason": "SMTP not configured"}), 400

    msg = MIMEMultipart("mixed")
    msg["From"]    = from_email
    msg["To"]      = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

    if resume_path and os.path.isfile(resume_path):
        with open(resume_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f'attachment; filename="{os.path.basename(resume_path)}"',
        )
        msg.attach(part)

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(username, password)
            smtp.sendmail(from_email, to_email, msg.as_string())
        _record_sent(to_email, company, job_title)
        return jsonify({"status": "sent"})
    except Exception as e:
        return jsonify({"status": "error", "reason": str(e)}), 500


@app.route("/api/sent")
def api_sent():
    if not SENT_FILE.exists():
        return jsonify({})
    try:
        with open(SENT_FILE) as f:
            return jsonify(json.load(f))
    except Exception:
        return jsonify({})


@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    if request.method == "POST":
        cfg = request.get_json() or {}
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
        return jsonify({"status": "saved"})
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                cfg = json.load(f)
            safe = {k: v for k, v in cfg.items() if k != "password"}
            safe["password"] = ""
            return jsonify(safe)
        except Exception:
            pass
    return jsonify({})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
