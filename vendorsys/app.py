from datetime import date, timedelta
from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from config import *

app = Flask(__name__)

app.secret_key = SECRET_KEY

app.config["MYSQL_HOST"] = MYSQL_HOST
app.config["MYSQL_USER"] = MYSQL_USER
app.config["MYSQL_PASSWORD"] = MYSQL_PASSWORD
app.config["MYSQL_DB"] = MYSQL_DB

mysql = MySQL(app)


# ---------------- HOME ---------------- #

@app.route("/")
def home():
    return redirect(url_for("login"))


# ---------------- REGISTER ---------------- #

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        shop_name = request.form["shop_name"]
        owner_name = request.form["owner_name"]
        email = request.form["email"]
        phone = request.form["phone"]
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form.get("confirm_password", "")

        # FIX: confirm-password field existed in the form but was never checked
        if password != confirm_password:
            return render_template(
                "register.html",
                error="Passwords do not match"
            )

        hashed_password = generate_password_hash(password)

        cursor = mysql.connection.cursor()

        cursor.execute("""
            INSERT INTO users
            (shop_name, owner_name, email, phone, username, password)
            VALUES(%s,%s,%s,%s,%s,%s)
        """,
        (shop_name, owner_name, email, phone, username, hashed_password))

        mysql.connection.commit()
        cursor.close()

        return redirect(url_for("login"))

    return render_template("register.html")


# ---------------- LOGIN ---------------- #

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        cursor = mysql.connection.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username=%s",
            (username,)
        )

        user = cursor.fetchone()

        cursor.close()

        # column order: (id, shop_name, owner_name, email, phone, username, password)
        if user and check_password_hash(user[6], password):
            session["user"] = username
            return redirect(url_for("dashboard"))
        else:
            return render_template(
                "login.html",
                error="Invalid Username or Password"
            )

    return render_template("login.html")


# ---------------- DASHBOARD ---------------- #

@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM products")
    total_products = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(quantity) FROM products")
    total_stock = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM products WHERE quantity<=5")
    low_stock = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM products
        WHERE expiry_date<CURDATE()
    """)
    expired_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM products
        WHERE expiry_date>=CURDATE() AND expiry_date<=DATE_ADD(CURDATE(),INTERVAL 7 DAY)
    """)
    expiring_soon = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM products
        WHERE expiry_date<=DATE_ADD(CURDATE(),INTERVAL 30 DAY)
        AND MONTH(expiry_date)=MONTH(CURDATE())
    """)
    expiring_products = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM products
        WHERE expiry_date>DATE_ADD(CURDATE(),INTERVAL 30 DAY)
    """)
    safe_stock = cursor.fetchone()[0]

    cursor.execute("""
        SELECT * FROM products
        ORDER BY expiry_date ASC
        LIMIT 4
    """)
    recent_products = cursor.fetchall()

    cursor.close()

    return render_template(
        "dashboard.html",
        total_products=total_products,
        total_stock=total_stock,
        low_stock=low_stock,
        expired_count=expired_count,
        expiring_soon=expiring_soon,
        expiring_products=expiring_products,
        safe_stock=safe_stock,
        recent_products=recent_products,
        today=date.today()
    )


# ===========================
# VIEW PRODUCTS (list page)
# ===========================

@app.route("/products")
def products():

    if "user" not in session:
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor()

    cursor.execute("SELECT * FROM products ORDER BY id DESC")

    data = cursor.fetchall()

    cursor.close()

    return render_template("product.html", products=data)


# ===========================
# ADD PRODUCT
# ===========================

@app.route("/add_product", methods=["GET", "POST"])
def add_product():

    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        product_name = request.form["product_name"]
        category = request.form["category"]
        quantity = request.form["quantity"]
        price = request.form["price"]
        expiry_date = request.form["expiry_date"]

        cursor = mysql.connection.cursor()

        cursor.execute("""
            INSERT INTO products
            (product_name, category, quantity, price, expiry_date)
            VALUES(%s,%s,%s,%s,%s)
        """,
        (product_name, category, quantity, price, expiry_date))

        mysql.connection.commit()

        cursor.close()

        return redirect(url_for("products"))

    # FIX: there was previously no GET handler / template for this page,
    # so the "Add Product" links across the app went nowhere.
    return render_template("add_product.html")


# ===========================
# DELETE PRODUCT
# ===========================

@app.route("/delete_product/<int:id>")
def delete_product(id):

    if "user" not in session:
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor()

    cursor.execute(
        "DELETE FROM products WHERE id=%s",
        (id,)
    )

    mysql.connection.commit()

    cursor.close()

    return redirect(url_for("products"))


# ===========================
# EDIT PRODUCT
# ===========================

