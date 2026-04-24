from flask import Flask

from app.config import config_map
from app.extensions import cors, db, jwt, migrate


def create_app(config_name: str = 'default') -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_map.get(config_name, config_map['default']))

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, resources={r'/api/*': {'origins': '*'}})

    from app.routes.auth import auth_bp
    from app.routes.chat import chat_bp
    from app.routes.department import department_bp
    from app.routes.knowledge import knowledge_bp
    from app.routes.space import space_bp
    from app.routes.system import system_bp
    from app.routes.user import user_bp

    app.register_blueprint(system_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(department_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(knowledge_bp)
    app.register_blueprint(space_bp)
    app.register_blueprint(chat_bp)

    register_cli(app)

    return app


def register_cli(app: Flask):
    @app.cli.command('init-db')
    def init_db_command():
        from app.models import (
            ChatSessionRegistry,
            Department,
            KnowledgeBaseRegistry,
            Space,
            SpaceDepartmentMember,
            SpaceUserMember,
            User,
        )
        from app.utils.constants import ROLE_DEPT_ADMIN, ROLE_SUPER_ADMIN, ROLE_USER
        from app.utils.security import hash_password

        db.create_all()

        if not Department.query.filter_by(name='Default').first():
            default_dept = Department(name='Default', is_enabled=True)
            db.session.add(default_dept)
            db.session.flush()
        else:
            default_dept = Department.query.filter_by(name='Default').first()

        if not Department.query.filter_by(name='Product').first():
            product_dept = Department(name='Product', is_enabled=True)
            db.session.add(product_dept)
            db.session.flush()
        else:
            product_dept = Department.query.filter_by(name='Product').first()

        if not User.query.filter_by(login_name='admin').first():
            admin = User(
                login_name='admin',
                full_name='System Admin',
                email='admin@local.test',
                department_id=default_dept.id,
                department_name=default_dept.name,
                role_level=ROLE_SUPER_ADMIN,
                password_hash=hash_password('Admin@123456'),
                is_enabled=True,
            )
            db.session.add(admin)

        if not User.query.filter_by(login_name='user01').first():
            standard_user = User(
                login_name='user01',
                full_name='Normal User',
                email='user01@local.test',
                department_id=default_dept.id,
                department_name=default_dept.name,
                role_level=ROLE_USER,
                password_hash=hash_password('User@123456'),
                is_enabled=True,
            )
            db.session.add(standard_user)

        if not User.query.filter_by(login_name='deptadmin01').first():
            dept_admin = User(
                login_name='deptadmin01',
                full_name='Dept Admin',
                email='deptadmin01@local.test',
                department_id=product_dept.id,
                department_name=product_dept.name,
                role_level=ROLE_DEPT_ADMIN,
                password_hash=hash_password('DeptAdmin@123456'),
                is_enabled=True,
            )
            db.session.add(dept_admin)

        db.session.commit()
        print('Database initialized.')
        print('Super admin: admin / Admin@123456')
        print('Normal user: user01 / User@123456')
        print('Department admin: deptadmin01 / DeptAdmin@123456')
