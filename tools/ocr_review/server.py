from flask import Flask, request, send_from_directory, jsonify, abort, send_file, g
import os
import json
import glob
import mimetypes
import time
import logging
from logging.handlers import RotatingFileHandler
from functools import wraps
import datetime

app = Flask(__name__)
BASE_DIR = os.path.dirname(__file__)
IMG_DIR = os.path.abspath(os.path.join(BASE_DIR, '../ocr_chars'))

# 设置日志
LOG_DIR = os.path.abspath(os.path.join(BASE_DIR, '../../logs'))
os.makedirs(LOG_DIR, exist_ok=True)

log_file = os.path.join(LOG_DIR, 'ocr_server.log')
file_handler = RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5, encoding='utf-8')
file_handler.setFormatter(logging.Formatter(
    '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
))
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)

# 性能统计
performance_stats = {
    'total_requests': 0,
    'successful_requests': 0,
    'failed_requests': 0,
    'avg_response_time': 0,
    'requests_by_type': {},
    'image_stats': {}
}

# 记录请求的中间件
@app.before_request
def before_request():
    g.start_time = time.time()
    app.logger.info(f"请求: {request.method} {request.path} 来自 {request.remote_addr}")

@app.after_request
def after_request(response):
    global performance_stats
    
    # 计算响应时间
    diff = time.time() - g.start_time
    
    # 更新统计
    performance_stats['total_requests'] += 1
    
    # 按请求类型分类
    req_type = request.path.split('/')[1] if len(request.path.split('/')) > 1 else 'root'
    if req_type not in performance_stats['requests_by_type']:
        performance_stats['requests_by_type'][req_type] = {'count': 0, 'success': 0, 'fail': 0}
    
    performance_stats['requests_by_type'][req_type]['count'] += 1
    
    # 记录成功/失败
    if 200 <= response.status_code < 300:
        performance_stats['successful_requests'] += 1
        performance_stats['requests_by_type'][req_type]['success'] += 1
    else:
        performance_stats['failed_requests'] += 1
        performance_stats['requests_by_type'][req_type]['fail'] += 1
    
    # 更新平均响应时间
    performance_stats['avg_response_time'] = ((performance_stats['avg_response_time'] * 
        (performance_stats['total_requests'] - 1)) + diff) / performance_stats['total_requests']
    
    app.logger.info(f"响应: {response.status_code} 用时 {diff:.4f}秒")
    
    return response

# 动态查找最新的映射文件
def get_latest_mapping_file():
    mapping_dir = os.path.abspath(os.path.join(BASE_DIR, '../../cache/mappings'))
    mapping_files = glob.glob(os.path.join(mapping_dir, '*_mapping.json'))
    if not mapping_files:
        return None
    # 按修改时间排序，取最新的
    return sorted(mapping_files, key=os.path.getmtime)[-1]

MAPPING_PATH = get_latest_mapping_file()
app.logger.info(f'使用映射文件: {MAPPING_PATH}')

@app.route('/')
def index():
    app.logger.info("请求主页面")
    return send_from_directory(BASE_DIR, 'ocr_review.html')

@app.route('/mapping.json')
def get_mapping():
    if not MAPPING_PATH or not os.path.exists(MAPPING_PATH):
        app.logger.error(f"映射文件不存在: {MAPPING_PATH}")
        # 如果映射文件不存在，返回404错误
        return jsonify({'error': 'Mapping file not found'}), 404
    
    app.logger.info(f'提供映射文件: {MAPPING_PATH}')
    return send_from_directory(os.path.dirname(MAPPING_PATH), os.path.basename(MAPPING_PATH))

