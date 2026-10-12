# Rotaract Club of SIMS website

A Flask starter website for the Rotaract Club of SIMS, Soundarya Institute of Management & Science, RY 2026–27, RID 3192.

## Features in this starter
- Public home, about, projects, events and gallery pages
- Membership application form
- Club collaboration request form
- Admin login and dashboard
- Admin can publish events/projects, review request statuses, add gallery links and register certificate verification codes
- Certificate code lookup page
- CSRF protection and password hashing

## Run locally
1. Install Python 3.11+.
2. Create a virtual environment:
   - macOS/Linux: `python -m venv .venv && source .venv/bin/activate`
   - Windows: `python -m venv .venv && .venv\\Scripts\\activate`
3. Install dependencies: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env`; set a strong `SECRET_KEY` and `ADMIN_PASSWORD`.
5. Run `python app.py`.
6. Visit `http://127.0.0.1:5000`.

The initial admin username/password default to `admin` / `ChangeMe123!` only if environment variables are not set. Change these immediately and never deploy with defaults.

## Routes
- `/` public home
- `/about`, `/projects`, `/events`, `/gallery`
- `/join` membership form
- `/collaborate` club collaboration request form
- `/certificate?code=SIMS-EXAMPLE-001` certificate verification
- `/admin/login` and `/admin` private admin panel

## Before public launch
- Set a long random `SECRET_KEY` and strong admin credentials.
- Use PostgreSQL or another persistent managed database for production.
- Use hosted object/image storage for gallery photos. Do not rely on local disk on ephemeral hosts.
- Add rate limiting, backups, privacy notice, retention policy and contact consent.
- Add proper certificate PDF generation and authenticated download only after certificate design and authorization rules are confirmed.
- Add email notifications, password reset and audit logs before broader rollout.
- Review student-data handling with college management and collect only necessary information.
- Replace sample content with confirmed dates, verified project outcomes, approved logo and official contact details.
- Keep debug mode disabled in production.

## Free-tier hosting outline
1. Push the project to a private or public Git repository.
2. Create a web service at a provider with a currently available free tier.
3. Configure build/install command: `pip install -r requirements.txt`.
4. Configure start command: `gunicorn app:app`.
5. Add environment variables `SECRET_KEY`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, and the provider's PostgreSQL `DATABASE_URL`.
6. Add hosted image storage credentials if integrating a provider.
7. Test forms, login, mobile layout, and database persistence after deploy.

Free-tier features and limits change; confirm the provider's current terms before choosing it.


### Board of Directors page
The public `/board` page lists the 26 RY 2026–27 board members and includes a searchable directory, ASTHRA logo, and President profile. Review names/designations with club leadership before launch.
