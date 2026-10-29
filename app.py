
from flask import (
    Flask, request, redirect, session,
    render_template_string, flash
)
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import html
import os
import secrets

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
DATABASE = "site.db"


# ==================== قاعدة البيانات ====================

def connect_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with connect_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                bio TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS likes (
                user_id INTEGER NOT NULL,
                post_id INTEGER NOT NULL,
                UNIQUE(user_id, post_id)
            );

            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                post_id INTEGER NOT NULL,
                content TEXT NOT NULL
            );
        """)


# ==================== أدوات مساعدة ====================

def escape_html(value):
    return html.escape(str(value or ""), quote=True)


def create_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(24)
    return session["csrf_token"]


def verify_csrf_token():
    submitted = request.form.get("csrf_token", "")
    saved = session.get("csrf_token", "")
    return bool(
        submitted and saved
        and secrets.compare_digest(submitted, saved)
    )


def csrf_field():
    return (
        '<input type="hidden" name="csrf_token" value="'
        + escape_html(create_csrf_token()) + '">'
    )


def render_page(content):
    messages = [
        escape_html(message)
        for message in __import__(
            "flask"
        ).get_flashed_messages()
    ]

    return render_template_string(
        TEMPLATE,
        content=content,
        messages=messages,
        logged_in=("user_id" in session),
        dark_mode=session.get("dark_mode", False)
    )


# ==================== تصميم الموقع ====================

TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>HICHAM RAH</title>

    <style>
        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            font-family: Tahoma, Arial, sans-serif;
            background: #f1f5f9;
            color: #1e293b;
            line-height: 1.8;
        }

        header {
            background: linear-gradient(135deg, #071952, #088395);
            color: white;
            padding: 35px 15px;
            text-align: center;
        }

        header h1 {
            margin: 0;
            font-size: 36px;
        }

        nav {
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 15px;
            padding: 15px;
            background: white;
        }

        nav a {
            text-decoration: none;
            color: #088395;
            font-weight: bold;
        }

        main {
            width: 94%;
            max-width: 750px;
            margin: 25px auto;
        }

        .card {
            background: white;
            padding: 20px;
            margin-bottom: 18px;
            border-radius: 12px;
            box-shadow: 0 3px 12px #00000010;
            overflow-wrap: anywhere;
        }

        input, textarea {
            width: 100%;
            padding: 12px;
            margin: 8px 0;
            border: 1px solid #cbd5e1;
            border-radius: 7px;
            font-family: inherit;
            font-size: 15px;
        }

        textarea {
            min-height: 100px;
            resize: vertical;
        }

        button {
            padding: 10px 18px;
            border: none;
            border-radius: 7px;
            background: #088395;
            color: white;
            cursor: pointer;
            font-family: inherit;
            font-size: 15px;
        }

        button:hover {
            background: #071952;
        }

        .notice {
            background: #e0f2fe;
            color: #075985;
        }

        hr {
            border: none;
            border-top: 1px solid #e2e8f0;
            margin: 20px 0;
        }

        footer {
            text-align: center;
            padding: 25px;
            color: #64748b;
        }

        body.dark {
            background: #111827;
            color: #f1f5f9;
        }

        body.dark nav,
        body.dark .card {
            background: #1f2937;
            color: #f1f5f9;
        }

        body.dark input,
        body.dark textarea {
            background: #374151;
            color: white;
            border-color: #4b5563;
        }

        @media (max-width: 500px) {
            header h1 {
                font-size: 28px;
            }

            nav {
                gap: 10px;
            }

            .card {
                padding: 15px;
            }
        }
    </style>
</head>

<body class="{{ 'dark' if dark_mode else '' }}">

<header>
    <h1>HICHAM RAH</h1>
    <p>مرحبًا بكم في موقعي الرسمي</p>
</header>

<nav>
    <a href="/">الرئيسية</a>

    {% if logged_in %}
        <a href="/profile">الملف الشخصي</a>
        <a href="/logout">تسجيل الخروج</a>
    {% else %}
        <a href="/register">إنشاء حساب</a>
        <a href="/login">تسجيل الدخول</a>
    {% endif %}

    <a href="/search">البحث</a>
    <a href="/theme">الوضع الليلي</a>
</nav>

<main>
    {% for message in messages %}
        <div class="card notice">{{ message }}</div>
    {% endfor %}

    <section class="card">
        {{ content|safe }}
    </section>
</main>

<footer>
    جميع الحقوق محفوظة © HICHAM RAH
</footer>

</body>
</html>
"""


# ==================== الصفحة الرئيسية ====================

