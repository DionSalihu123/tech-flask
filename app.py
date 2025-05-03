from flask import Flask, render_template, request, redirect, url_for, flash, g,session
from werkzeug.security import generate_password_hash, check_password_hash
import database

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Required for flash messages

@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('tech_db', None)
    if db is not None:
        db.close()


@app.route('/home')
@app.route('/')
def home():
    user = None
    if 'username' in session:
        user = {
            'logged_in': True,
            'username': session['username']
        }
    return render_template('index.html', user=user)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        surname = request.form['surname']
        email = request.form['email']
        password = request.form['password']
        
        db = database.get_database()
        cursor = db.cursor()

        # Check if email already exists
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            flash('Email already exists.')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)

        cursor.execute("""
            INSERT INTO users (username, surname, email, password)
            VALUES (?, ?, ?, ?)""",
            (username, surname, email, hashed_password)
        )

        db.commit()
        flash("Registration successful! Please log in.")
        return redirect(url_for('login'))

    return render_template('register.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        db = database.get_database()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash(f"Welcome back, {user['username']}! Role: {user['role']}")
            return redirect(url_for('home'))
        else:
            flash("Invalid email or password.")
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    product_id = request.form['product_id']
    product_name = request.form['product_name']
    product_price = float(request.form['product_price'])
    product_image = request.form['product_image']

    if 'cart' not in session:
        session['cart'] = []

    # Check if product already exists in cart
    for item in session['cart']:
        if item['id'] == product_id:
            item['quantity'] += 1
            break
    else:
        session['cart'].append({
            'id': product_id,
            'name': product_name,
            'price': product_price,
            'image': product_image,
            'quantity': 1
        })

    session.modified = True
    return redirect(url_for('shporta'))  # redirect to the cart page


@app.route('/remove_from_cart/<product_id>')
def remove_from_cart(product_id):
    if 'cart' in session:
        session['cart'] = [item for item in session['cart'] if item['id'] != product_id]
        session.modified = True
    return redirect(url_for('shporta'))

@app.route("/shporta")
def shporta():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template("shporta.html")


@app.route('/place_order', methods=['POST'])
def place_order():
    # ensure user is logged in
    if 'user_id' not in session:
        flash("Please log in to place an order.", "warning")
        return redirect(url_for('login'))

    cart = session.get('cart', [])
    if not cart:
        flash("Your cart is empty.", "warning")
        return redirect(url_for('shporta'))

    db = database.get_database()
    cursor = db.cursor()

    # 1) insert the order record
    total = sum(item['price'] * item['quantity'] for item in cart)
    cursor.execute(
        "INSERT INTO orders (user_id, total_price) VALUES (?, ?)",
        (session['user_id'], total)
    )
    order_id = cursor.lastrowid

    # 2) insert each item into order_items
    for item in cart:
        cursor.execute(
            "INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (?, ?, ?, ?)",
            (order_id, item['id'], item['quantity'], item['price'])
        )

    db.commit()
    cursor.close()

    # 3) clear the cart and redirect
    session.pop('cart', None)
    flash("Your order has been placed successfully!", "success")
    return redirect(url_for('home'))


@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
