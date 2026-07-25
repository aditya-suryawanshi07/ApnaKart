from datetime import datetime

from flask import Flask, render_template, session, redirect, url_for, request
from werkzeug.utils import secure_filename
import os
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps

app = Flask(__name__)
UPLOAD_FOLDER = os.path.join("static", "images")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

app.secret_key = "apnakart_secret_key"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///apnakart.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# -------------------------
# Database models
# -------------------------

class Product(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    price = db.Column(
        db.Integer,
        nullable=False
    )

    image = db.Column(
        db.String(200)
    )

    description = db.Column(
        db.String(300)
    )

    rating = db.Column(
        db.Float,
        default=4.5
    )

    category = db.Column(
        db.String(50)
    )


class User(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(200),
        nullable=False
    )
    is_admin = db.Column(
    db.Boolean,
    default=False
    )


class Order(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        nullable=False
    )

    customer_name = db.Column(
        db.String(100),
        nullable=False
    )

    address = db.Column(
        db.String(300),
        nullable=False
    )

    phone = db.Column(
        db.String(20),
        nullable=False
    )

    total = db.Column(
        db.Integer,
        nullable=False
    )

    order_date = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

def admin_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):

        if "user_id" not in session:
            return redirect(url_for("login"))

        user = db.session.get(
            User,
            session["user_id"]
        )

        if not user or not user.is_admin:
            return "Access Denied: Admins only.", 403

        return f(*args, **kwargs)

    return decorated_function
# -------------------------
# Helper functions
# -------------------------

def get_cart():

    cart = session.get("cart", {})

    # Convert old list-based cart into the new dictionary format
    if isinstance(cart, list):

        new_cart = {}

        for product_id in cart:

            product_key = str(product_id)

            if product_key in new_cart:
                new_cart[product_key] += 1
            else:
                new_cart[product_key] = 1

        cart = new_cart
        session["cart"] = cart
        session.modified = True

    return cart


def get_cart_count():

    cart = get_cart()

    return sum(cart.values())


# -------------------------
# Home page
# -------------------------

@app.route("/")
def home():

    category = request.args.get("category")
    search = request.args.get("search")

    products_query = Product.query

    if category:

        products_query = products_query.filter_by(
            category=category
        )

    if search:

        products_query = products_query.filter(
            Product.name.ilike(f"%{search}%")
        )

    products = products_query.all()

    return render_template(
        "index.html",
        products=products,
        cart_count=get_cart_count()
    )


# -------------------------
# Product details
# -------------------------

@app.route("/product/<int:product_id>")
def product_details(product_id):

    product = db.session.get(Product, product_id)

    if product is None:
        return "Product not found", 404

    return render_template(
        "product_details.html",
        product=product,
        cart_count=get_cart_count()
    )


# -------------------------
# Shopping cart
# -------------------------

@app.route("/add_to_cart/<int:product_id>")
def add_to_cart(product_id):

    product = db.session.get(Product, product_id)

    if product is None:
        return redirect(url_for("home"))

    cart = get_cart()
    product_key = str(product_id)

    if product_key in cart:
        cart[product_key] += 1
    else:
        cart[product_key] = 1

    session["cart"] = cart
    session.modified = True

    return redirect(
        request.referrer or url_for("cart")
    )


@app.route("/cart")
def cart():

    cart_data = get_cart()
    cart_items = []
    total = 0

    invalid_product_ids = []

    for product_id, quantity in cart_data.items():

        product = db.session.get(
            Product,
            int(product_id)
        )

        if product is None:
            invalid_product_ids.append(product_id)
            continue

        subtotal = product.price * quantity

        cart_items.append({
            "product": product,
            "quantity": quantity,
            "subtotal": subtotal
        })

        total += subtotal

    for product_id in invalid_product_ids:
        cart_data.pop(product_id, None)

    if invalid_product_ids:
        session["cart"] = cart_data
        session.modified = True

    return render_template(
        "cart.html",
        cart_items=cart_items,
        total=total,
        cart_count=get_cart_count()
    )


@app.route("/increase_quantity/<int:product_id>")
def increase_quantity(product_id):

    cart = get_cart()
    product_key = str(product_id)

    if product_key in cart:
        cart[product_key] += 1

    session["cart"] = cart
    session.modified = True

    return redirect(url_for("cart"))


@app.route("/decrease_quantity/<int:product_id>")
def decrease_quantity(product_id):

    cart = get_cart()
    product_key = str(product_id)

    if product_key in cart:

        cart[product_key] -= 1

        if cart[product_key] <= 0:
            cart.pop(product_key)

    session["cart"] = cart
    session.modified = True

    return redirect(url_for("cart"))


@app.route("/remove_from_cart/<int:product_id>")
def remove_from_cart(product_id):

    cart = get_cart()
    product_key = str(product_id)

    cart.pop(product_key, None)

    session["cart"] = cart
    session.modified = True

    return redirect(url_for("cart"))


# -------------------------
# Wishlist
# -------------------------

@app.route("/add_to_wishlist/<int:product_id>")
def add_to_wishlist(product_id):

    product = db.session.get(Product, product_id)

    if product is None:
        return redirect(url_for("home"))

    wishlist = session.get("wishlist", [])

    if product_id not in wishlist:
        wishlist.append(product_id)

    session["wishlist"] = wishlist
    session.modified = True

    return redirect(
        request.referrer or url_for("home")
    )


