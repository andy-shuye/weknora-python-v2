from app.models.space import Space
from app.models.user import User
from app.utils.constants import ROLE_DEPT_ADMIN, ROLE_SUPER_ADMIN


def is_super_admin(user: User) -> bool:
    return bool(user and user.role_level == ROLE_SUPER_ADMIN)


def is_dept_admin(user: User) -> bool:
    return bool(user and user.role_level in {ROLE_DEPT_ADMIN, ROLE_SUPER_ADMIN})


def can_manage_space(user: User, space: Space) -> bool:
    if not user or not space:
        return False
    if user.role_level == ROLE_SUPER_ADMIN:
        return True
    if user.role_level != ROLE_DEPT_ADMIN:
        return False
    if space.owner_user_id == user.id:
        return True
    if user.department_id and space.owner_department_id == user.department_id:
        return True
    return False


def can_share_kb(user: User) -> bool:
    return bool(user and user.role_level in {ROLE_DEPT_ADMIN, ROLE_SUPER_ADMIN})
