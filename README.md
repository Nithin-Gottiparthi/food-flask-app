# Food Ordering & Delivery — Flask + MySQL

A clean starter for a food ordering website with:
- User signup/login
- Browse restaurants & menu items
- Add to cart & place orders
- Live order status tracking (polling)
- Order history
- Admin dashboard to manage orders and statuses

## Tech Stack
- Python 3.10+
- Flask, Flask-Login, Flask-Migrate, SQLAlchemy
- MySQL (via PyMySQL)
- HTML, CSS, JavaScript

## Setup

1. Create a MySQL database:
   ```sql
   CREATE DATABASE food_delivery_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

2. Configure environment variables (optional; defaults in `config.py`):
   ```bash
   export DB_USER=root
   export DB_PASS=your_password
   export DB_HOST=127.0.0.1
   export DB_PORT=3306
   export DB_NAME=food_delivery_db
   export SECRET_KEY=change-this
   ```

3. Install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. Initialize tables (two options):
   - **Auto-create (dev quick start)**: simply run `python app.py` once; it will create tables and seed sample data.
   - **Migrations (recommended)**:
     ```bash
     flask --app app:create_app db init
     flask --app app:create_app db migrate -m "init"
     flask --app app:create_app db upgrade
     ```

5. Run the app:
   ```bash
   python app.py
   ```
   Login as admin at `/login` with **admin@example.com / admin123**.
   Or create a new user via `/signup`.

## Notes
- Cart is session-based and limited to a single restaurant per order.
- Live tracking uses polling (`/api/order/<id>/status`), change the interval in `Config.ORDER_STATUS_POLL_MS`.
- Extend models to add delivery partners, addresses, payments, etc.