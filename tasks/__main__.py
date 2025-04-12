from . import AppContext
from middleware.apploader import register_by
import asyncio
import settings
import signal
import sys


signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(0))


mode = sys.argv[1] if len(sys.argv) > 1 else 'task'
register_funcname = 'task_register' if mode == 'task' else f'{mode}_register'
name = getattr(settings, f'{mode.upper()}_WORKER', 'TaskWorker')

app = AppContext(name)

register_by(register_funcname, app)

async def main():
    async with app:
        await app.run()

try:
    asyncio.run(main())
except (KeyboardInterrupt, SystemExit):
    app.logger.info('TaskWorker stoped')
