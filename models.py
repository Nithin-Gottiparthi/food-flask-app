from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    orders = db.relationship("Order", backref="user", lazy=True)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

class Restaurant(db.Model):
    __tablename__ = "restaurants"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    menu_items = db.relationship("MenuItem", backref="restaurant", lazy=True)

class MenuItem(db.Model):
    __tablename__ = "menu_items"
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey("restaurants.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(400), default="")
    price = db.Column(db.Numeric(10, 2), nullable=False)
    is_available = db.Column(db.Boolean, default=True)

class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey("restaurants.id"), nullable=False)
    status = db.Column(db.String(30), default="Pending", index=True)  # Pending, Preparing, Out for Delivery, Delivered
    total_amount = db.Column(db.Numeric(10,2), default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    restaurant = db.relationship("Restaurant", backref="orders")

    items = db.relationship("OrderItem", backref="order", lazy=True, cascade="all, delete-orphan")

class OrderItem(db.Model):
    __tablename__ = "order_items"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey("menu_items.id"), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    price_each = db.Column(db.Numeric(10,2), nullable=False)

    menu_item = db.relationship("MenuItem")