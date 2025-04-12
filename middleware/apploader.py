from typing import Any, Callable
from data.logger import create_logger
import importlib
import inspect
import sys
import os

logger = create_logger('AppLoader', index=False, ecosystem=False)


def register_by(register_funcname: str, app: Any, extra_process: Callable[..., bool] | None = None):
    apps_path = os.path.join(os.getcwd(), 'apps')
    for app_name in os.listdir(apps_path):
        if app_name.startswith('disable_'): continue
        app_path = os.path.join(apps_path, app_name)
        if not os.path.isdir(app_path): continue
        if not os.path.exists(os.path.join(app_path, '__init__.py')): continue
        sys.path.append(app_path)
        try:
            module = importlib.import_module(f'apps.{app_name}')
            if not hasattr(module, register_funcname):
                # logger.error(f"App: {app_name} does not have {register_funcname}")
                continue
            module_func = getattr(module, register_funcname)
            if extra_process and extra_process(module_func):
                logger.info(f"Imported App: {app_name}")
            elif callable(module_func):
                sig = inspect.signature(module_func)
                params = sig.parameters.values()
                if len(params) == 1 and list(params)[0].annotation == app.__class__:
                    module_func(app)
                    logger.info(f"Imported App: {app_name}")
                else:
                    logger.error(f"App: {app_name} {register_funcname} signature error")
            else:
                logger.error(f"App: {app_name} {register_funcname} type error")
        except Exception as e:
            logger.exception(f"Importing App: {app_name} Error: {e}")
