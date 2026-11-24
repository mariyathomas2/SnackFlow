from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user import User, Role
from app.services.audit_service import log_audit

auth_bp = Blueprint('auth', __name__)

def role_required(*allowed_roles):
    """
    Decorator to restrict access to users with specified roles.
    Owner has super-user access to all routes.
    """
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if current_user.role == Role.OWNER or current_user.role in allowed_roles:
                return f(*args, **kwargs)
            flash(f"Access denied: This action requires '{', '.join(allowed_roles)}' privileges.", "danger")
            return redirect(url_for('dashboard.index'))
        return decorated_function
    return decorator

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if not user.is_active:
                flash("Your account has been deactivated. Please contact the administrator.", "danger")
                return render_template('auth/login.html')

            login_user(user)
            log_audit(
                action="USER_LOGIN",
                entity_type="User",
                entity_id=user.id,
                description=f"User {user.username} ({user.role}) logged in."
            )
            flash(f"Welcome back, {user.full_name}! Logged in as {user.role_display}.", "success")
            
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))
        else:
            flash("Invalid username or password. Please try again.", "danger")

    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    log_audit(
        action="USER_LOGOUT",
        entity_type="User",
        entity_id=current_user.id,
        description=f"User {current_user.username} logged out."
    )
    logout_user()
    flash("You have been securely logged out.", "info")
    return redirect(url_for('auth.login'))

@auth_bp.route('/switch-role/<role>')
@login_required
def switch_role(role):
    """
    Demo helper: Switches current session to a representative user of the requested role
    to easily demonstrate role-specific workflows during evaluations/interviews.
    """
    if role not in Role.ALL:
        flash("Invalid role requested.", "danger")
        return redirect(url_for('dashboard.index'))

    target_user = User.query.filter_by(role=role, is_active=True).first()
    if target_user:
        login_user(target_user)
        flash(f"Switched role to: {target_user.role_display} ({target_user.username})", "info")
    else:
        flash(f"No demo user found for role: {role}", "warning")

    return redirect(url_for('dashboard.index'))
