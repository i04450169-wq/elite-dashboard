import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
# مفتاح تشفير الجلسات (غيره في Render)
app.secret_key = os.getenv("SECRET_KEY", "elite-super-secret-key-2026")

# مسار قاعدة البيانات (لو هترفع على Render هتغيره في المتغيرات)
DB_PATH = os.getenv("DB_PATH", "admin_bot.sqlite3")

# بيانات الدخول للوحة (يفضل تغييرها في متغيرات البيئة)
DASHBOARD_USER = os.getenv("DASH_USER", "admin")
DASHBOARD_PASS_HASH = generate_password_hash(os.getenv("DASH_PASS", "elite2026"))

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ─── تسجيل الدخول ───
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if username == DASHBOARD_USER and check_password_hash(DASHBOARD_PASS_HASH, password):
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        else:
            flash("اسم المستخدم أو كلمة المرور غير صحيحة", "danger")
            
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))

# ─── الصفحة الرئيسية (محمية) ───
@app.route("/")
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    
    stats = {
        "users": 0, "lessons": 0, "questions": 0, "tickets": 0
    }
    recent_activity = []
    
    try:
        with closing(get_db()) as conn:
            # إحصائيات سريعة
            stats["users"] = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            stats["lessons"] = conn.execute("SELECT COUNT(*) FROM study_lessons").fetchone()[0]
            stats["questions"] = conn.execute("SELECT COUNT(*) FROM study_questions").fetchone()[0]
            stats["tickets"] = conn.execute("SELECT COUNT(*) FROM support_tickets WHERE status='open'").fetchone()[0]
            
            # آخر 15 حدث في البوت (سجل النشاط)
            rows = conn.execute(
                "SELECT actor_id, action, details, created_at FROM audit_log ORDER BY id DESC LIMIT 15"
            ).fetchall()
            recent_activity = [dict(r) for r in rows]
    except Exception as e:
        flash(f"مشكلة في قراءة قاعدة البيانات: {str(e)}", "warning")
        
    return render_template("dashboard.html", stats=stats, activity=recent_activity)

# ─── API للتحديث التلقائي (AJAX) ───
@app.route("/api/stats")
def api_stats():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
        
    stats = {"users": 0, "activity": []}
    try:
        with closing(get_db()) as conn:
            stats["users"] = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            rows = conn.execute("SELECT actor_id, action, created_at FROM audit_log ORDER BY id DESC LIMIT 10").fetchall()
            stats["activity"] = [dict(r) for r in rows]
    except:
        pass
    return jsonify(stats)

if __name__ == "__main__":
    # تشغيل محلي
    app.run(debug=True, host="0.0.0.0", port=5000)