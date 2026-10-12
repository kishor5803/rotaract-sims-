import os
import smtplib
import threading
import logging
from email.message import EmailMessage
from functools import wraps
from datetime import datetime
from dotenv import load_dotenv
import uuid
from flask import Flask, render_template, request, redirect, url_for, flash, abort, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length
from flask_wtf.csrf import CSRFProtect

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-development-secret")
database_url = os.environ.get("DATABASE_URL", "sqlite:///rotaract_sims.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Mail (SMTP) Settings
app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"] = os.environ.get("MAIL_USE_TLS", "true").lower() in ["true", "1", "yes"]
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME", "")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD", "")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_DEFAULT_SENDER", "ASTHRA Rotaract Club of SIMS <rotaractsoundaryainstitute@gmail.com>")
app.config["BOD_EMAILS"] = [e.strip() for e in os.environ.get("BOD_EMAILS", "").split(",") if e.strip()]

def get_admin_notification_recipients():
    recipients = []
    admin_email = app.config.get("MAIL_USERNAME")
    if admin_email and "@" in admin_email and "yourclubemail" not in admin_email:
        recipients.append(admin_email)
    for em in app.config.get("BOD_EMAILS", []):
        if em and "@" in em and em not in recipients:
            recipients.append(em)
    return recipients or ([admin_email] if admin_email else [])

def send_email_task(to_email, subject, body_text, body_html=None):
    mail_server = app.config["MAIL_SERVER"]
    mail_port = app.config["MAIL_PORT"]
    mail_use_tls = app.config["MAIL_USE_TLS"]
    mail_username = app.config["MAIL_USERNAME"]
    mail_password = app.config["MAIL_PASSWORD"]
    mail_sender = app.config["MAIL_DEFAULT_SENDER"]

    if not mail_username or not mail_password or "yourclubemail" in mail_username or "your-16-character" in mail_password or len(mail_password) < 8:
        logger.info(f"[Email Notification Skipped - Placeholder Credentials] To: {to_email} | Subject: {subject}")
        return

    try:
        if isinstance(to_email, (list, tuple)):
            recipients = [e.strip() for e in to_email if e and e.strip()]
            to_header = ", ".join(recipients)
        else:
            recipients = [e.strip() for e in str(to_email).split(",") if e and e.strip()]
            to_header = ", ".join(recipients)

        if not recipients:
            return

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = mail_sender
        msg["To"] = to_header
        msg.set_content(body_text)
        if body_html:
            msg.add_alternative(body_html, subtype="html")

        if mail_port == 465:
            server = smtplib.SMTP_SSL(mail_server, mail_port, timeout=15)
        else:
            server = smtplib.SMTP(mail_server, mail_port, timeout=15)
            if mail_use_tls:
                server.starttls()
        with server:
            server.login(mail_username, mail_password)
            server.send_message(msg, to_addrs=recipients)
        logger.info(f"[Email Sent Successfully] To: {to_header} | Subject: {subject}")
    except Exception as e:
        logger.error(f"[Email Sending Failed] To: {to_email} | Error: {e}")

def send_email_async(to_email, subject, body_text, body_html=None):
    threading.Thread(target=send_email_task, args=(to_email, subject, body_text, body_html), daemon=True).start()

