# handlers/__init__.py
from . import start_handler
from . import order_handler
from . import staff_handler
from . import admin_menu_management_handler  # <-- Добавили
from . import report_handler

# Можно также экспортировать роутеры напрямую, если хотите обращаться к ним как handlers.start_router
# from .start_handler import router as start_router
# from .order_handler import router as order_router