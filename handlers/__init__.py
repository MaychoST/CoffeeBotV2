# handlers/__init__.py

from .start_handler import router as start_router
from .common_handler import router as common_router
from .order_handler import router as order_router
from .staff_handler import router as staff_router
from .admin_menu_management_handler import router as admin_menu_management_router
from .report_handler import router as report_router

__all__ = [
    "start_router",
    "common_router",
    "order_router",
    "staff_router",
    "admin_menu_management_router",
    "report_router",
]