from app import app, db, User

with app.app_context():

    email = input("Enter admin email: ").strip()

    user = User.query.filter_by(email=email).first()

    if user:
        user.is_admin = True
        db.session.commit()
        print("Admin access granted!")
    else:
        print("User not found. Register the account first.")