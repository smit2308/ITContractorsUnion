# Welcome To The IT Contractors Union GitHub Site 🇺🇸

## H1B Job Mailer — Local Web App

A local web app built on top of this repo's H1B LCA data. It filters active job postings by state, role, and experience level, then lets you send personalized cold emails with your resume directly to hiring managers — no recruiters, no job boards.

### Quick Start

```bash
pip install flask pandas werkzeug
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000)

### Features

- **Filter by state, role, and experience level** — pulls from the LCA CSV files in this repo
- **Smart filtering** — drops staffing/consulting firms, immigration inboxes, and duplicate contacts automatically
- **Personalized emails** — template variables: `{name}`, `{company}`, `{role_noun}`, `{role_area}`, `{experience_blurb}`, `{your_name}`, `{your_phone}`, `{your_linkedin}`
- **Template presets** — save multiple named templates and switch between them
- **Resume manager** — upload PDFs, pick the active one; it attaches automatically on send
- **Duplicate detection** — in-page visual dedup + cross-session tracking via `sent_emails.json`
- **Bulk send** — select multiple rows and send in one click
- **All data persists** — sent log, SMTP config, resumes, and templates all survive restarts

### Setup

1. **SMTP Config** — click ⚙ SMTP Config in the header
   - Use your Gmail address + a [Google App Password](https://myaccount.google.com/apppasswords) (requires 2FA)
   - Fill in Your Name, Phone, and LinkedIn for the email signature
2. **Resume** — click Manage in the header → upload a PDF → it becomes the active resume
3. **Template** — click Edit Template to customize the subject and body, or create presets for different tones

### Data

State CSVs live in `H1B_Jobs_By_State/`. To get updated data, sync from upstream:

```bash
git fetch upstream
git merge upstream/Main
```

Or download directly from the [DOL Foreign Labor Performance Data](https://www.dol.gov/agencies/eta/foreign-labor/performance) page.

### Local data files (gitignored)

| File | Contents |
|---|---|
| `email_config.json` | SMTP settings + sender profile |
| `sent_emails.json` | Log of every address emailed |
| `resumes/` + `resumes.json` | Uploaded resume PDFs |
| `templates.json` | Saved email template presets |

---

## HOW TO GET DIRECT TO HIRING MANAGERS (Manual Method)

1. Download the data files from this repo, or the original location here: https://www.dol.gov/agencies/eta/foreign-labor/performance
2. Load them up in a spreadsheet or database.
3. Use the contact info in the files to contact the employer.
4. Request Copies of their LCAs.
5. The Hiring Manager's name will be in Section J of the LCA form. See the form here: https://flag.dol.gov/sites/default/files/2019-09/ETA_Form_9035.pdf

Notes:
1. When an employer files an LCA, they are required by Law (8 U.S.C. 1182, 20 CFR 655), to make the LCAs available to the Public.
2. You may have to actually travel to the worksite to view the LCAs. Focus on employers within your "ordinary commute distance".
3. Some employers will publish LCAs on their website. Try looking at their "Careers" page, or for "Compliance" or "Immigration" pages.
4. You may be able to obtain copies of the LCAs by email from the **Employer Point Of Contact** that is contained in the data files.
5. You can also send mail to the hiring manager, by addressing it to "Hiring Manager, LCA #...". It should get directly to them.

### Stop Wasting Your Time With Fake Recruiters And Worthless Jobs Websites!
### Stop Being Scammed With Ghost Jobs, And Phony Offers!
### Get Rid Of All The Third-Party And Fourth Party Deals!

### Become A Member Of The IT Contractors Union Today!