@app.route("/wishlist")
def wishlist():

    wishlist_items = []
    wishlist_ids = session.get("wishlist", [])
    valid_wishlist_ids = []

    for product_id in wishlist_ids:

        product = db.session.get(
            Product,
            product_id
        )

        if product:

            wishlist_items.append(product)
            valid_wishlist_ids.append(product_id)

    if wishlist_ids != valid_wishlist_ids:

        session["wishlist"] = valid_wishlist_ids
        session.modified = True

    return render_template(
        "wishlist.html",
        products=wishlist_items,
        cart_count=get_cart_count()
    )


@app.route("/remove_from_wishlist/<int:product_id>")
def remove_from_wishlist(product_id):

    wishlist = session.get("wishlist", [])

    if product_id in wishlist:
        wishlist.remove(product_id)

    session["wishlist"] = wishlist
    session.modified = True

    return redirect(url_for("wishlist"))


# -------------------------
# Checkout
# -------------------------

@app.route("/checkout", methods=["GET", "POST"])
def checkout():

    if "user_id" not in session:
        return redirect(url_for("login"))

    cart_data = get_cart()
    cart_items = []
    total = 0

    for product_id, quantity in cart_data.items():

        product = db.session.get(
            Product,
            int(product_id)
        )

        if product is None:
            continue

        subtotal = product.price * quantity

        cart_items.append({
            "product": product,
            "quantity": quantity,
            "subtotal": subtotal
        })

        total += subtotal

    if request.method == "POST":

        if not cart_items:
            return redirect(url_for("cart"))

        customer_name = request.form.get(
            "name",
            ""
        ).strip()

        address = request.form.get(
            "address",
            ""
        ).strip()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        if not customer_name or not address or not phone:

            return render_template(
                "checkout.html",
                cart_items=cart_items,
                total=total,
                message="Please fill in all checkout details."
            )

        order = Order(
            user_id=session["user_id"],
            customer_name=customer_name,
            address=address,
            phone=phone,
            total=total
        )

        db.session.add(order)
        db.session.commit()

        session["cart"] = {}
        session.modified = True

        return render_template(
            "order_success.html"
        )

    return render_template(
        "checkout.html",
        cart_items=cart_items,
        total=total
    )


# -------------------------
# Orders
# -------------------------

@app.route("/my_orders")
def my_orders():

    if "user_id" not in session:
        return redirect(url_for("login"))

    orders = Order.query.filter_by(
        user_id=session["user_id"]
    ).order_by(
        Order.order_date.desc()
    ).all()

    return render_template(
        "my_orders.html",
        orders=orders,
        cart_count=get_cart_count()
    )


# -------------------------
# Authentication
# -------------------------

@app.route("/login", methods=["GET", "POST"])
def login():

    message = ""

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        user = User.query.filter_by(
            email=email
        ).first()

        if user and check_password_hash(
            user.password,
            password
        ):

            session["user_id"] = user.id
            session["user_name"] = user.name

            return redirect(url_for("home"))

        message = "Invalid email or password."

    return render_template(
        "login.html",
        message=message,
        cart_count=get_cart_count()
    )


@app.route("/logout")
def logout():

    session.pop("user_id", None)
    session.pop("user_name", None)

    return redirect(url_for("home"))


@app.route("/register", methods=["GET", "POST"])
def register():

    message = ""

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        if not name or not email or not password:

            message = "Please fill in all fields."

        else:

            existing_user = User.query.filter_by(
                email=email
            ).first()

            if existing_user:

                message = "Email already registered."

            else:

                hashed_password = generate_password_hash(
                    password
                )

                new_user = User(
                    name=name,
                    email=email,
                    password=hashed_password
                )

                db.session.add(new_user)
                db.session.commit()

                return redirect(url_for("login"))

    return render_template(
        "register.html",
        message=message,
        cart_count=get_cart_count()
    )

@app.route("/admin")
@admin_required
def admin():

    products = Product.query.all()

    total_products = Product.query.count()
    total_users = User.query.count()
    total_orders = Order.query.count()

    total_revenue = db.session.query(
        db.func.sum(Order.total)
    ).scalar() or 0

    return render_template(
        "admin.html",
        products=products,
        total_products=total_products,
        total_users=total_users,
        total_orders=total_orders,
        total_revenue=total_revenue
    )

@app.route("/admin/add", methods=["GET", "POST"])
@admin_required
def add_product():

    if request.method == "POST":

        image_file = request.files.get("image")

        if image_file and image_file.filename:

            filename = secure_filename(image_file.filename)

            image_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                filename
            )

            image_file.save(image_path)

        else:
            filename = "default.jpg"

        product = Product(
            name=request.form["name"],
            price=int(request.form["price"]),
            image=filename,
            description=request.form["description"],
            category=request.form["category"],
            rating=float(request.form["rating"])
        )

        db.session.add(product)
        db.session.commit()

        return redirect(url_for("admin"))

    return render_template("add_product.html")


@app.route("/admin/delete/<int:product_id>")
@admin_required
def delete_product(product_id):

    product = Product.query.get_or_404(product_id)

    db.session.delete(product)
    db.session.commit()
    return redirect(url_for("admin"))

@app.route("/admin/edit/<int:product_id>", methods=["GET", "POST"])
@admin_required
def edit_product(product_id):

    product = Product.query.get_or_404(product_id)

    if request.method == "POST":

        product.name = request.form["name"]
        product.price = int(request.form["price"])
        product.image = request.form["image"]
        product.description = request.form["description"]
        product.category = request.form["category"]
        product.rating = float(request.form["rating"])

        db.session.commit()

        return redirect(url_for("admin"))

    return render_template(
        "edit_product.html",
        product=product
    )


# Create database

with app.app_context():
    db.create_all()

# Run application

if __name__ == "__main__":
    app.run(debug=True)