from sqlmodel import Session, select
from backend.app.core.database import engine, init_db
from backend.app.models.user import User
from backend.app.models.operator import Operator
from backend.app.models.queue import Queue
from backend.app.models.module import Module
from backend.app.models.operator_queue import OperatorQueue
from backend.app.core.security import get_password_hash


def init_db_data():
    """Ensure tables exist and seed essential data for new installs."""
    init_db()

    with Session(engine) as session:
        # --- Admin user ---
        admin = session.exec(select(User).where(User.email == "admin@zeroq.cl")).first()
        if not admin:
            print("Creating default admin user...")
            admin = User(
                email="admin@zeroq.cl",
                hashed_password=get_password_hash("admin"),
                is_superuser=True,
                full_name="Admin",
            )
            session.add(admin)
        else:
            print("Admin user already exists.")

        # --- Operators without password ---
        operators = session.exec(select(Operator)).all()
        for op in operators:
            if not op.hashed_password:
                print(f"Setting default password for operator {op.username}...")
                op.hashed_password = get_password_hash("1234")
                session.add(op)

        session.commit()

        # --- Sample data for new installs ---
        # Queue
        queue = session.exec(select(Queue)).first()
        if not queue:
            print("Creating sample Queue 'General'...")
            queue = Queue(name="General", prefix="A", is_active=True)
            session.add(queue)
            session.commit()
            session.refresh(queue)

        # Module
        module = session.exec(select(Module)).first()
        if not module:
            print("Creating sample Module 'Modulo 1'...")
            module = Module(name="Modulo 1", is_active=True)
            session.add(module)
            session.commit()
            session.refresh(module)

        # Operator
        op = session.exec(select(Operator).where(Operator.username == "operador")).first()
        if not op:
            print("Creating sample Operator 'operador'...")
            op = Operator(
                name="Operador 1",
                username="operador",
                hashed_password=get_password_hash("1234"),
                is_active=True,
                current_module_id=module.id if module else None,
            )
            session.add(op)
            session.commit()
            session.refresh(op)

            # Assign all queues to sample operator
            all_queues = session.exec(select(Queue)).all()
            for q in all_queues:
                session.add(OperatorQueue(operator_id=op.id, queue_id=q.id))
            session.commit()
            print(f"Assigned {len(all_queues)} queue(s) to sample operator.")

        print("Database initialized with default credentials and sample data.")


if __name__ == "__main__":
    init_db_data()
