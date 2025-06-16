# Имя файла: handlers/__init__.py (ФИНАЛЬНАЯ ВЕРСИЯ)

from .start_handler import router as start_router
from .common_handler import router as common_router
from .order_handler import router as order_router
from .staff_handler import router as staff_handler
from .admin_menu_management_handler import router as admin_menu_management_router
from .report_handler import router as report_router

# Этот список указывает, какие имена будут импортированы при 'from handlers import *'
# и помогает IDE с автодополнением.
__all__ = [
    "start_router",
    "common_router",
    "order_router",
    "staff_handler",
    "admin_menu_management_router",
    "report_router",
]