@app.route("/")
def home():
    with connect_db() as db:
        posts = db.execute("""
            SELECT
                posts.id,
                posts.user_id,
                posts.content,
                users.username,
                (
                    SELECT COUNT(*)
                    FROM likes
                    WHERE likes.post_id = posts.id
                ) AS likes_count
            FROM posts
            JOIN users ON users.id = posts.user_id
            ORDER BY posts.id DESC
        """).fetchall()

    content = "<h2>المنشورات الحديثة</h2>"

    if "user_id" in session:
        content += f"""
            <form method="post" action="/post">
                {csrf_field()}
                <textarea name="content"
                    maxlength="2000"
                    placeholder="اكتب منشورك هنا..."
                    required></textarea>
                <button type="submit">نشر المنشور</button>
            </form>
        """
    else:
        content += """
            <p>
                سجّل الدخول للمشاركة في الموقع
                ونشر المحتوى وإضافة التعليقات.
            </p>
        """

    if not posts:
        content += "<p>لا توجد منشورات حتى الآن.</p>"

    for post in posts:
        content += f"""
            <hr>
            <h3>{escape_html(post['username'])}</h3>
            <p>{escape_html(post['content'])}</p>
            <p>عدد الإعجابات: {post['likes_count']}</p>
        """

        if "user_id" in session:
            content += f"""
                <form method="post" action="/like/{post['id']}">
                    {csrf_field()}
                    <button type="submit">
                        إعجاب أو إلغاء الإعجاب
                    </button>
                </form>

                <form method="post"
                    action="/comment/{post['id']}">
                    {csrf_field()}
                    <input name="content"
                        maxlength="500"
                        placeholder="اكتب تعليقًا..."
                        required>
                    <button type="submit">إرسال التعليق</button>
                </form>
            """

        with connect_db() as db:
            comments = db.execute("""
                SELECT comments.content, users.username
                FROM comments
                JOIN users ON users.id = comments.user_id
                WHERE comments.post_id = ?
                ORDER BY comments.id DESC
            """, (post["id"],)).fetchall()

        for comment in comments:
            content += (
                "<p><strong>"
                + escape_html(comment["username"])
                + ":</strong> "
                + escape_html(comment["content"])
                + "</p>"
            )

    return render_page(content)


# ==================== إنشاء حساب ====================

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if not verify_csrf_token():
            return "الطلب غير صالح.", 400

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not 3 <= len(username) <= 30:
            flash("يجب أن يتراوح اسم المستخدم بين 3 و30 حرفًا.")
            return redirect("/register")

        if len(password) < 8:
            flash("يجب أن تتكون كلمة المرور من 8 أحرف على الأقل.")
            return redirect("/register")

        try:
            with connect_db() as db:
                db.execute(
                    "INSERT INTO users(username, password) VALUES (?, ?)",
                    (username, generate_password_hash(password))
                )

            flash("تم إنشاء الحساب بنجاح.")
            return redirect("/login")

        except sqlite3.IntegrityError:
            flash("اسم المستخدم مستخدم بالفعل.")

    return render_page(f"""
        <h2>إنشاء حساب جديد</h2>
        <form method="post">
            {csrf_field()}
            <input name="username"
                minlength="3" maxlength="30"
                placeholder="اسم المستخدم" required>

            <input type="password" name="password"
                minlength="8"
                placeholder="كلمة المرور" required>

            <button type="submit">إنشاء الحساب</button>
        </form>
    """)


# ==================== تسجيل الدخول ====================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if not verify_csrf_token():
            return "الطلب غير صالح.", 400

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        with connect_db() as db:
            user = db.execute(
                "SELECT * FROM users WHERE username = ?",
                (username,)
            ).fetchone()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            create_csrf_token()

            flash("مرحبًا بك في HICHAM RAH.")
            return redirect("/")

        flash("اسم المستخدم أو كلمة المرور غير صحيحة.")

    return render_page(f"""
        <h2>تسجيل الدخول</h2>
        <form method="post">
            {csrf_field()}
            <input name="username"
                placeholder="اسم المستخدم" required>

            <input type="password" name="password"
                placeholder="كلمة المرور" required>

            <button type="submit">تسجيل الدخول</button>
        </form>
    """)


# ==================== تسجيل الخروج ====================

@app.route("/logout")
def logout():
    session.clear()
    flash("تم تسجيل الخروج بنجاح.")
    return redirect("/")


# ==================== إضافة منشور ====================

@app.route("/post", methods=["POST"])
def add_post():
    if "user_id" not in session:
        return redirect("/login")

    if not verify_csrf_token():
        return "الطلب غير صالح.", 400

    content = request.form.get("content", "").strip()

    if not content or len(content) > 2000:
        flash("يجب ألا يتجاوز المنشور 2000 حرف.")
        return redirect("/")

    with connect_db() as db:
        db.execute(
            "INSERT INTO posts(user_id, content) VALUES (?, ?)",
            (session["user_id"], content)
        )

    flash("تم نشر المحتوى بنجاح.")
    return redirect("/")


