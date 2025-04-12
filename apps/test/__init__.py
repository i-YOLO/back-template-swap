try:
    from . import views
    on_init = views.router
except ImportError:
    # No View module
    pass
try:
    from . import task
    task_register = task.task_register
except ImportError:
    # No Task module
    pass
