import os

try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv(override=True)
except:
    pass

SERVER_LAYER = int(os.getenv('SERVER_LAYER', '2'))
SERVER_APP_LAYER = int(os.getenv('SERVER_APP_LAYER', '5'))

TASK_WORKER = os.getenv('TASK_WORKER', 'TaskWorker')
PULL_WORKER = os.getenv('PULL_WORKER', 'PullWorker')

CACHE_URL = os.getenv('CACHE_URL', 'redis://127.0.0.1:6379/0')
RABBIT_URL = os.getenv('RABBIT_URL', 'amqp://guest:guest@rabbitmq:5672/')

DATABASE_DICT: dict[str, str] = {}

for env_name, env_value in os.environ.items():
    if env_name.startswith('DATABASE_URL_'):
        DATABASE_DICT[env_name.removeprefix('DATABASE_URL_').lower()] = env_value

DATABASE_URLS = os.getenv('DATABASE_URLS', 'sqlite:////data/web3.db').split(',')

ENV = os.getenv('ENV', 'development')  # development, production, testing

CHECK_SALT = os.getenv('CHECK_SALT', 'check_salt')
JWT_SECRET = os.getenv('JWT_SECRET', 'jwt_secret')
URL_FILTERS = os.getenv('URL_FILTERS', '/ping').split(',')

QUICK_KEY = os.getenv('QUICK_KEY', 'QN_IPFS_API')