@app.route('/save', methods=['POST'])
def save_mapping():
    if not MAPPING_PATH:
        app.logger.error("没有配置映射文件路径")
        return jsonify({'error': 'No mapping file configured'}), 500
        
    try:
        data = request.get_json()
        app.logger.info(f"保存映射数据，包含 {len(data)} 个项目")
        
        with open(MAPPING_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return {'status': 'ok'}
    except Exception as e:
        app.logger.error(f"保存映射时出错: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/ocr_chars/<path:filename>')
def get_image(filename):
    global performance_stats
    
    file_path = os.path.join(IMG_DIR, filename)
    app.logger.info(f"请求图片: {filename}, 完整路径: {file_path}")
    
    # 记录图片统计
    if filename not in performance_stats['image_stats']:
        performance_stats['image_stats'][filename] = {
            'requests': 0, 
            'success': 0, 
            'fail': 0,
            'last_request': None
        }
    
    performance_stats['image_stats'][filename]['requests'] += 1
    performance_stats['image_stats'][filename]['last_request'] = datetime.datetime.now().isoformat()
    
    if not os.path.exists(file_path):
        app.logger.error(f"图片不存在: {file_path}")
        performance_stats['image_stats'][filename]['fail'] += 1
        # 如果图片不存在，返回404错误
        return jsonify({'error': 'Image not found'}), 404
    
    try:
        # 确保PNG文件使用正确的MIME类型
        if filename.lower().endswith('.png'):
            app.logger.info(f"返回PNG图片: {filename}, 大小: {os.path.getsize(file_path)}字节")
            performance_stats['image_stats'][filename]['success'] += 1
            return send_file(file_path, mimetype='image/png')
        else:
            app.logger.info(f"返回文件: {filename}, 大小: {os.path.getsize(file_path)}字节")
            performance_stats['image_stats'][filename]['success'] += 1
            return send_from_directory(IMG_DIR, filename)
    except Exception as e:
        app.logger.error(f"发送图片时出错 {filename}: {str(e)}")
        performance_stats['image_stats'][filename]['fail'] += 1
        return jsonify({'error': f'Error serving image: {str(e)}'}), 500

@app.route('/stats')
def get_stats():
    """提供服务器性能统计数据"""
    return jsonify(performance_stats)

@app.route('/logs')
def get_logs():
    """查看最新的日志"""
    try:
        with open(log_file, 'r') as f:
            # 返回最后100行日志
            lines = f.readlines()[-100:]
            return jsonify({
                'log_file': log_file,
                'lines': lines
            })
    except Exception as e:
        return jsonify({'error': f'Error reading logs: {str(e)}'}), 500

@app.route('/api/images')
def get_images_list():
    """获取图片目录中的所有图片信息，供测试页面使用"""
    try:
        # 获取图片文件列表
        image_files = [f for f in os.listdir(IMG_DIR) if f.lower().endswith('.png')]
        
        # 构建图片信息列表
        images_info = []
        for filename in sorted(image_files):
            file_path = os.path.join(IMG_DIR, filename)
            stat = os.stat(file_path)
            
            # 从性能统计中获取该图片的请求记录
            stats = performance_stats['image_stats'].get(filename, {
                'requests': 0,
                'success': 0,
                'fail': 0,
                'last_request': None
            })
            
            images_info.append({
                'filename': filename,
                'path': f'/ocr_chars/{filename}',
                'size': stat.st_size,
                'modified': datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'unicode': filename[1:-4],  # 从文件名中提取Unicode编码，例如UE51D.png -> E51D
                'stats': stats
            })
        
        app.logger.info(f"获取图片列表: 共 {len(images_info)} 张图片")
        return jsonify({
            'total': len(images_info),
            'images': images_info,
            'base_url': request.host_url.rstrip('/'),
        })
    except Exception as e:
        app.logger.error(f"获取图片列表出错: {str(e)}")
        return jsonify({'error': f'Error getting images list: {str(e)}'}), 500

@app.route('/test')
def image_test_page():
    """提供图片加载测试页面"""
    return send_from_directory(BASE_DIR, 'image_test.html')

if __name__ == '__main__':
    # 确保正确识别MIME类型
    mimetypes.add_type('image/png', '.png')
    app.logger.info(f"启动服务器，图片目录: {IMG_DIR}")
    app.logger.info(f"已配置MIME类型: image/png -> .png")
    app.run(port=5001, debug=True) 