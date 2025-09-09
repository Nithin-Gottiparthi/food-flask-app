from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from decimal import Decimal
from config import Config
from models import db, User, Restaurant, MenuItem, Order, OrderItem
from sqlalchemy.exc import IntegrityError

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    Migrate(app, db)

    login_manager = LoginManager(app)
    login_manager.login_view = 'login'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.context_processor
    def inject_globals():
        return {"current_user": current_user}

    # --------- Auth ---------
    @app.route('/signup', methods=['GET', 'POST'])
    def signup():
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            if not name or not email or not password:
                flash('All fields are required.', 'danger')
                return render_template('signup.html')
            try:
                user = User(name=name, email=email)
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                flash('Account created. Please log in.', 'success')
                return redirect(url_for('login'))
            except IntegrityError:
                db.session.rollback()
                flash('Email already registered.', 'warning')
        return render_template('signup.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            user = User.query.filter_by(email=email).first()
            if user and user.check_password(password):
                login_user(user)
                return redirect(url_for('restaurants'))
            flash('Invalid credentials', 'danger')
        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('login'))

    # --------- Browse ---------
    @app.route('/')
    @login_required
    def home():
        return redirect(url_for('restaurants'))

    @app.route('/restaurants')
    @login_required
    def restaurants():
        data = Restaurant.query.filter_by(is_active=True).all()
        return render_template('restaurants.html', restaurants=data)

    @app.route('/restaurant/<int:restaurant_id>/menu')
    @login_required
    def menu(restaurant_id):
        r = Restaurant.query.get_or_404(restaurant_id)
        items = MenuItem.query.filter_by(restaurant_id=restaurant_id, is_available=True).all()
        return render_template('menu.html', restaurant=r, items=items)

    # --------- Cart (session-based) ---------
    def _get_cart():
        if 'cart' not in session:
            session['cart'] = {"restaurant_id": None, "items": {}}  # items: {menu_item_id: qty}
        return session['cart']

    @app.route('/cart/add', methods=['POST'])
    @login_required
    def cart_add():
        menu_item_id = int(request.form.get('menu_item_id'))
        qty = int(request.form.get('quantity', 1))
        item = MenuItem.query.get_or_404(menu_item_id)
        cart = _get_cart()
        if cart['restaurant_id'] not in (None, item.restaurant_id):
            return jsonify({"ok": False, "message": "Cart contains items from a different restaurant."}), 400
        cart['restaurant_id'] = item.restaurant_id
        cart['items'][str(menu_item_id)] = cart['items'].get(str(menu_item_id), 0) + max(1, qty)
        session.modified = True
        return jsonify({"ok": True})

    @app.route('/cart')
    @login_required
    def cart_view():
        cart = _get_cart()
        items = []
        total = Decimal('0.00')
        if cart['items']:
            ids = [int(k) for k in cart['items'].keys()]
            db_items = {i.id: i for i in MenuItem.query.filter(MenuItem.id.in_(ids)).all()}
            for id_str, qty in cart['items'].items():
                mi = db_items.get(int(id_str))
                if not mi: 
                    continue
                line_total = Decimal(mi.price) * qty
                total += line_total
                items.append({"item": mi, "qty": qty, "line_total": line_total})
        return render_template('cart.html', items=items, total=total)

    @app.route('/cart/clear', methods=['POST'])
    @login_required
    def cart_clear():
        session.pop('cart', None)
        return redirect(url_for('restaurants'))

    @app.route('/checkout', methods=['POST'])
    @login_required
    def checkout():
        cart = _get_cart()
        if not cart['items']:
            flash('Your cart is empty.', 'warning')
            return redirect(url_for('cart_view'))
        restaurant_id = cart['restaurant_id']
        order = Order(user_id=current_user.id, restaurant_id=restaurant_id, status='Pending', total_amount=0)
        db.session.add(order)
        db.session.flush()  # get order.id

        total = Decimal('0.00')
        ids = [int(k) for k in cart['items'].keys()]
        db_items = {i.id: i for i in MenuItem.query.filter(MenuItem.id.in_(ids)).all()}
        for id_str, qty in cart['items'].items():
            mi = db_items.get(int(id_str))
            if not mi: 
                continue
            oi = OrderItem(order_id=order.id, menu_item_id=mi.id, quantity=qty, price_each=mi.price)
            db.session.add(oi)
            total += Decimal(mi.price) * qty
        order.total_amount = total
        db.session.commit()

        # Clear cart
        session.pop('cart', None)
        return redirect(url_for('order_status', order_id=order.id))

    # --------- Orders ---------
    @app.route('/orders')
    @login_required
    def orders_history():
        orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
        return render_template('order_history.html', orders=orders)

    @app.route('/order/<int:order_id>/status')
    @login_required
    def order_status(order_id):
        order = Order.query.get_or_404(order_id)
        if order.user_id != current_user.id and not current_user.is_admin:
            return "Not authorized", 403
        poll_ms = Config.ORDER_STATUS_POLL_MS
        return render_template('order_status.html', order=order, poll_ms=poll_ms)

    @app.route('/api/order/<int:order_id>/status')
    @login_required
    def order_status_api(order_id):
        order = Order.query.get_or_404(order_id)
        if order.user_id != current_user.id and not current_user.is_admin:
            return jsonify({"ok": False}), 403
        return jsonify({
            "ok": True,
            "status": order.status,
            "updated_at": order.updated_at.isoformat()
        })

    # --------- Admin ---------
    def admin_required():
        return current_user.is_authenticated and current_user.is_admin

    @app.route('/admin')
    @login_required
    def admin_dashboard():
        if not admin_required():
            return "Admins only", 403
        orders = Order.query.order_by(Order.created_at.desc()).all()
        return render_template('admin_dashboard.html', orders=orders)

    @app.route('/admin/order/<int:order_id>/set_status', methods=['POST'])
    @login_required
    def admin_set_status(order_id):
        if not admin_required():
            return "Admins only", 403
        new_status = request.form.get('status')
        if new_status not in ['Pending', 'Preparing', 'Out for Delivery', 'Delivered']:
            return "Invalid status", 400
        order = Order.query.get_or_404(order_id)
        order.status = new_status
        db.session.commit()
        return redirect(url_for('admin_dashboard'))

    return app

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        # Create tables if not exist
        db.create_all()

        # Seed minimal data if empty
        if not User.query.first():
            admin = User(name="Admin", email="admin@example.com", is_admin=True)
            admin.set_password("admin123")
            db.session.add(admin)

        if not Restaurant.query.first():
            r1 = Restaurant(name="Spice Villa", address="Main Street 1")
            r2 = Restaurant(name="Urban Bites", address="Central Avenue 99")
            db.session.add_all([r1, r2])
            db.session.flush()
            items = [
                MenuItem(restaurant_id=r1.id, name="Paneer Butter Masala", description="Classic North Indian curry", price=220.00),
                MenuItem(restaurant_id=r1.id, name="Garlic Naan", description="Tandoor-baked flatbread", price=40.00),
                MenuItem(restaurant_id=r2.id, name="Veg Burger", description="Crispy patty with fresh veggies", price=150.00),
                MenuItem(restaurant_id=r2.id, name="French Fries", description="Golden and crispy", price=90.00),
            ]
            db.session.add_all(items)
        db.session.commit()

    app.run(host="0.0.0.0", port=5000, debug=True)