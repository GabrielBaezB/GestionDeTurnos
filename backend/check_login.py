from sqlmodel import Session, select
from backend.app.core.database import engine
from backend.app.models.user import User
from backend.app.core.security import verify_password, get_password_hash

def check_login():
    with Session(engine) as session:
        # Check Admin
        user = session.exec(select(User).where(User.email == "admin@zeroq.cl")).first()
        if not user:
            print("ERROR: Admin user not found in DB!")
            return

        print(f"User found: {user.email}")
        print(f"Hashed in DB: {user.hashed_password}")
        
        # Test Password
        is_valid = verify_password("admin", user.hashed_password)
        if is_valid:
            print("SUCCESS: Password 'admin' is VALID.")
        else:
            print("FAILURE: Password 'admin' is INVALID.")
            # Debug hash
            new_hash = get_password_hash("admin")
            print(f"New hash gen: {new_hash}")

if __name__ == "__main__":
    check_login()
