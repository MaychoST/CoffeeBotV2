# Имя файла: handlers/__init__.py (ВРЕМЕННАЯ ОТЛАДОЧНАЯ ВЕРСИЯ 1)

from .start_handler import router as start_router
from .common_handler import router as common_router
# from .order_handler import router as order_router # <-- Временно отключен
# from .staff_handler import router as staff_router # <-- Временно отключен
# from .admin_menu_management_handler import router as admin_menu_management_router # <-- Временно отключен
# from .report_handler import router as report_router # <-- Временно отключен


# Временно экспортируем только работающие роутеры
__all__ = [
    "start_router",
    "common_handler",
]