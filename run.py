import os
import sys
from app import create_app, db

app = create_app()

def init_app():
    with app.app_context():
        # Check if DB exists or users exist
        from app.models.user import User
        db.create_all()
        if not User.query.first():
            print("⚡ Initializing database with benchmark scenario...")
            from seed import seed_database
            seed_database()

if __name__ == '__main__':
    init_app()
    
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '127.0.0.1')
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() in ['true', '1', 't']

    print("\n" + "=" * 65)
    print("   SnackFlow – Food Manufacturing Order-to-Audit ERP")
    print("=" * 65)
    print(f" * Server running on: http://{host}:{port}/")
    print(" * Demo Credentials (Password: admin123 for all):")
    print("     - Owner:                 username: owner")
    print("     - Factory Admin:         username: admin")
    print("     - Salesman A:            username: salesman_a")
    print("     - Salesman B:            username: salesman_b")
    print("     - Production Supervisor: username: supervisor")
    print("     - Accountant / Auditor:  username: accountant")
    print("=" * 65 + "\n")

    app.run(host=host, port=port, debug=debug)