# ==================== الإعجاب بالمنشورات ====================

@app.route("/like/<int:post_id>", methods=["POST"])
def like(post_id):
    if "user_id" not in session:
        return redirect("/login")

    if not verify_csrf_token():
        return "الطلب غير صالح.", 400

    with connect_db() as db:
        post = db.execute(
            "SELECT id FROM posts WHERE id = ?", (post_id,)
        ).fetchone()

        if not post:
            return "المنشور غير موجود.", 404

        existing = db.execute("""
            SELECT 1 FROM likes
            WHERE user_id = ? AND post_id = ?
        """, (session["user_id"], post_id)).fetchone()

        if existing:
            db.execute("""
                DELETE FROM likes
                WHERE user_id = ? AND post_id = ?
            """, (session["user_id"], post_id))
        else:
            db.execute("""
                INSERT OR IGNORE INTO likes(user_id, post_id)
                VALUES (?, ?)
            """, (session["user_id"], post_id))

    return redirect("/")


# ==================== التعليقات ====================

@app.route("/comment/<int:post_id>", methods=["POST"])
def comment(post_id):
    if "user_id" not in session:
        return redirect("/login")

    if not verify_csrf_token():
        return "الطلب غير صالح.", 400

    content = request.form.get("content", "").strip()

    if not content or len(content) > 500:
        flash("يجب ألا يتجاوز التعليق 500 حرف.")
        return redirect("/")

    with connect_db() as db:
        post = db.execute(
            "SELECT id FROM posts WHERE id = ?", (post_id,)
        ).fetchone()

        if not post:
            return "المنشور غير موجود.", 404

        db.execute("""
            INSERT INTO comments(user_id, post_id, content)
            VALUES (?, ?, ?)
        """, (session["user_id"], post_id, content))

    return redirect("/")


# ==================== الملف الشخصي ====================

@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user_id" not in session:
        return redirect("/login")

    with connect_db() as db:
        if request.method == "POST":
            if not verify_csrf_token():
                return "الطلب غير صالح.", 400

            bio = request.form.get("bio", "").strip()[:300]

            db.execute(
                "UPDATE users SET bio = ? WHERE id = ?",
                (bio, session["user_id"])
            )

            flash("تم تحديث الملف الشخصي.")

        user = db.execute(
            "SELECT username, bio FROM users WHERE id = ?",
            (session["user_id"],)
        ).fetchone()

    return render_page(f"""
        <h2>الملف الشخصي</h2>
        <p><strong>اسم المستخدم:</strong>
            {escape_html(user['username'])}</p>

        <form method="post">
            {csrf_field()}
            <label>نبذة تعريفية عنك</label>
            <textarea name="bio" maxlength="300"
                placeholder="اكتب نبذة عن نفسك...">{escape_html(user['bio'])}</textarea>
            <button type="submit">حفظ التغييرات</button>
        </form>
    """)


# ==================== البحث ====================

@app.route("/search")
def search():
    query = request.args.get("q", "").strip()[:100]

    content = f"""
        <h2>البحث في الموقع</h2>
        <form method="get">
            <input name="q" maxlength="100"
                value="{escape_html(query)}"
                placeholder="ابحث عن مستخدم أو منشور">
            <button type="submit">بحث</button>
        </form>
    """

    if query:
        pattern = "%" + query + "%"

        with connect_db() as db:
            users = db.execute("""
                SELECT username FROM users
                WHERE username LIKE ? LIMIT 30
            """, (pattern,)).fetchall()

            posts = db.execute("""
                SELECT posts.content, users.username
                FROM posts
                JOIN users ON users.id = posts.user_id
                WHERE posts.content LIKE ?
                ORDER BY posts.id DESC LIMIT 30
            """, (pattern,)).fetchall()

        content += "<h3>نتائج المستخدمين</h3>"

        for user in users:
            content += "<p>" + escape_html(user["username"]) + "</p>"

        content += "<h3>نتائج المنشورات</h3>"

        for post in posts:
            content += (
                "<p><strong>" + escape_html(post["username"])
                + ":</strong> " + escape_html(post["content"]) + "</p>"
            )

        if not users and not posts:
            content += "<p>لم يتم العثور على نتائج.</p>"

    return render_page(content)


# ==================== الوضع الليلي ====================

@app.route("/theme")
def theme():
    session["dark_mode"] = not session.get("dark_mode", False)
    return redirect(request.referrer or "/")


# ==================== تشغيل الموقع ====================

if __name__ == "__main__":
    initialize_database()
    app.run(host="127.0.0.1", port=5000, debug=False)