@app.route("/edit_product/<int:id>", methods=["GET", "POST"])
def edit_product(id):

    if "user" not in session:
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor()

    if request.method == "POST":

        product_name = request.form["product_name"]
        category = request.form["category"]
        quantity = request.form["quantity"]
        price = request.form["price"]
        expiry_date = request.form["expiry_date"]

        cursor.execute("""
            UPDATE products
            SET
                product_name=%s,
                category=%s,
                quantity=%s,
                price=%s,
                expiry_date=%s
            WHERE id=%s
        """,
        (
            product_name,
            category,
            quantity,
            price,
            expiry_date,
            id
        ))

        mysql.connection.commit()

        cursor.close()

        return redirect(url_for("products"))

    cursor.execute(
        "SELECT * FROM products WHERE id=%s",
        (id,)
    )

    product = cursor.fetchone()

    cursor.close()

    # FIX: this template file did not exist before (was mistakenly named product.html)
    return render_template(
        "edit_product.html",
        product=product
    )


# ===========================
# INVENTORY
# ===========================

@app.route("/inventory")
def inventory():

    if "user" not in session:
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor()

    cursor.execute("SELECT * FROM products ORDER BY product_name")

    products = cursor.fetchall()

    cursor.close()

    return render_template(
        "inventory.html",
        products=products,
        today=date.today(),
        today_plus_7=date.today() + timedelta(days=7)
    )


# ===========================
# ANALYTICS
# ===========================

@app.route("/analytics")
def analytics():

    if "user" not in session:
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM products")
    total_products = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(quantity) FROM products")
    total_stock = cursor.fetchone()[0] or 0

    cursor.execute("SELECT AVG(price) FROM products")
    average_price = cursor.fetchone()[0] or 0

    cursor.execute("SELECT SUM(quantity*price) FROM products")
    total_stock_value = cursor.fetchone()[0] or 0

    cursor.execute("""
        SELECT SUM(quantity*price) FROM products
        WHERE expiry_date<CURDATE()
    """)
    expiry_loss = cursor.fetchone()[0] or 0

    cursor.execute("""
        SELECT category, SUM(quantity) FROM products
        GROUP BY category
    """)
    category_breakdown = cursor.fetchall()

    cursor.close()

    return render_template(
        "analytics.html",
        total_products=total_products,
        total_stock=total_stock,
        average_price=average_price,
        total_stock_value=total_stock_value,
        expiry_loss=expiry_loss,
        category_breakdown=category_breakdown
    )


# ===========================
# EXPIRY ALERTS
# ===========================

@app.route("/alerts")
def alerts():

    if "user" not in session:
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM products WHERE expiry_date<CURDATE()")
    expired_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM products
        WHERE expiry_date>=CURDATE() AND expiry_date<=DATE_ADD(CURDATE(),INTERVAL 7 DAY)
    """)
    expiring_soon = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM products
        WHERE MONTH(expiry_date)=MONTH(CURDATE()) AND YEAR(expiry_date)=YEAR(CURDATE())
    """)
    expiring_this_month = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM products
        WHERE expiry_date>DATE_ADD(CURDATE(),INTERVAL 30 DAY)
    """)
    safe_stock = cursor.fetchone()[0]

    cursor.execute("""
        SELECT * FROM products
        WHERE expiry_date<=DATE_ADD(CURDATE(),INTERVAL 30 DAY)
        ORDER BY expiry_date ASC
    """)
    at_risk_products = cursor.fetchall()

    cursor.close()

    # FIX: this route did not exist before, so every "Expiry Alerts" link
    # in the app was dead, and the page itself only ever showed fake data.
    return render_template(
        "alerts.html",
        expired_count=expired_count,
        expiring_soon=expiring_soon,
        expiring_this_month=expiring_this_month,
        safe_stock=safe_stock,
        at_risk_products=at_risk_products,
        today=date.today(),
        today_plus_7=date.today() + timedelta(days=7)
    )


# ===========================
# PROFILE
# ===========================

@app.route("/profile")
def profile():

    if "user" not in session:
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE username=%s",
        (session["user"],)
    )

    user = cursor.fetchone()

    cursor.close()

    return render_template(
        "profile.html",
        user=user
    )


# ===========================
# SEARCH
# ===========================

@app.route("/search", methods=["POST"])
def search():

    if "user" not in session:
        return redirect(url_for("login"))

    keyword = request.form["search"]

    cursor = mysql.connection.cursor()

    cursor.execute(
        "SELECT * FROM products WHERE product_name LIKE %s",
        ("%" + keyword + "%",)
    )

    products = cursor.fetchall()

    cursor.close()

    return render_template("product.html", products=products)


# ---------------- LOGOUT ---------------- #

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
