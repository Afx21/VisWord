# api/index.py - Vercel无服务器函数入口
from flask import Flask, request, Response
import json
import os
import sys
import traceback

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# 导入原始的Flask应用
try:
    from app import app as flask_app
except ImportError as e:
    print(f"导入Flask应用失败: {e}")
    print(traceback.format_exc())
    
    # 创建简单的备用应用
    from flask import Flask
    flask_app = Flask(__name__)
    
    @flask_app.route('/', defaults={'path': ''})
    @flask_app.route('/<path:path>')
    def catch_all(path):
        return f"Flask应用导入失败: {str(e)}"

# Vercel Lambda函数处理程序
def handler(event, context):
    """处理Vercel HTTP请求"""
    
    # 解析Vercel事件
    http_method = event.get('httpMethod', 'GET')
    path = event.get('path', '/')
    headers = event.get('headers', {})
    query_string = event.get('queryStringParameters', {})
    body = event.get('body', '')
    is_base64_encoded = event.get('isBase64Encoded', False)
    
    # 如果是base64编码，解码body
    if is_base64_encoded:
        import base64
        body = base64.b64decode(body).decode('utf-8')
    
    # 创建WSGI环境字典
    environ = {
        'REQUEST_METHOD': http_method,
        'PATH_INFO': path,
        'QUERY_STRING': '&'.join([f'{k}={v}' for k, v in (query_string or {}).items()]),
        'SERVER_NAME': 'localhost',
        'SERVER_PORT': '80',
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'wsgi.url_scheme': 'http',
        'wsgi.input': None,
        'wsgi.errors': sys.stderr,
        'wsgi.multithread': False,
        'wsgi.multiprocess': False,
        'wsgi.run_once': False,
        'wsgi.version': (1, 0),
    }
    
    # 添加HTTP头
    for key, value in headers.items():
        key_upper = key.upper().replace('-', '_')
        if key_upper not in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
            environ[f'HTTP_{key_upper}'] = value
        else:
            environ[key_upper] = value
    
    # 对于有body的请求，需要提供输入流
    if body:
        from io import BytesIO
        environ['wsgi.input'] = BytesIO(body.encode('utf-8'))
        environ['CONTENT_LENGTH'] = str(len(body.encode('utf-8')))
    
    # 准备响应
    response_headers = []
    response_body = []
    
    def start_response(status, headers, exc_info=None):
        nonlocal response_headers
        response_headers[:] = [status, headers]
        return response_body.append
    
    # 调用Flask应用
    try:
        result = flask_app.wsgi_app(environ, start_response)
        
        # 收集响应数据
        for data in result:
            response_body.append(data)
        
        if hasattr(result, 'close'):
            result.close()
        
        # 提取状态码和响应头
        status_code = int(response_headers[0].split()[0])
        headers_dict = dict(response_headers[1])
        
        # 构建响应体
        body_content = b''.join(response_body).decode('utf-8')
        
        return {
            'statusCode': status_code,
            'headers': headers_dict,
            'body': body_content
        }
        
    except Exception as e:
        print(f"处理请求时出错: {e}")
        print(traceback.format_exc())
        
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e),
                'message': 'Internal server error'
            })
        }

# 兼容性：直接导出app供Vercel使用
app = flask_app