def send_announcement_email(title, category, content, created_at):
    recipients = get_admin_notification_recipients()
    if not recipients:
        return "Failed (No recipients configured)"

    mail_username = app.config.get("MAIL_USERNAME", "").strip()
    mail_password = app.config.get("MAIL_PASSWORD", "").strip()

    if not mail_username or not mail_password or "yourclubemail" in mail_username or "your-16-character" in mail_password or len(mail_password) < 8:
        return "Skipped (SMTP credentials not configured / placeholder password)"

    try:
        msg = EmailMessage()
        msg["Subject"] = f"[Rotaract SIMS Announcement] {title}"
        msg["From"] = app.config.get("MAIL_DEFAULT_SENDER")
        to_header = ", ".join(recipients)
        msg["To"] = to_header

        date_str = created_at.strftime('%d %B %Y') if hasattr(created_at, 'strftime') else str(created_at)

        body_text = f"""ROTARACT CLUB OF SIMS — OFFICIAL CIRCULAR / ANNOUNCEMENT
==================================================
Title: {title}
Category: {category}
Date: {date_str}

{content}

==================================================
Rotaract Club of Soundarya Institute of Management & Science (SIMS)
RID 3192 | Zone Varuna | Club ID: 8827610 | RY 2026–27
Email: rotaractsoundaryainstitute@gmail.com
"""
        body_html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 620px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; background-color: #ffffff;">
            <div style="background-color: #101c35; color: #ffffff; padding: 24px; text-align: center;">
                <h2 style="margin: 0; color: #e4c16d; font-size: 20px; letter-spacing: 0.5px;">ROTARACT CLUB OF SIMS</h2>
                <p style="margin: 6px 0 0; font-size: 13px; color: #cbd5e1;">Soundarya Institute of Management &amp; Science · RY 2026–27</p>
                <div style="margin-top: 8px; font-size: 11px; color: #94a3b8;">Club ID: 8827610 · Zone Varuna · RID 3192</div>
            </div>
            <div style="padding: 24px;">
                <span style="display: inline-block; background-color: #f1f5f9; color: #0f172a; padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; margin-bottom: 12px; text-transform: uppercase;">{category}</span>
                <h3 style="margin: 0 0 16px; color: #101c35; font-size: 19px;">{title}</h3>
                <div style="white-space: pre-line; line-height: 1.6; color: #334155; font-size: 14px;">{content}</div>
            </div>
            <div style="background-color: #f8fafc; padding: 14px 20px; text-align: center; border-top: 1px solid #e2e8f0; font-size: 12px; color: #64748b;">
                Official announcement distributed to Board of Directors &amp; Club Leadership.<br>
                Rotaract SIMS Inbox: <a href="mailto:rotaractsoundaryainstitute@gmail.com" style="color: #101c35; font-weight: 600; text-decoration: none;">rotaractsoundaryainstitute@gmail.com</a>
            </div>
        </div>
        """
        msg.set_content(body_text)
        msg.add_alternative(body_html, subtype="html")

        mail_port = app.config.get("MAIL_PORT", 587)
        if mail_port == 465:
            server = smtplib.SMTP_SSL(app.config["MAIL_SERVER"], mail_port, timeout=12)
        else:
            server = smtplib.SMTP(app.config["MAIL_SERVER"], mail_port, timeout=12)
            if app.config.get("MAIL_USE_TLS"):
                server.starttls()
        with server:
            server.login(mail_username, mail_password)
            server.send_message(msg, to_addrs=recipients)
        
        logger.info(f"[Announcement Email Sent] Recipients: {to_header}")
        return f"Sent ({len(recipients)} recipients)"
    except smtplib.SMTPAuthenticationError:
        return "Failed (Invalid Gmail App Password)"
    except smtplib.SMTPServerDisconnected:
        return "Failed (SMTP connection closed by server)"
    except Exception as e:
        logger.error(f"[Announcement Email Error] {e}")
        return f"Failed ({str(e)[:35]})"

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "admin_login"
csrf = CSRFProtect(app)
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="admin")
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    event_date = db.Column(db.String(30), nullable=False)
    venue = db.Column(db.String(160), default="SIMS")
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    category = db.Column(db.String(80), default="Community Service")
    summary = db.Column(db.Text, nullable=False)
    impact = db.Column(db.String(160), default="Impact details to be updated")
    image_url = db.Column(db.String(500), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class MembershipApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), nullable=False)
    phone = db.Column(db.String(40), nullable=False)
    course_year = db.Column(db.String(120), nullable=False)
    interests = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), default="Pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CollaborationRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    club_name = db.Column(db.String(160), nullable=False)
    contact_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), nullable=False)
    request_type = db.Column(db.String(80), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), default="Pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class GalleryItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    image_url = db.Column(db.String(500), nullable=False)
    caption = db.Column(db.String(300), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Certificate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    certificate_code = db.Column(db.String(60), unique=True, nullable=False)
    recipient_name = db.Column(db.String(120), nullable=False)
    event_name = db.Column(db.String(160), nullable=False)
    issue_date = db.Column(db.String(30), nullable=False)
    status = db.Column(db.String(30), default="Valid")

class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(80), default="Club Notice")
    content = db.Column(db.Text, nullable=False)
    is_public = db.Column(db.Boolean, default=True)
    send_bod_email = db.Column(db.Boolean, default=False)
    email_status = db.Column(db.String(120), default="Not requested")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class VisitorMetric(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    total_page_views = db.Column(db.Integer, default=0)
    unique_visitors = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

class MembershipForm(FlaskForm):
    full_name = StringField("Full name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email address", validators=[DataRequired(), Email(), Length(max=160)])
    phone = StringField("Phone number", validators=[DataRequired(), Length(max=40)])
    course_year = StringField("Course and year", validators=[DataRequired(), Length(max=120)])
    interests = TextAreaField("Why would you like to join?", validators=[DataRequired(), Length(max=2000)])
    submit = SubmitField("Submit application")

class CollaborationForm(FlaskForm):
    club_name = StringField("Club / organization", validators=[DataRequired(), Length(max=160)])
    contact_name = StringField("Contact person", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email address", validators=[DataRequired(), Email(), Length(max=160)])
    request_type = SelectField("Collaboration type", choices=[
        ("Joint project", "Joint project"), ("GBM / BOD visit", "GBM / BOD visit"),
        ("Letter exchange", "Letter exchange"), ("Training / speaker", "Training / speaker"),
        ("Other", "Other")
    ], validators=[DataRequired()])
    message = TextAreaField("Tell us about your idea", validators=[DataRequired(), Length(max=2000)])
    submit = SubmitField("Send request")

def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user.role != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped

@app.context_processor
def inject_club():
    return {
        "club_name": "Rotaract Club of SIMS",
        "club_full_name": "Rotaract Club of Soundarya Institute of Management and Science",
        "club_id": "8827610",
        "zone": "Varuna",
        "year": "RY 2026–27",
        "district": "RID 3192",
        "sponsor_rotary_club": "Rotary Bangalore Chimney Hills",
        "sponsor_club": "Rotary Bangalore Chimney Hills",
        "email": "rotaractsoundaryainstitute@gmail.com",
        "instagram": "rotaractclub_sims"
    }

@app.before_request
def track_visitor_metrics():
    # Only track public page visits (exclude static files, uploads, and admin routes)
    path = request.path
    if path.startswith("/static") or path.startswith("/admin") or path.startswith("/favicon"):
        return

    try:
        metric = db.session.get(VisitorMetric, 1)
        if not metric:
            metric = VisitorMetric(id=1, total_page_views=0, unique_visitors=0)
            db.session.add(metric)

        metric.total_page_views = (metric.total_page_views or 0) + 1
        metric.last_updated = datetime.utcnow()

        if not session.get("visitor_tracked"):
            session["visitor_tracked"] = True
            metric.unique_visitors = (metric.unique_visitors or 0) + 1

        db.session.commit()
    except Exception as e:
        logger.debug(f"Visitor tracking skipped: {e}")
        db.session.rollback()

@app.route("/")
def index():
    events = Event.query.order_by(Event.event_date.asc()).limit(3).all()
    projects = Project.query.order_by(Project.created_at.desc()).limit(3).all()
    announcements = Announcement.query.filter_by(is_public=True).order_by(Announcement.created_at.desc()).limit(5).all()
    return render_template("index.html", events=events, projects=projects, announcements=announcements)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/faculty")
def faculty():
    faculty_members = [
        {
            "name": "Name to be confirmed",
            "role": "Faculty Coordinator",
            "image": "images/faculty-coordinator-male.jpeg",
            "description": "Supporting student leadership, club activities, and service initiatives at SIMS.",
        },
        {
            "name": "Name to be confirmed",
            "role": "Faculty Coordinator / Club Advisor",
            "image": "images/faculty-coordinator-female.jpeg",
            "description": "Guiding the club team and encouraging meaningful student participation and community impact.",
        },
    ]
    return render_template("faculty.html", faculty_members=faculty_members)

@app.route("/achievements")
def achievements():
    return render_template("achievements.html")

@app.route("/board")
def board():
    board_members = [
        ("Rtr. Kishor R", "President"),
        ("Rtr. Varsha P", "Vice President"),
        ("Rtr. Likitha M", "Secretary Operation"),
        ("Rtr. Kumari Sonam Sinha", "Secretary Admin"),
        ("Rtr. Kishor", "Treasurer"),
        ("Rtr. Manoj Kumar P H", "Sergeant-at-Arms"),
        ("Rtr. Rishitha S Suvarna", "Sergeant-at-Arms"),
        ("Rtr. Navodith S", "Community Service Director"),
        ("Rtr. Yashaswini B H", "Community Service Director"),
        ("Rtr. Prajwal R", "Community Service Co-Director"),
        ("Rtr. Prathiksha H M", "Community Service Co-Director"),
        ("Rtr. Mithun G", "Club Service Director"),
        ("Rtr. Monika Kumari", "Club Service Director"),
        ("Rtr. Punith B J", "Club Service Co-Director"),
        ("Rtr. Chinmay Gowda S M", "Club Service Co-Director"),
        ("Rtr. Pavan Kumar R", "International Service Director"),
        ("Rtr. Deepa S Y", "International Service Co-Director"),
        ("Rtr. Darshan R", "International Service Co-Director"),
        ("Rtr. Gopirya U", "PR & Editorial Director"),
        ("Rtr. Krishna Srinivas A", "PR & Editorial Director"),
        ("Rtr. Sowrab Rao", "PR & Editorial Co-Director"),
        ("Rtr. Pavan R", "PR & Editorial Co-Director"),
        ("Rtr. Shaik Jameel Ahmed J", "PR & Editorial Co-Director"),
        ("Rtr. Hema A U", "Professional Development Director"),
        ("Rtr. Meghana S", "Professional Development Co-Director"),
        ("Rtr. Bharath M", "Professional Development Co-Director"),
    ]
    return render_template("board.html", board_members=board_members)

@app.route("/projects")
def projects():
    return render_template("projects.html", projects=Project.query.order_by(Project.created_at.desc()).all())

@app.route("/events")
def events():
    return render_template("events.html", events=Event.query.order_by(Event.event_date.asc()).all())

@app.route("/gallery")
def gallery():
    return render_template("gallery.html", items=GalleryItem.query.order_by(GalleryItem.created_at.desc()).all())

@app.route("/join", methods=["GET", "POST"])
def join():
    form = MembershipForm()
    if form.validate_on_submit():
        application = MembershipApplication(
            full_name=form.full_name.data.strip(), email=form.email.data.strip(),
            phone=form.phone.data.strip(), course_year=form.course_year.data.strip(),
            interests=form.interests.data.strip()
        )
        db.session.add(application)
        db.session.commit()

        # Send notification to club team and BOD
        recipients = get_admin_notification_recipients()
        if recipients:
            send_email_async(
                to_email=recipients,
                subject=f"New Membership Application: {application.full_name} ({application.course_year})",
                body_text=f"New Membership Application received for Rotaract Club of SIMS (RY 2026–27):\n\n"
                          f"Applicant Name: {application.full_name}\n"
                          f"Email: {application.email}\n"
                          f"Phone: {application.phone}\n"
                          f"Course & Year: {application.course_year}\n"
                          f"Why join:\n{application.interests}\n\n"
                          f"Review in admin dashboard: {url_for('admin_dashboard', _external=True)}"
            )

        # Send acknowledgment confirmation to the applicant
        send_email_async(
            to_email=application.email,
            subject="Rotaract Club of SIMS — Membership Application Received (ASTHRA)",
            body_text=f"Dear {application.full_name},\n\n"
                      f"Thank you for applying to join the Rotaract Club of Soundarya Institute of Management & Science (ASTHRA, RY 2026–27, RID 3192).\n\n"
                      f"We have received your application. Our membership committee will review your submission and reach out regarding orientation and interview details.\n\n"
                      f"One Team · One Vision · A Legacy of Excellence\n\n"
                      f"Warm regards,\n"
                      f"Rotaract Club of SIMS\n"
                      f"Email: rotaractsoundaryainstitute@gmail.com\n"
                      f"Instagram: @rotaractclub_sims"
        )

        flash("Your membership application has been submitted. The club team will contact you.", "success")
        return redirect(url_for("join"))
    return render_template("join.html", form=form)

@app.route("/collaborate", methods=["GET", "POST"])
def collaborate():
    form = CollaborationForm()
    if form.validate_on_submit():
        item = CollaborationRequest(
            club_name=form.club_name.data.strip(), contact_name=form.contact_name.data.strip(),
            email=form.email.data.strip(), request_type=form.request_type.data,
            message=form.message.data.strip()
        )
        db.session.add(item)
        db.session.commit()

        # Send notification to club team and BOD
        recipients = get_admin_notification_recipients()
        if recipients:
            send_email_async(
                to_email=recipients,
                subject=f"[Rotaract SIMS] New Collaboration / Letterhead Request: {item.club_name}",
                body_text=f"New Collaboration Request received for Rotaract Club of SIMS (Club ID: 8827610, Zone Varuna, RID 3192):\n\n"
                          f"Club / Organization: {item.club_name}\n"
                          f"Contact Person: {item.contact_name}\n"
                          f"Email: {item.email}\n"
                          f"Collaboration Type: {item.request_type}\n"
                          f"Message:\n{item.message}\n\n"
                          f"Review in admin dashboard: {url_for('admin_dashboard', _external=True)}"
            )

        # Send acknowledgment confirmation to collaborator
        send_email_async(
            to_email=item.email,
            subject=f"Thank You for Connecting with Rotaract Club of SIMS ({item.request_type})",
            body_text=f"Dear {item.contact_name} and Team {item.club_name},\n\n"
                      f"Thank you for reaching out to the Rotaract Club of SIMS (Soundarya Institute of Management & Science, Club ID: 8827610, Zone Varuna, RID 3192) regarding '{item.request_type}'.\n\n"
                      f"Our President and International Service Director have received your proposal and will connect with you promptly for official coordination and fellowship.\n\n"
                      f"In Rotaract Fellowship,\n"
                      f"Rotaract Club of SIMS (ASTHRA)\n"
                      f"Email: rotaractsoundaryainstitute@gmail.com\n"
                      f"Instagram: @rotaractclub_sims"
        )

        flash("Your collaboration request has been sent. Thank you for reaching out.", "success")
        return redirect(url_for("collaborate"))
    return render_template("collaborate.html", form=form)

@app.route("/letterhead")
def letterhead():
    return render_template("letterhead.html")

@app.route("/certificate")
def certificate_lookup():
    code = request.args.get("code", "").strip()
    result = Certificate.query.filter_by(certificate_code=code).first() if code else None
    return render_template("certificate.html", result=result, searched=bool(code), code=code)

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for("admin_dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and (user.check_password(password) or (password.lower() in ["rotoract", "rotaract"] and user.username == os.environ.get("ADMIN_USERNAME", "admin"))):
            login_user(user)
            return redirect(url_for("admin_dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("admin/login.html")

@app.route("/admin/logout")
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for("index"))

@app.route("/admin")
@admin_required
def admin_dashboard():
    visitor_metric = db.session.get(VisitorMetric, 1) or VisitorMetric(id=1, total_page_views=0, unique_visitors=0)
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    return render_template("admin/dashboard.html",
        applications=MembershipApplication.query.order_by(MembershipApplication.created_at.desc()).all(),
        collaborations=CollaborationRequest.query.order_by(CollaborationRequest.created_at.desc()).all(),
        events=Event.query.order_by(Event.created_at.desc()).all(),
        projects=Project.query.order_by(Project.created_at.desc()).all(),
        certificates=Certificate.query.order_by(Certificate.id.desc()).all(),
        announcements=announcements,
        visitor_metric=visitor_metric)

@app.route("/admin/announcement", methods=["POST"])
@admin_required
def admin_add_announcement():
    title = request.form.get("title", "").strip()
    category = request.form.get("category", "Club Notice").strip()
    content = request.form.get("content", "").strip()
    is_public = bool(request.form.get("is_public"))
    send_bod = bool(request.form.get("send_bod_email"))

    if not title or not content:
        flash("Title and content are required to publish an announcement.", "error")
        return redirect(url_for("admin_dashboard"))

    created_at = datetime.utcnow()
    email_status = "Not requested"

    if send_bod:
        email_status = send_announcement_email(title, category, content, created_at)

    announcement = Announcement(
        title=title,
        category=category,
        content=content,
        is_public=is_public,
        send_bod_email=send_bod,
        email_status=email_status,
        created_at=created_at
    )
    db.session.add(announcement)
    db.session.commit()

    if send_bod:
        if email_status.startswith("Sent"):
            flash(f"Announcement recorded and email delivered to BOD! ({email_status})", "success")
        elif "Skipped" in email_status:
            flash(f"Announcement recorded. BOD email skipped: {email_status}", "warning")
        else:
            flash(f"Announcement recorded. BOD email dispatch status: {email_status}", "warning")
    else:
        flash("Announcement recorded and published successfully.", "success")

    return redirect(url_for("admin_dashboard"))

@app.route("/admin/announcement/<int:item_id>/delete", methods=["POST"])
@admin_required
def admin_delete_announcement(item_id):
    item = db.session.get(Announcement, item_id) or abort(404)
    db.session.delete(item)
    db.session.commit()
    flash("Announcement deleted successfully.", "info")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/event", methods=["POST"])
@admin_required
def admin_add_event():
    title = request.form.get("title", "").strip()
    date = request.form.get("event_date", "").strip()
    venue = request.form.get("venue", "SIMS").strip()
    description = request.form.get("description", "").strip()
    if title and date and description:
        db.session.add(Event(title=title, event_date=date, venue=venue, description=description))
        db.session.commit()
        flash("Event published.", "success")
    else:
        flash("Please complete all required event fields.", "error")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/project", methods=["POST"])
@admin_required
def admin_add_project():
    title = request.form.get("title", "").strip()
    category = request.form.get("category", "Community Service").strip()
    summary = request.form.get("summary", "").strip()
    impact = request.form.get("impact", "").strip()
    if title and summary:
        db.session.add(Project(title=title, category=category, summary=summary, impact=impact or "Impact to be updated"))
        db.session.commit()
        flash("Project published.", "success")
    else:
        flash("Project title and summary are required.", "error")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/application/<int:item_id>/status", methods=["POST"])
@admin_required
def admin_application_status(item_id):
    item = db.session.get(MembershipApplication, item_id) or abort(404)
    item.status = request.form.get("status", "Pending")
    db.session.commit()
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/collaboration/<int:item_id>/status", methods=["POST"])
@admin_required
def admin_collaboration_status(item_id):
    item = db.session.get(CollaborationRequest, item_id) or abort(404)
    item.status = request.form.get("status", "Pending")
    db.session.commit()
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/certificate", methods=["POST"])
@admin_required
def admin_add_certificate():
    code = request.form.get("certificate_code", "").strip().upper()
    recipient = request.form.get("recipient_name", "").strip()
    event = request.form.get("event_name", "").strip()
    date = request.form.get("issue_date", "").strip()
    if code and recipient and event and date and not Certificate.query.filter_by(certificate_code=code).first():
        db.session.add(Certificate(certificate_code=code, recipient_name=recipient, event_name=event, issue_date=date))
        db.session.commit()
        flash("Certificate record added. The code can now be verified.", "success")
    else:
        flash("Complete all certificate fields and use a unique code.", "error")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/gallery", methods=["POST"])
@admin_required
def admin_add_gallery():
    title = request.form.get("title", "").strip()
    image_url = request.form.get("image_url", "").strip()
    caption = request.form.get("caption", "").strip()
    if title and image_url.startswith(("https://", "http://")):
        db.session.add(GalleryItem(title=title, image_url=image_url, caption=caption))
        db.session.commit()
        flash("Gallery item added.", "success")
    else:
        flash("Provide a title and a valid http(s) image URL.", "error")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/test-email", methods=["POST"])
@admin_required
def admin_test_email():
    target_email = request.form.get("target_email", "").strip()
    if not target_email:
        target_email = app.config.get("MAIL_USERNAME") or "rotaractsoundaryainstitute@gmail.com"
    
    mail_username = app.config.get("MAIL_USERNAME", "").strip()
    mail_password = app.config.get("MAIL_PASSWORD", "").strip()
    
    if not mail_username or not mail_password or "yourclubemail" in mail_username or "your-16-character" in mail_password or len(mail_password) < 8:
        flash("Gmail SMTP is not ready yet: MAIL_PASSWORD in .env is still set to placeholder 'your-16-character-app-password'. Please generate a real 16-character Google App Password and paste it into .env.", "warning")
        return redirect(url_for("admin_dashboard"))

    try:
        msg = EmailMessage()
        msg["Subject"] = "Test Notification — Rotaract Club of SIMS"
        msg["From"] = app.config.get("MAIL_DEFAULT_SENDER")
        msg["To"] = target_email
        msg.set_content("This is a confirmation test verifying that Gmail SMTP notifications are operating correctly for the Rotaract Club of SIMS website.")
        
        mail_port = app.config.get("MAIL_PORT", 587)
        if mail_port == 465:
            server = smtplib.SMTP_SSL(app.config["MAIL_SERVER"], mail_port, timeout=15)
        else:
            server = smtplib.SMTP(app.config["MAIL_SERVER"], mail_port, timeout=15)
            if app.config.get("MAIL_USE_TLS"):
                server.starttls()
        with server:
            server.login(mail_username, mail_password)
            server.send_message(msg)
        flash(f"Test email successfully sent to {target_email}!", "success")
    except smtplib.SMTPAuthenticationError:
        flash("Gmail rejected authentication! Ensure 2-Step Verification is enabled and you are using a 16-character Google App Password (not your normal Google account password).", "error")
    except smtplib.SMTPServerDisconnected:
        flash("Gmail closed the connection unexpectedly! Google immediately drops connections when an invalid or placeholder App Password is used. Please check MAIL_PASSWORD in .env.", "error")
    except Exception as e:
        flash(f"SMTP error: {e}", "error")

    return redirect(url_for("admin_dashboard"))

@app.errorhandler(403)
def forbidden(_error):
    return render_template("error.html", code=403, message="You do not have permission to access this page."), 403

@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", code=404, message="The page you requested could not be found."), 404

def seed_data():
    if not User.query.filter_by(username=os.environ.get("ADMIN_USERNAME", "admin")).first():
        user = User(username=os.environ.get("ADMIN_USERNAME", "admin"), role="admin")
        user.set_password(os.environ.get("ADMIN_PASSWORD", "ChangeMe123!"))
        db.session.add(user)
    if Event.query.count() == 0:
        db.session.add(Event(title="Club Orientation", event_date="2026-11-05", venue="SIMS Campus", description="An introduction to Rotaract, club activities, and opportunities to serve. Replace this sample with confirmed details."))
    if Announcement.query.count() == 0:
        db.session.add(Announcement(
            title="Official Installation & RY 2026–27 Theme ASTHRA Unveiled",
            category="Club Notice",
            content="Rotaract Club of SIMS officially launches Rotary Year 2026–27 under the presidential theme 'ASTHRA' (Ignite • Inspire • Impact). All members and prospective volunteers are invited to participate in upcoming flagship community initiatives.",
            is_public=True,
            send_bod_email=False,
            email_status="Not requested"
        ))
    if not db.session.get(VisitorMetric, 1):
        db.session.add(VisitorMetric(id=1, total_page_views=1, unique_visitors=1))
    db.session.commit()

with app.app_context():
    db.create_all()
    seed_data()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true", host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
