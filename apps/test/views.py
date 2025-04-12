from io import BytesIO
from fastapi import APIRouter
from pydantic import field_validator, BaseModel
from starlette.responses import StreamingResponse

from middleware import Request
from middleware.security import SecurityCheckerBase, SecurityData, SecurityStatus
from views.render import Json
from data.logger import create_logger
from sqlalchemy import text
from tasks import TaskEntry

logger = create_logger('test.view')

router = APIRouter(prefix='/api/v1/test')


@router.get('/health')
async def health(request: Request):
    """
    健康检查(本身有一个最默认的/ping)
    """
    return Json({'status': 'ok'})


@router.get('/security')
async def security(request: Request):
    """
    认证流程
    """
    request = Request.from_request(request)
    security_data: SecurityData = request.authorize()
    if not request.verified:  # security_data.status != SecurityStatus.VERIFIED:
        return Json(**security_data.response)
    return Json(request.user)  # security_data.data


@router.get('/database')
async def database_query(request: Request):
    """
    数据库查询
    """
    request = Request.from_request(request)
    async with request.context.database.dbtest() as db:  # Connect to env: DATABASE_URL_DBTEST
        result = await db.execute(text('SELECT 1'))
        return Json({'result': result.fetchone()})


@router.get('/cache')
async def cache_query(request: Request):
    """
    缓存查询
    """
    request = Request.from_request(request)
    cache = request.context.cache
    value = cache.get('test:cache', str)
    return Json({'cache': value})


@router.post('/cache')
async def cache_set(request: Request):
    """
    缓存设置
    """
    request = Request.from_request(request)
    cache = request.context.cache
    data = await request.body()
    if len(data) <= 0 or len(data) > 1024:
        return Json(code=10000, message='Data length must be between 1 and 1024', status=400)
    try:
        data_str = data.decode('utf-8')
    except:
        return Json(code=10001, message='Data must be a utf-8 string', status=400)
    cache.set('test:cache', data_str, expire=60000)  # 60s
    return Json(message='Cache set successfully')


@router.post('/task')
async def upload_task(request: Request):
    """
    上传任务
    """
    request = Request.from_request(request)
    data = await request.body()
    if len(data) <= 0 or len(data) > 1048576:
        return Json(code=10000, message='Data length must be between 1B and 1MB', status=400)
    try:
        task_obj = TaskEntry.model_validate_json(data)
    except:
        return Json(code=10001, message='Data must be a utf-8 string and a TaskEntry json object', status=400)
    try:
        await request.context.amqp.send('test', task_obj)
        return Json(message='Task uploaded successfully')
    except Exception as e:
        return Json(code=10002, message=str(e), status=400)
