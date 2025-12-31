from flask import Flask, render_template, request, jsonify, session, send_from_directory
from flask_cors import CORS
import os
import sqlite3
from datetime import datetime, timedelta
import base64
import uuid
import json
import re
import random
from openai import OpenAI
from PIL import Image
import io
from dotenv import load_dotenv
import traceback
import logging

# 设置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()  # 加载.env文件


app = Flask(__name__)
CORS(app, 
     origins=["http://localhost:5000", "http://127.0.0.1:5000", "http://localhost:5500", "http://127.0.0.1:5500"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
     supports_credentials=True,
     resources={
         r"/api/*": {
             "origins": ["http://localhost:5000", "http://127.0.0.1:5000", "http://localhost:5500", "http://127.0.0.1:5500", "http://localhost:3000", "http://127.0.0.1:3000"],
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"]
         }
     })
app.secret_key = 'viswords-secret-key-2025'
app.config['DATABASE'] = 'viswords.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 初始化豆包API客户端
ARK_API_KEY = os.environ.get("ARK_API_KEY", "您的豆包API密钥")
logger.info(f"Loaded ARK_API_KEY (first 5 chars): {ARK_API_KEY[:5] if ARK_API_KEY else 'None'}")

# 初始化OpenAI客户端（豆包API）
client = OpenAI(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    api_key=ARK_API_KEY,
)

# 豆包模型配置
DOUBAO_MODEL = "doubao-seed-1-6-251015"

# 全局变量跟踪初始化状态
_initialized = False

# 初始化数据库
def init_db():
    try:
        with sqlite3.connect(app.config['DATABASE']) as conn:
            cursor = conn.cursor()
            
            # 用户表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 单词表（四六级词汇 + 用户自定义词汇）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT UNIQUE,
                    phonetic TEXT,
                    definition_en TEXT,
                    definition_cn TEXT,
                    level TEXT,  -- CET-4, CET-6, custom, learned
                    image_url TEXT,
                    example_sentence TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source TEXT DEFAULT 'system'  -- system, user, image, search
                )
            ''')
            
            # 用户学习记录 - 确保包含 mastery_score 列
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    word_id INTEGER,
                    status TEXT,  -- known, learning, mastered
                    last_reviewed TIMESTAMP,
                    review_count INTEGER DEFAULT 0,
                    mastery_score INTEGER DEFAULT 0,  -- 0-100分
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (word_id) REFERENCES words (id)
                )
            ''')
            
            # AI生成的问题记录
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ai_questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    word_ids TEXT,  -- JSON数组，包含的单词ID
                    question TEXT,
                    answer TEXT,
                    user_answers TEXT,  -- JSON数组，用户答案
                    score INTEGER,
                    type TEXT,  -- test, translation
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # 图片识别记录
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS image_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    image_path TEXT,
                    description TEXT,
                    recognized_words TEXT,  -- JSON数组
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # 翻译测试记录
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS translation_tests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    word_id INTEGER,
                    sentence_en TEXT,
                    sentence_cn TEXT,
                    user_translation TEXT,
                    is_correct BOOLEAN,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (word_id) REFERENCES words (id)
                )
            ''')
            
            # 学习历史记录
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS learning_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    word_id INTEGER,
                    action TEXT,  -- review, test, translation, custom_add
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (word_id) REFERENCES words (id)
                )
            ''')
            
            conn.commit()
            logger.info("Database initialized successfully")
            
            # 检查并添加可能缺失的列
            try:
                cursor.execute('ALTER TABLE user_words ADD COLUMN mastery_score INTEGER DEFAULT 0;')
                logger.info("Added mastery_score column to user_words table")
            except:
                pass  # 列可能已存在
                
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        logger.error(traceback.format_exc())
        raise e

# 添加丰富的示例单词数据
def add_sample_words():
    # 在 add_sample_words() 函数后添加


    # CET-4 词汇 (80个)
    cet4_words = [
        ("abandon", "/əˈbændən/", "to leave completely and finally", "放弃，抛弃", "CET-4", "", "He decided to abandon his car and continue on foot."),
        ("benefit", "/ˈbenɪfɪt/", "something that is advantageous or good", "利益，好处", "CET-4", "", "Regular exercise has many health benefits."),
        ("challenge", "/ˈtʃælɪndʒ/", "a call to take part in a contest", "挑战", "CET-4", "", "She accepted the challenge to climb the mountain."),
        ("diligent", "/ˈdɪlɪdʒənt/", "constant in effort to accomplish something", "勤奋的", "CET-4", "", "The diligent student always completes his homework on time."),
        ("endeavor", "/ɪnˈdevər/", "to exert oneself to do or effect something", "努力，尽力", "CET-4", "", "We will endeavor to finish the project by Friday."),
        ("frequent", "/ˈfriːkwənt/", "happening often", "频繁的", "CET-4", "", "He makes frequent trips to London for business."),
        ("generate", "/ˈdʒenəreɪt/", "to produce or create something", "产生，生成", "CET-4", "", "The new policy will generate more jobs."),
        ("hinder", "/ˈhɪndər/", "to make it difficult for someone to do something", "阻碍", "CET-4", "", "Bad weather may hinder our travel plans."),
        ("illustrate", "/ˈɪləstreɪt/", "to explain or make something clear by using examples", "说明，阐明", "CET-4", "", "The diagram illustrates how the machine works."),
        ("justify", "/ˈdʒʌstɪfaɪ/", "to show or prove to be right or reasonable", "证明...合理", "CET-4", "", "Can you justify your decision to leave early?"),
        ("knowledge", "/ˈnɒlɪdʒ/", "facts, information, and skills acquired through experience or education", "知识", "CET-4", "", "She has extensive knowledge of history."),
        ("language", "/ˈlæŋɡwɪdʒ/", "the method of human communication", "语言", "CET-4", "", "English is an international language."),
        ("method", "/ˈmeθəd/", "a particular procedure for accomplishing something", "方法", "CET-4", "", "We need a better method to solve this problem."),
        ("necessary", "/ˈnesəsəri/", "required to be done, achieved, or present", "必要的", "CET-4", "", "Sleep is necessary for good health."),
        ("opportunity", "/ˌɒpəˈtjuːnəti/", "a set of circumstances that makes it possible to do something", "机会", "CET-4", "", "This job is a great opportunity for me."),
        ("progress", "/ˈprəʊɡres/", "forward or onward movement towards a destination", "进步", "CET-4", "", "She has made good progress in her studies."),
        ("quality", "/ˈkwɒləti/", "the standard of something as measured against other things", "质量", "CET-4", "", "We only sell products of the highest quality."),
        ("require", "/rɪˈkwaɪər/", "need for a particular purpose", "需要", "CET-4", "", "This job requires patience and skill."),
        ("significant", "/sɪɡˈnɪfɪkənt/", "sufficiently great or important to be worthy of attention", "重要的", "CET-4", "", "There has been a significant increase in sales."),
        ("tradition", "/trəˈdɪʃn/", "the transmission of customs or beliefs from generation to generation", "传统", "CET-4", "", "It's a family tradition to have dinner together on Sundays."),
        ("ultimate", "/ˈʌltɪmət/", "being the best or most extreme example of its kind", "最终的，极致的", "CET-4", "", "The ultimate goal is world peace."),
        ("various", "/ˈveəriəs/", "different from one another", "各种各样的", "CET-4", "", "We have various options to choose from."),
        ("witness", "/ˈwɪtnəs/", "see an event happen", "目击，见证", "CET-4", "", "She witnessed the accident from her window."),
        ("yield", "/jiːld/", "to produce or provide something", "产生，屈服", "CET-4", "", "The investment yields a high return."),
        ("zone", "/zəʊn/", "an area with a particular feature or use", "区域", "CET-4", "", "This is a no-parking zone."),
        ("ambition", "/æmˈbɪʃn/", "a strong desire to achieve something", "雄心，野心", "CET-4", "", "Her ambition is to become a doctor."),
        ("brilliant", "/ˈbrɪliənt/", "extremely bright or impressive", "灿烂的，杰出的", "CET-4", "", "He gave a brilliant performance."),
        ("candidate", "/ˈkændɪdət/", "a person who applies for a job or is nominated for election", "候选人", "CET-4", "", "There are three candidates for the position."),
        ("debate", "/dɪˈbeɪt/", "a formal discussion on a particular topic", "辩论", "CET-4", "", "There was a heated debate about the new policy."),
        ("evidence", "/ˈevɪdəns/", "facts or information indicating whether something is true", "证据", "CET-4", "", "The police found evidence at the crime scene."),
    ]
    
    # CET-6 词汇 (50个)
    cet6_words = [
        ("abnormal", "/æbˈnɔːrml/", "different from what is usual or expected", "反常的，异常的", "CET-6", "", "Such abnormal behavior should be investigated."),
        ("benevolent", "/bəˈnevələnt/", "well meaning and kindly", "仁慈的，慈善的", "CET-6", "", "He was a benevolent leader who cared for his people."),
        ("culminate", "/ˈkʌlmɪneɪt/", "reach a climax or point of highest development", "达到顶点，告终", "CET-6", "", "Years of hard work culminated in her success."),
        ("deteriorate", "/dɪˈtɪəriəreɪt/", "become progressively worse", "恶化，变坏", "CET-6", "", "The situation deteriorated rapidly."),
        ("eloquent", "/ˈeləkwənt/", "fluent or persuasive in speaking or writing", "雄辩的，有说服力的", "CET-6", "", "He gave an eloquent speech at the conference."),
        ("fragile", "/ˈfrædʒaɪl/", "easily broken or damaged", "易碎的，脆弱的", "CET-6", "", "Handle the package carefully, it's fragile."),
        ("gregarious", "/ɡrɪˈɡeəriəs/", "fond of company; sociable", "爱交际的，群居的", "CET-6", "", "She's very gregarious and enjoys parties."),
        ("hierarchy", "/ˈhaɪərɑːki/", "a system in which members are ranked according to status", "等级制度", "CET-6", "", "The company has a strict hierarchy."),
        ("integrity", "/ɪnˈteɡrəti/", "the quality of being honest and having strong moral principles", "正直，诚实", "CET-6", "", "He is a man of great integrity."),
        ("juxtaposition", "/ˌdʒʌkstəpəˈzɪʃn/", "the fact of two things being seen or placed close together", "并置，并列", "CET-6", "", "The juxtaposition of old and new buildings is striking."),
        ("lucid", "/ˈluːsɪd/", "expressed clearly; easy to understand", "清晰的，易懂的", "CET-6", "", "She gave a lucid explanation of the theory."),
        ("meticulous", "/məˈtɪkjələs/", "showing great attention to detail; very careful and precise", "一丝不苟的，细致的", "CET-6", "", "He is meticulous in his work."),
        ("nostalgia", "/nɒˈstældʒə/", "a sentimental longing for the past", "怀旧之情", "CET-6", "", "The old photos filled her with nostalgia."),
        ("obsolete", "/ˈɒbsəliːt/", "no longer produced or used; out of date", "过时的，废弃的", "CET-6", "", "This technology is now obsolete."),
        ("paradigm", "/ˈpærədaɪm/", "a typical example or pattern of something", "范例，范式", "CET-6", "", "This study will change the paradigm in our field."),
        ("quandary", "/ˈkwɒndəri/", "a state of perplexity or uncertainty over what to do", "困境，困惑", "CET-6", "", "I'm in a quandary about which job to accept."),
        ("resilient", "/rɪˈzɪliənt/", "able to withstand or recover quickly from difficult conditions", "有弹性的，适应力强的", "CET-6", "", "Children are often more resilient than adults."),
        ("scrutinize", "/ˈskruːtənaɪz/", "examine or inspect closely and thoroughly", "仔细检查，审查", "CET-6", "", "The documents were carefully scrutinized."),
        ("taciturn", "/ˈtæsɪtɜːn/", "reserved or uncommunicative in speech", "沉默寡言的", "CET-6", "", "He was a taciturn man who spoke little."),
        ("ubiquitous", "/juːˈbɪkwɪtəs/", "present, appearing, or found everywhere", "无处不在的", "CET-6", "", "Mobile phones are now ubiquitous."),
    ]
    
    with sqlite3.connect(app.config['DATABASE']) as conn:
        cursor = conn.cursor()
        
        # 添加CET-4单词
        for word in cet4_words:
            cursor.execute('''
                INSERT OR IGNORE INTO words (word, phonetic, definition_en, definition_cn, level, image_url, example_sentence)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', word)
        
        # 添加CET-6单词
        for word in cet6_words:
            cursor.execute('''
                INSERT OR IGNORE INTO words (word, phonetic, definition_en, definition_cn, level, image_url, example_sentence)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', word)
        
        conn.commit()

# 在 add_sample_words() 函数后添加

def import_words_from_file():
    """从 words.txt 文件导入单词"""
    try:
        file_path = 'words.txt'
        if not os.path.exists(file_path):
            logger.info(f"单词文件 {file_path} 不存在")
            return 0
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        imported_count = 0
        skipped_count = 0
        
        with sqlite3.connect(app.config['DATABASE']) as conn:
            cursor = conn.cursor()
            
            for line in lines:
                line = line.strip()
                # 跳过空行和注释
                if not line or line.startswith('#'):
                    continue
                
                # 解析CSV格式（注意：有些字段可能为空）
                parts = [part.strip() for part in line.split(',')]
                
                # 确保至少有6个字段（最后一个例句字段可能包含逗号，所以需要特殊处理）
                if len(parts) < 6:
                    logger.warning(f"跳过格式不正确的行: {line}")
                    continue
                
                # 处理可能包含逗号的例句字段
                if len(parts) > 6:
                    # 合并第6个及之后的字段作为例句
                    example_sentence = ','.join(parts[6:]).strip()
                    parts = parts[:6] + [example_sentence]
                elif len(parts) == 6:
                    # 如果没有例句字段，添加空字符串
                    parts.append('')
                
                # 确保有7个字段
                word_data = parts + [''] * (7 - len(parts))
                
                word = word_data[0].lower()
                phonetic = word_data[1] if len(word_data) > 1 else ''
                definition_en = word_data[2] if len(word_data) > 2 else ''
                definition_cn = word_data[3] if len(word_data) > 3 else ''
                level = word_data[4] if len(word_data) > 4 else 'CET-4'
                image_url = word_data[5] if len(word_data) > 5 else ''
                example_sentence = word_data[6] if len(word_data) > 6 else ''
                
                # 检查单词是否已存在
                cursor.execute('SELECT id FROM words WHERE word = ?', (word,))
                if cursor.fetchone():
                    skipped_count += 1
                    continue
                
                # 插入单词
                cursor.execute('''
                    INSERT INTO words (word, phonetic, definition_en, definition_cn, level, image_url, example_sentence, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (word, phonetic, definition_en, definition_cn, level, image_url, example_sentence, 'file'))
                
                imported_count += 1
                
                if imported_count % 100 == 0:
                    logger.info(f"已导入 {imported_count} 个单词...")
            
            conn.commit()
        
        logger.info(f"从文件导入完成: {imported_count} 个新单词，跳过 {skipped_count} 个重复单词")
        return imported_count
        
    except Exception as e:
        logger.error(f"从文件导入单词失败: {str(e)}")
        logger.error(traceback.format_exc())
        return 0
# 在第一个请求之前初始化
# 在第一个请求之前初始化
@app.before_request
def initialize():
    global _initialized
    if not _initialized:
        try:
            init_db()
            
            # 检查是否需要添加示例数据
            with sqlite3.connect(app.config['DATABASE']) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM words WHERE level IN ("CET-4", "CET-6")')
                count = cursor.fetchone()[0]
                
                # 如果单词数量很少，先尝试从文件导入
                if count < 100:
                    # 首先尝试从文件导入单词
                    file_import_count = import_words_from_file()
                    
                    # 如果文件导入的单词很少，再添加示例单词
                    cursor.execute('SELECT COUNT(*) FROM words WHERE level IN ("CET-4", "CET-6")')
                    count = cursor.fetchone()[0]
                    
                    if count < 50:
                        add_sample_words()
                        logger.info(f"添加了 {count} 个示例单词到数据库")
                    else:
                        logger.info(f"从文件成功导入 {file_import_count} 个单词")
                else:
                    logger.info(f"数据库中已有 {count} 个单词，跳过导入")
            
            _initialized = True
            logger.info("应用程序初始化成功")
        except Exception as e:
            logger.error(f"初始化过程中出错: {str(e)}")
            logger.error(traceback.format_exc())
 #添加CORS头到所有响应
#@app.after_request
#def after_request(response):
 #   response.headers.add('Access-Control-Allow-Origin', '*')
  #  response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With')
  #  response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
 #   return response

# 处理预检请求
#@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
#@app.route('/<path:path>', methods=['OPTIONS'])
#def handle_options(path):
  #  response = jsonify()
   # response.headers.add('Access-Control-Allow-Origin', '*')
  #  response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With')
  #  response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
  #  return response
# 添加favicon路由，避免404错误
@app.route('/favicon.ico')
def favicon():
    return '', 204
@app.route('/.well-known/appspecific/com.chrome.devtools.json')
def devtools_manifest():
    return '', 200

# 全局404错误处理
@app.errorhandler(404)
def not_found_error(error):
    logger.error(f'404错误: {request.url}')
    return jsonify({'error': 'Not found'}), 404
# 添加一个通用的OPTIONS处理方法
@app.route('/api/<path:path>', methods=['OPTIONS'])
def handle_api_options(path):
    response = jsonify()
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With')
   
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response



# 调用豆包API（文本）
def call_doubao_api(messages, temperature=0.7, stream=False):
    """调用豆包API进行文本对话"""
    try:
        # 检查API密钥
        if not ARK_API_KEY or ARK_API_KEY == "您的豆包API密钥":
            logger.warning("警告: 未配置豆包API密钥，使用模拟数据")
            return None
            
        response = client.chat.completions.create(
            model=DOUBAO_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=2000,
            stream=stream
        )
        
        if stream:
            # 处理流式响应
            content = ""
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content += chunk.choices[0].delta.content
            return content
        else:
            return response.choices[0].message.content
    except Exception as e:
        logger.error(f"豆包API调用失败: {e}")
        return None

# 调用豆包API（图片识别）
def call_doubao_image_api(image_path, question="描述这张图片并提取适合英语学习的单词"):
    """调用豆包API进行图片识别"""
    try:
        # 检查API密钥
        if not ARK_API_KEY or ARK_API_KEY == "您的豆包API密钥":
            logger.warning("警告: 未配置豆包API密钥，使用模拟数据")
            return None
            
        # 读取图片并转换为base64
        with open(image_path, 'rb') as f:
            image_b64 = base64.b64encode(f.read()).decode('utf-8')
        
        # 构建消息
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}"
                        },
                    },
                    {"type": "text", "text": question},
                ],
            }
        ]
        
        response = client.chat.completions.create(
            model=DOUBAO_MODEL,
            messages=messages,
            max_tokens=2000
        )
        
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"豆包图片API调用失败: {e}")
        return None

# 生成AI测试题目
def generate_ai_test(known_words, unknown_words):
    """使用豆包API生成英语学习测试题目"""
    
    prompt = f"""你是一个专业的英语老师，请根据以下信息生成一个英语学习测试题：
       
学生已经掌握的单词：{', '.join(known_words[:5]) if known_words else '暂无'}

请生成一个包含以下内容的测试：
1. 一个包含2-3个新单词的英文句子，要求句子有上下文意义
2. 针对这个句子，设计3个理解性问题（选择题形式，每个问题4个选项）
3. 一个造句练习，要求学生用指定的新单词造句，并提供提示

请严格使用以下JSON格式返回，不要包含任何其他文本：
{{
    "sentence": "生成的英文句子",
    "questions": [
        {{"question": "问题1", "options": ["选项A", "选项B", "选项C", "选项D"], "answer": "A"}},
        {{"question": "问题2", "options": ["选项A", "选项B", "选项C", "选项D"], "answer": "B"}},
        {{"question": "问题3", "options": ["选项A", "选项B", "选项C", "选项D"], "answer": "C"}}
    ],
    "make_sentence": {{
        "word": "要造句的单词",
        "hint": "造句提示"
    }},
    "correct_answers": {{
        "questions": ["正确答案解释1", "正确答案解释2", "正确答案解释3"],
        "make_sentence": "建议的造句示例"
    }}
}}

请确保：
1. 句子要包含学生正在学习的单词
2. 问题要针对句子的理解和单词的用法
3. 答案用A、B、C、D表示
4. 在correct_answers中提供每个问题的详细解释和造句示例
5. 只返回JSON格式，不要有其他任何文本
"""
    
    messages = [
        {"role": "system", "content": "你是一个经验丰富的英语教师，擅长设计有趣有效的学习测试。请只返回JSON格式，不要包含任何其他文本或说明。"},
        {"role": "user", "content": prompt}
    ]
    
    response = call_doubao_api(messages, temperature=0.8)
    
    if response:
        try:
            logger.info(f"豆包API返回的原始响应: {response[:200]}...")
            
            # 清理响应文本，尝试提取JSON
            json_str = response.strip()
            
            # 移除可能存在的markdown代码块
            if '```json' in json_str:
                # 提取```json和```之间的内容
                import re
                json_str = re.search(r'```json(.*?)```', json_str, re.DOTALL)
                if json_str:
                    json_str = json_str.group(1).strip()
            
            # 移除```标记
            json_str = json_str.replace('```', '')
            
            # 查找第一个{和最后一个}
            start = json_str.find('{')
            end = json_str.rfind('}')
            
            if start != -1 and end != -1 and start < end:
                json_str = json_str[start:end+1]
            
            # 记录清理后的JSON字符串
            logger.info(f"清理后的JSON字符串: {json_str[:200]}...")
            
            test_data = json.loads(json_str)
            
            # 验证返回的数据结构
            required_keys = ['sentence', 'questions', 'make_sentence']
            if all(key in test_data for key in required_keys):
                # 确保有正确答案解释
                if 'correct_answers' not in test_data:
                    test_data['correct_answers'] = {
                        'questions': ['正确答案解释1', '正确答案解释2', '正确答案解释3'],
                        'make_sentence': '建议的造句示例'
                    }
                
                logger.info(f"成功解析测试数据，包含 {len(test_data.get('questions', []))} 个问题")
                return test_data
            else:
                missing_keys = [key for key in required_keys if key not in test_data]
                logger.warning(f"返回的JSON格式不正确，缺少键: {missing_keys}")
                logger.warning(f"返回的数据: {test_data}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            logger.error(f"尝试解析的文本: {json_str[:500]}...")
        except Exception as e:
            logger.error(f"处理AI响应时出错: {e}")
            logger.error(f"响应内容: {response[:500]}...")
    
    # 如果AI调用失败，返回模拟数据
    logger.info("使用模拟数据作为备选")
    return generate_fallback_test(known_words, unknown_words)
def generate_fallback_test(known_words, unknown_words):
    """生成模拟测试数据作为备选"""
    # 如果没有未知单词，使用一些默认单词
    if not unknown_words:
        unknown_words = ['study', 'learn', 'practice']
    
    # 如果没有已知单词，使用一些简单单词
    if not known_words:
        known_words = ['word', 'english', 'student']
    
    # 创建句子
    target_word = unknown_words[0] if unknown_words else 'study'
    sentence = f"The diligent student decided to {target_word} diligently for the upcoming English exam, hoping to achieve excellent results through consistent practice and review."
    
    # 创建问题
    questions = [
        {
            "question": "What is the main topic of this sentence?",
            "options": ["A student's study habits", "An exam schedule", "English learning methods", "Academic achievement"],
            "answer": "A"
        },
        {
            "question": f"What does the word '{target_word}' mean in this context?",
            "options": ["To prepare", "To study", "To teach", "To read"],
            "answer": "B"
        },
        {
            "question": "What quality does the student demonstrate?",
            "options": ["Laziness", "Diligence", "Carelessness", "Indifference"],
            "answer": "B"
        }
    ]
    
    return {
        "sentence": sentence,
        "questions": questions,
        "make_sentence": {
            "word": target_word,
            "hint": f"Use '{target_word}' in a sentence about learning or education"
        },
        "correct_answers": {
            "questions": [
                "The sentence mainly discusses a student's approach to studying for an exam.",
                f"The word '{target_word}' here means to engage in learning or preparation.",
                "The student demonstrates diligence, which means careful and persistent work."
            ],
            "make_sentence": f"Example: I need to {target_word} more regularly to improve my vocabulary."
        }
    }

# 生成翻译测试
def generate_translation_test(word_info):
    """生成包含指定单词的句子供翻译测试"""
    
    prompt = f"""请为英语单词 '{word_info["word"]}'（中文意思：{word_info["definition_cn"]}）创建一个翻译测试。
    
    要求：
    1. 创建一个包含这个单词的英文句子
    2. 提供这个句子的中文翻译
    3. 句子要适合英语学习者理解
    
    请用JSON格式返回：
    {{
        "sentence_en": "英文句子",
        "sentence_cn": "中文翻译",
        "hint": "翻译提示（可选）"
    }}
    """
    
    messages = [
        {"role": "system", "content": "你是一个英语老师，为学习者创建翻译练习。"},
        {"role": "user", "content": prompt}
    ]
    
    response = call_doubao_api(messages, temperature=0.7)
    
    if response:
        try:
            # 尝试从响应中提取JSON
            json_str = response.strip()
            json_str = re.sub(r'```json\s*', '', json_str)
            json_str = re.sub(r'\s*```', '', json_str)
            json_str = re.sub(r'^.*?{', '{', json_str, 1, re.DOTALL)
            json_str = re.sub(r'}.*?$', '}', json_str, 1, re.DOTALL)
            
            test_data = json.loads(json_str)
            
            # 验证返回的数据结构
            if all(key in test_data for key in ['sentence_en', 'sentence_cn']):
                return test_data
        except:
            pass
    
    # 如果AI调用失败，返回模拟数据
    return {
        "sentence_en": f"Learning new vocabulary like '{word_info['word']}' is essential for language acquisition.",
        "sentence_cn": f"学习像'{word_info['word']}'这样的新词汇对于语言习得至关重要。",
        "hint": "注意句子结构和单词用法"
    }

# 图片识别和单词建议
def process_image_for_words(image_path):
    """处理图片并返回相关的单词建议"""
    
    question = """请描述这张图片的内容，并从中提取8个适合英语学习的单词（四六级水平）。
    按以下格式返回：
    图片描述: [详细描述图片内容]
    推荐单词: 
    1. 单词1|音标1|英文释义1|中文释义1
    2. 单词2|音标2|英文释义2|中文释义2
    3. 单词3|音标3|英文释义3|中文释义3
    ...（最多3个）
    
    请确保格式准确，每个单词一行，用|分隔各个部分。"""
    
    response = call_doubao_image_api(image_path, question)
    
    if response:
        result = parse_word_suggestions(response)
        if result['words']:
            return result
    
    # 如果AI调用失败，返回模拟数据
    return generate_fallback_image_analysis()

def parse_word_suggestions(text):
    """解析AI返回的单词建议"""
    lines = text.split('\n')
    description = ""
    words = []
    
    for line in lines:
        line = line.strip()
        if line.startswith('图片描述:'):
            description = line.replace('图片描述:', '').strip()
        elif '|' in line and len(line.split('|')) >= 4:
            # 移除行号，如 "1. "、"2. "等
            line = re.sub(r'^\d+\.\s*', '', line)
            parts = line.split('|')
            if len(parts) >= 4:
                words.append({
                    'word': parts[0].strip(),
                    'phonetic': parts[1].strip(),
                    'definition_en': parts[2].strip(),
                    'definition_cn': parts[3].strip()
                })
    
    # 如果没有找到描述，取前几行作为描述
    if not description and lines:
        description = lines[0][:100] + "..."
    
    # 确保至少有一些单词
    if not words:
        words = generate_fallback_words()
    
    return {
        'description': description,
        'words': words[:10]  # 最多返回10个单词
    }

def generate_fallback_image_analysis():
    """生成模拟图片分析数据作为备选"""
    # 模拟识别结果
    image_themes = [
        {
            "description": "A beautiful landscape with mountains, trees, and a clear blue sky.",
            "words": [
                {"word": "landscape", "phonetic": "/ˈlændskeɪp/", "definition_en": "all the visible features of an area of land", "definition_cn": "风景, 景观"},
                {"word": "mountain", "phonetic": "/ˈmaʊntən/", "definition_en": "a large natural elevation of the earth's surface", "definition_cn": "山, 山脉"},
                {"word": "tree", "phonetic": "/triː/", "definition_en": "a woody perennial plant", "definition_cn": "树, 树木"},
                {"word": "sky", "phonetic": "/skaɪ/", "definition_en": "the region of the atmosphere above the earth", "definition_cn": "天空"},
                {"word": "nature", "phonetic": "/ˈneɪtʃər/", "definition_en": "the physical world and everything in it", "definition_cn": "自然, 自然界"}
            ]
        },
        {
            "description": "A busy city street with buildings, cars, and people walking.",
            "words": [
                {"word": "city", "phonetic": "/ˈsɪti/", "definition_en": "a large town", "definition_cn": "城市"},
                {"word": "building", "phonetic": "/ˈbɪldɪŋ/", "definition_en": "a structure with a roof and walls", "definition_cn": "建筑物"},
                {"word": "street", "phonetic": "/striːt/", "definition_en": "a public road in a city or town", "definition_cn": "街道"},
                {"word": "traffic", "phonetic": "/ˈtræfɪk/", "definition_en": "vehicles moving on a road", "definition_cn": "交通"},
                {"word": "urban", "phonetic": "/ˈɜːbən/", "definition_en": "relating to a city", "definition_cn": "城市的"}
            ]
        },
        {
            "description": "A person reading a book in a library or study room.",
            "words": [
                {"word": "book", "phonetic": "/bʊk/", "definition_en": "a written or printed work", "definition_cn": "书, 书籍"},
                {"word": "read", "phonetic": "/riːd/", "definition_en": "look at and comprehend the meaning of written material", "definition_cn": "阅读"},
                {"word": "library", "phonetic": "/ˈlaɪbrəri/", "definition_en": "a building or room containing collections of books", "definition_cn": "图书馆"},
                {"word": "study", "phonetic": "/ˈstʌdi/", "definition_en": "the devotion of time and attention to acquiring knowledge", "definition_cn": "学习, 研究"},
                {"word": "knowledge", "phonetic": "/ˈnɒlɪdʒ/", "definition_en": "facts, information, and skills acquired through experience or education", "definition_cn": "知识"}
            ]
        }
    ]
    
    # 随机选择一个主题
    theme = random.choice(image_themes)
    
    return {
        'description': theme['description'],
        'words': theme['words']
    }

def generate_fallback_words():
    """生成模拟单词数据"""
    return [
        {"word": "example", "phonetic": "/ɪɡˈzɑːmpl/", "definition_en": "a thing characteristic of its kind", "definition_cn": "例子, 范例"},
        {"word": "word", "phonetic": "/wɜːd/", "definition_en": "a single distinct meaningful element of speech", "definition_cn": "单词, 词语"},
        {"word": "learn", "phonetic": "/lɜːn/", "definition_en": "gain or acquire knowledge of or skill in", "definition_cn": "学习, 学会"}
    ]

# 获取单词详细信息
def get_word_details(word):
    """使用豆包API获取单词的详细信息"""
    
    prompt = f"""请提供单词'{word}'的详细信息：
    1. 音标（英式和美式）
    2. 英文释义
    3. 中文释义
    4. 词性
    5. 一个例句
    
    按以下格式返回：
    Word: {word}
    Phonetic: /音标/
    Part of Speech: 词性
    Definition (EN): 英文释义
    Definition (CN): 中文释义
    Example: 例句
    
    请确保信息准确，格式正确。"""
    
    messages = [
        {"role": "system", "content": "你是一个英语词典，准确提供单词信息。"},
        {"role": "user", "content": prompt}
    ]
    
    response = call_doubao_api(messages, temperature=0.3)
    
    # 解析响应
    result = {'word': word, 'found': False}
    if response:
        lines = response.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('Phonetic:'):
                result['phonetic'] = line.replace('Phonetic:', '').strip()
            elif line.startswith('Part of Speech:'):
                result['type'] = line.replace('Part of Speech:', '').strip()
            elif line.startswith('Definition (EN):'):
                result['definition_en'] = line.replace('Definition (EN):', '').strip()
            elif line.startswith('Definition (CN):'):
                result['definition_cn'] = line.replace('Definition (CN):', '').strip()
            elif line.startswith('Example:'):
                result['example'] = line.replace('Example:', '').strip()
        
        result['found'] = True
    
    # 如果AI调用失败，返回模拟数据
    if not result['found']:
        return get_fallback_word_details(word)
    
    return result

def get_fallback_word_details(word):
    """获取单词的模拟详细信息"""
    
    # 在数据库中查找单词
    with sqlite3.connect(app.config['DATABASE']) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM words WHERE word = ?', (word.lower(),))
        row = cursor.fetchone()
        
        if row:
            return {
                'found': True,
                'word': row[1],
                'phonetic': row[2],
                'definition_en': row[3],
                'definition_cn': row[4],
                'level': row[5],
                'example': row[7]
            }
    
    # 如果数据库中不存在，创建模拟数据
    word_examples = {
        "apple": {"phonetic": "/ˈæpl/", "definition_en": "a round fruit with red, yellow, or green skin", "definition_cn": "苹果"},
        "book": {"phonetic": "/bʊk/", "definition_en": "a written or printed work consisting of pages", "definition_cn": "书"},
        "cat": {"phonetic": "/kæt/", "definition_en": "a small domesticated carnivorous mammal", "definition_cn": "猫"},
        "dog": {"phonetic": "/dɒɡ/", "definition_en": "a domesticated carnivorous mammal", "definition_cn": "狗"},
        "house": {"phonetic": "/haʊs/", "definition_en": "a building for human habitation", "definition_cn": "房子"},
        "school": {"phonetic": "/skuːl/", "definition_en": "an institution for educating children", "definition_cn": "学校"},
        "teacher": {"phonetic": "/ˈtiːtʃə(r)/", "definition_en": "a person who teaches", "definition_cn": "老师"},
        "student": {"phonetic": "/ˈstjuːdnt/", "definition_en": "a person who is studying", "definition_cn": "学生"},
        "computer": {"phonetic": "/kəmˈpjuːtə(r)/", "definition_en": "an electronic device for storing and processing data", "definition_cn": "计算机"},
        "phone": {"phonetic": "/fəʊn/", "definition_en": "a telephone", "definition_cn": "电话"}
    }
    
    if word.lower() in word_examples:
        details = word_examples[word.lower()]
        return {
            'found': True,
            'word': word,
            'phonetic': details['phonetic'],
            'definition_en': details['definition_en'],
            'definition_cn': details['definition_cn'],
            'level': 'CET-4',
            'example': f"This is an example sentence with the word '{word}'."
        }
    
    # 如果单词不在示例中，创建通用数据
    return {
        'found': True,
        'word': word,
        'phonetic': f"/{word.lower()}/",
        'definition_en': f"Definition of {word}",
        'definition_cn': f"{word}的中文释义",
        'level': 'CET-4',
        'example': f"Example sentence using the word '{word}'."
    }

# 保存上传的图片
def save_uploaded_image(file):
    """保存上传的图片并返回路径"""
    # 生成唯一文件名
    filename = f"{uuid.uuid4().hex}_{file.filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    # 保存文件
    file.save(filepath)
    
    # 调整图片大小（如果需要）
    try:
        img = Image.open(filepath)
        # 如果图片太大，调整大小
        if img.size[0] > 1024 or img.size[1] > 1024:
            img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            img.save(filepath, 'JPEG')
    except Exception as e:
        logger.error(f"图片处理失败: {e}")
    
    return filepath

# 静态文件路由
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# API路由
@app.route('/api/init_user', methods=['POST'])
def api_init_user():
    try:
        data = request.json
        username = data.get('username', 'default_user')
        
        # 检查用户是否已存在
        with sqlite3.connect(app.config['DATABASE']) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
            result = cursor.fetchone()
            
            if result:
                user_id = result[0]
            else:
                cursor.execute('INSERT INTO users (username) VALUES (?)', (username,))
                conn.commit()
                user_id = cursor.lastrowid
            
            # 记录学习历史
            cursor.execute('''
                INSERT INTO learning_history (user_id, action, details)
                VALUES (?, ?, ?)
            ''', (user_id, 'login', f'用户 {username} 登录系统'))
            conn.commit()
        
        # 设置session
        session['user_id'] = user_id
        session['username'] = username
        
        return jsonify({
            'user_id': user_id,
            'username': username,
            'message': '用户初始化成功'
        })
    except Exception as e:
        logger.error(f"Error in api_init_user: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/get_learning_progress', methods=['GET'])
def api_get_learning_progress():
    """获取用户学习进度"""
    try:
        user_id = session.get('user_id', 1)
        
        with sqlite3.connect(app.config['DATABASE']) as conn:
            cursor = conn.cursor()
            
            # 获取用户学习统计
            cursor.execute('''
                SELECT 
                    COUNT(CASE WHEN status = 'mastered' THEN 1 END) as mastered,
                    COUNT(CASE WHEN status = 'learning' THEN 1 END) as learning,
                    COUNT(CASE WHEN status = 'known' THEN 1 END) as known,
                    COUNT(*) as total
                FROM user_words 
                WHERE user_id = ?
            ''', (user_id,))
            
            stats = cursor.fetchone()
            
            if not stats:
                return jsonify({
                    'user_id': user_id,
                    'progress': {
                        'mastered': 0,
                        'learning': 0,
                        'known': 0,
                        'total': 0
                    },
                    'today_activities': 0,
                    'streak_days': 0
                })
            
            # 获取今日活动数
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute('''
                SELECT COUNT(*) FROM learning_history 
                WHERE user_id = ? AND DATE(created_at) = ?
            ''', (user_id, today))
            today_activities = cursor.fetchone()[0] or 0
            
            # 获取连续学习天数（简化版）
            cursor.execute('''
                SELECT COUNT(DISTINCT DATE(created_at)) as streak
                FROM learning_history 
                WHERE user_id = ? 
                AND created_at >= date('now', '-30 days')
                ORDER BY created_at DESC
                LIMIT 1
            ''', (user_id,))
            streak_result = cursor.fetchone()
            streak_days = streak_result[0] if streak_result and streak_result[0] else 0
            
            return jsonify({
                'user_id': user_id,
                'progress': {
                    'mastered': stats[0] or 0,
                    'learning': stats[1] or 0,
                    'known': stats[2] or 0,
                    'total': stats[3] or 0
                },
                'today_activities': today_activities,
                'streak_days': streak_days
            })
    except Exception as e:
        logger.error(f"Error in api_get_learning_progress: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/get_word_list', methods=['GET'])
def api_get_word_list():
    try:
        level = request.args.get('level', 'CET-4')  # CET-4, CET-6, custom, learned, all
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        user_id = session.get('user_id', 1)
        logger.debug(f"Fetching word list for user_id: {user_id}, level: {level}, limit: {limit}, offset: {offset}")
        
        with sqlite3.connect(app.config['DATABASE']) as conn:
            cursor = conn.cursor()
            
            # 构建查询条件
            if level == 'learned':
                # 已掌握的单词
                cursor.execute('''
                    SELECT w.*, uw.status, uw.mastery_score
                    FROM words w
                    JOIN user_words uw ON w.id = uw.word_id
                    WHERE uw.user_id = ? AND uw.status = 'mastered'
                    ORDER BY uw.last_reviewed DESC
                    LIMIT ? OFFSET ?
                ''', (user_id, limit, offset))
            elif level == 'custom':
                # 用户自定义单词
                cursor.execute('''
                    SELECT w.*, COALESCE(uw.status, 'new') as user_status, COALESCE(uw.mastery_score, 0) as mastery_score
                    FROM words w
                    LEFT JOIN user_words uw ON w.id = uw.word_id AND uw.user_id = ?
                    WHERE w.source = 'user' OR w.level = 'custom'
                    ORDER BY w.created_at DESC
                    LIMIT ? OFFSET ?
                ''', (user_id, limit, offset))
            elif level == 'all':
                # 所有单词
                cursor.execute('''
                    SELECT w.*, COALESCE(uw.status, 'new') as user_status, COALESCE(uw.mastery_score, 0) as mastery_score
                    FROM words w
                    LEFT JOIN user_words uw ON w.id = uw.word_id AND uw.user_id = ?
                    ORDER BY w.id
                    LIMIT ? OFFSET ?
                ''', (user_id, limit, offset))
            else:
                # 特定级别的单词
                cursor.execute('''
                    SELECT w.*, COALESCE(uw.status, 'new') as user_status, COALESCE(uw.mastery_score, 0) as mastery_score
                    FROM words w
                    LEFT JOIN user_words uw ON w.id = uw.word_id AND uw.user_id = ?
                    WHERE w.level = ?
                    ORDER BY w.id
                    LIMIT ? OFFSET ?
                ''', (user_id, level, limit, offset))
            
            words = []
            for row in cursor.fetchall():
                words.append({
                    'id': row[0],
                    'word': row[1],
                    'phonetic': row[2],
                    'definition_en': row[3],
                    'definition_cn': row[4],
                    'level': row[5],
                    'image_url': row[6],
                    'example_sentence': row[7],
                    'created_at': row[8],
                    'source': row[9],
                    'user_status': row[10] if len(row) > 10 else 'new',
                    'mastery_score': row[11] if len(row) > 11 else 0
                })
            
            # 获取总数量
            if level == 'learned':
                cursor.execute('SELECT COUNT(*) FROM user_words WHERE user_id = ? AND status = "mastered"', (user_id,))
            elif level == 'custom':
                cursor.execute('SELECT COUNT(*) FROM words WHERE source = "user" OR level = "custom"')
            elif level == 'all':
                cursor.execute('SELECT COUNT(*) FROM words')
            else:
                cursor.execute('SELECT COUNT(*) FROM words WHERE level = ?', (level,))
            
            total = cursor.fetchone()[0]
        
        logger.debug(f"Successfully fetched {len(words)} words")
        return jsonify({
            'words': words,
            'total': total,
            'has_more': (offset + len(words)) < total
        })
    except Exception as e:
        logger.error(f"Error in api_get_word_list: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/update_word_status', methods=['POST'])
def api_update_word_status():
    try:
        data = request.json
        word_id = data.get('word_id')
        status = data.get('status')  # known, learning, mastered
        user_id = session.get('user_id', 1)
        
        logger.debug(f"更新单词状态: user_id={user_id}, word_id={word_id}, status={status}")
        
        # 如果是临时ID（前端生成的），先检查单词是否存在
        if isinstance(word_id, int) and word_id > 1000000:
            word_data = data.get('word_data')
            if word_data:
                # 在数据库中查找或创建单词
                with sqlite3.connect(app.config['DATABASE']) as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT id FROM words WHERE word = ?', (word_data['word'].lower(),))
                    result = cursor.fetchone()
                    if result:
                        word_id = result[0]
                        logger.debug(f"临时单词已存在，使用数据库ID: {word_id}")
                    else:
                        # 创建新单词
                        cursor.execute('''
                            INSERT OR IGNORE INTO words (word, phonetic, definition_en, definition_cn, level, example_sentence, source)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            word_data['word'].lower(),
                            word_data.get('phonetic', ''),
                            word_data.get('definition_en', ''),
                            word_data.get('definition_cn', ''),
                            'custom',
                            word_data.get('example_sentence', ''),
                            'user'
                        ))
                        word_id = cursor.lastrowid
                        conn.commit()
                        logger.debug(f"创建新单词，数据库ID: {word_id}")
            else:
                logger.error("临时ID但未提供word_data")
                return jsonify({'error': '临时ID必须提供单词数据'}), 400
        
        with sqlite3.connect(app.config['DATABASE']) as conn:
            cursor = conn.cursor()
            
            # 检查是否已存在记录
            cursor.execute('SELECT id, mastery_score FROM user_words WHERE user_id = ? AND word_id = ?', (user_id, word_id))
            existing = cursor.fetchone()
            
            # 计算掌握分数
            mastery_score = 0
            if status == 'known':
                mastery_score = 30
            elif status == 'learning':
                mastery_score = 60
            elif status == 'mastered':
                mastery_score = 100
            
            if existing:
                cursor.execute('''
                    UPDATE user_words 
                    SET status = ?, last_reviewed = ?, review_count = review_count + 1, mastery_score = ?
                    WHERE id = ?
                ''', (status, datetime.now(), mastery_score, existing[0]))
                logger.debug(f"更新现有记录，原记录ID: {existing[0]}")
            else:
                cursor.execute('''
                    INSERT INTO user_words (user_id, word_id, status, last_reviewed, review_count, mastery_score)
                    VALUES (?, ?, ?, ?, 1, ?)
                ''', (user_id, word_id, status, datetime.now(), mastery_score))
                logger.debug(f"插入新记录，单词ID: {word_id}")
            
            # 记录学习历史
            cursor.execute('''
                INSERT INTO learning_history (user_id, word_id, action, details)
                VALUES (?, ?, ?, ?)
            ''', (user_id, word_id, 'update_status', f'将单词状态更新为 {status}，掌握分数: {mastery_score}'))
            
            conn.commit()
        
        return jsonify({'success': True, 'message': '状态更新成功'})
    except Exception as e:
        logger.error(f"Error in api_update_word_status: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/add_custom_word', methods=['POST'])
def api_add_custom_word():
    """添加用户自定义单词"""
    try:
        data = request.json
        user_id = session.get('user_id', 1)
        
        word = data.get('word', '').strip().lower()
        phonetic = data.get('phonetic', '')
        definition_en = data.get('definition_en', '')
        definition_cn = data.get('definition_cn', '')
        example_sentence = data.get('example_sentence', '')
        
        if not word:
            return jsonify({'error': '单词不能为空'}), 400
        
        with sqlite3.connect(app.config['DATABASE']) as conn:
            cursor = conn.cursor()
            
            # 检查单词是否已存在
            cursor.execute('SELECT id FROM words WHERE word = ?', (word,))
            existing = cursor.fetchone()
            
            if existing:
                # 单词已存在，更新为自定义
                cursor.execute('''
                    UPDATE words SET 
                        phonetic = COALESCE(?, phonetic),
                        definition_en = COALESCE(?, definition_en),
                        definition_cn = COALESCE(?, definition_cn),
                        example_sentence = COALESCE(?, example_sentence),
                        level = 'custom',
                        source = 'user'
                    WHERE id = ?
                ''', (phonetic, definition_en, definition_cn, example_sentence, existing[0]))
                word_id = existing[0]
            else:
                # 创建新单词
                cursor.execute('''
                    INSERT INTO words (word, phonetic, definition_en, definition_cn, level, example_sentence, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (word, phonetic, definition_en, definition_cn, 'custom', example_sentence, 'user'))
                word_id = cursor.lastrowid
            
            # 自动标记为已掌握
            cursor.execute('''
                INSERT OR REPLACE INTO user_words (user_id, word_id, status, last_reviewed, review_count, mastery_score)
                VALUES (?, ?, ?, ?, 1, 100)
            ''', (user_id, word_id, 'mastered', datetime.now()))
            
            # 记录学习历史
            cursor.execute('''
                INSERT INTO learning_history (user_id, word_id, action, details)
                VALUES (?, ?, ?, ?)
            ''', (user_id, word_id, 'custom_add', f'添加自定义单词: {word}'))
            
            conn.commit()
        
        return jsonify({
            'success': True,
            'message': '自定义单词添加成功',
            'word_id': word_id
        })
    except Exception as e:
        logger.error(f"Error in api_add_custom_word: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate_test', methods=['POST'])
def api_generate_test():
    try:
        user_id = session.get('user_id', 1)
        
        with sqlite3.connect(app.config['DATABASE']) as conn:
            cursor = conn.cursor()
            
            # 已掌握的单词
            cursor.execute('''
                SELECT w.word FROM words w
                JOIN user_words uw ON w.id = uw.word_id
                WHERE uw.user_id = ? AND uw.status = 'mastered'
                ORDER BY uw.last_reviewed DESC
                LIMIT 5
            ''', (user_id,))
            known_words = [row[0] for row in cursor.fetchall()]
            
            # 正在学习的单词
            cursor.execute('''
                SELECT w.word FROM words w
                JOIN user_words uw ON w.id = uw.word_id
                WHERE uw.user_id = ? AND uw.status = 'learning'
                ORDER BY uw.last_reviewed DESC
                LIMIT 3
            ''', (user_id,))
            unknown_words = [row[0] for row in cursor.fetchall()]
        
        # 如果没有正在学习的单词，从单词库中随机选择
        if not unknown_words:
            with sqlite3.connect(app.config['DATABASE']) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT word FROM words 
                    WHERE id NOT IN (
                        SELECT word_id FROM user_words 
                        WHERE user_id = ? AND status = 'mastered'
                    )
                    ORDER BY RANDOM() LIMIT 3
                ''', (user_id,))
                unknown_words = [row[0] for row in cursor.fetchall()]
        
        # 如果没有单词，使用默认单词
        if not unknown_words:
            unknown_words = ['study', 'learn', 'practice']
        
        # 生成测试
        test_data = generate_ai_test(known_words, unknown_words)
        
        # 保存到数据库
        with sqlite3.connect(app.config['DATABASE']) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO ai_questions (user_id, word_ids, question, answer, type)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, json.dumps(unknown_words), json.dumps(test_data), json.dumps(test_data.get('questions', [])), 'test'))
            conn.commit()
        
        return jsonify(test_data)
    except Exception as e:
        logger.error(f"Error in api_generate_test: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

# 在API路由部分添加


@app.route('/api/import_words_from_file', methods=['POST'])
def api_import_words_from_file():
    """从文件导入单词（手动触发）"""
    try:
        imported_count = import_words_from_file()
        
        return jsonify({
            'success': True,
            'message': f'成功导入 {imported_count} 个单词',
            'imported_count': imported_count
        })
    except Exception as e:
        logger.error(f"Error in api_import_words_from_file: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/submit_test', methods=['POST'])
def api_submit_test():
    """提交测试答案"""
    try:
        data = request.json
        user_id = session.get('user_id', 1)
        
        test_data = data.get('test_data')
        user_answers = data.get('user_answers', {})
        user_sentence = data.get('user_sentence', '')
        
        if not test_data:
            return jsonify({'error': '测试数据不能为空'}), 400
        
        # 计算分数
        score = 0
        total_questions = len(test_data.get('questions', []))
        correct_answers = []
        
        # 检查选择题答案
        for i, question in enumerate(test_data.get('questions', [])):
            user_answer = user_answers.get(str(i))
            correct_answer = question.get('answer', 'A')
            
            if user_answer == correct_answer:
                score += 1
                correct_answers.append(True)
            else:
                correct_answers.append(False)
        
        # 检查造句（简单检查）
        make_word = test_data.get('make_sentence', {}).get('word', '').lower()
        if user_sentence and make_word and make_word in user_sentence.lower():
            score += 1
        
        total_score = total_questions + 1  # 选择题 + 造句题
        percentage = (score / total_score) * 100
        
        # 保存测试结果
        with sqlite3.connect(app.config['DATABASE']) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO ai_questions (user_id, question, answer, user_answers, score, type)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                json.dumps(test_data),
                json.dumps(test_data.get('correct_answers', {})),
                json.dumps({'choices': user_answers, 'sentence': user_sentence}),
                percentage,
                'test_result'
            ))
            
            # 记录学习历史
            cursor.execute('''
                INSERT INTO learning_history (user_id, action, details)
                VALUES (?, ?, ?)
            ''', (user_id, 'test_submit', f'提交测试，得分: {score}/{total_score} ({percentage:.1f}%)'))
            
            conn.commit()
        
        return jsonify({
            'success': True,
            'score': score,
            'total': total_score,
            'percentage': percentage,
            'correct_answers': correct_answers,
            'correct_answers_explanation': test_data.get('correct_answers', {})
        })
    except Exception as e:
        logger.error(f"Error in api_submit_test: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze_image', methods=['POST'])
def api_analyze_image():
    try:
        if 'image' not in request.files:
            logger.error("未提供图片文件")
            return jsonify({'error': 'No image provided'}), 400
        
        image_file = request.files['image']
        user_id = session.get('user_id', 1)
        
        logger.debug(f"开始处理图片，用户ID: {user_id}, 文件名: {image_file.filename}")
        
        # 检查文件类型
        if not image_file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
            logger.error(f"不支持的文件类型: {image_file.filename}")
            return jsonify({'error': 'Invalid file type. Please upload an image.'}), 400
        
        # 保存图片
        image_path = save_uploaded_image(image_file)
        logger.debug(f"图片保存路径: {image_path}")
        
        try:
            # 处理图片
            result = process_image_for_words(image_path)
            logger.debug(f"图片处理完成，识别到 {len(result['words'])} 个单词")
            
            # 保存识别记录
            with sqlite3.connect(app.config['DATABASE']) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO image_records (user_id, image_path, description, recognized_words)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, image_path, result['description'], json.dumps(result['words'])))
                conn.commit()
            
            # 为每个识别出的单词获取更多信息
            word_ids = []
            for word_info in result['words']:
                # 检查单词是否已存在
                with sqlite3.connect(app.config['DATABASE']) as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT id FROM words WHERE word = ?', (word_info['word'].lower(),))
                    existing = cursor.fetchone()
                    
                    if existing:
                        word_ids.append(existing[0])
                        logger.debug(f"单词已存在: {word_info['word']}, ID: {existing[0]}")
                    else:
                        # 获取单词详细信息
                        word_details = get_word_details(word_info['word'])
                        
                        if word_details['found']:
                            # 保存到单词库
                            cursor.execute('''
                                INSERT OR IGNORE INTO words (word, phonetic, definition_en, definition_cn, level, example_sentence, source)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                word_details['word'].lower(),
                                word_details.get('phonetic', word_info.get('phonetic', '')),
                                word_details.get('definition_en', word_info.get('definition_en', '')),
                                word_details.get('definition_cn', word_info.get('definition_cn', '')),
                                'CET-4',
                                word_details.get('example', ''),
                                'image'
                            ))
                            word_id = cursor.lastrowid
                            word_ids.append(word_id)
                            conn.commit()
                            logger.debug(f"新单词保存到数据库: {word_info['word']}, ID: {word_id}")
            
            # 生成图片URL
            image_url = f"/uploads/{os.path.basename(image_path)}"
            result['image_url'] = image_url
            
            # 记录学习历史
            with sqlite3.connect(app.config['DATABASE']) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO learning_history (user_id, action, details)
                    VALUES (?, ?, ?)
                ''', (user_id, 'image_analysis', f'图片识别，识别到 {len(result["words"])} 个单词'))
                conn.commit()
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"图片分析失败: {e}")
            # 清理临时文件
            if os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except:
                    pass
            # 返回友好的错误信息
            return jsonify({
                'error': f'图片分析失败: {str(e)}',
                'description': '图片识别失败，请重试或使用其他图片',
                'words': [],
                'image_url': ''
            }), 500
    except Exception as e:
        logger.error(f"Error in api_analyze_image: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/search_word', methods=['GET'])
def api_search_word():
    try:
        word = request.args.get('word', '').strip().lower()
        
        if not word:
            return jsonify({'error': 'No word provided'}), 400
        
        # 先查数据库
        with sqlite3.connect(app.config['DATABASE']) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM words WHERE word = ?', (word,))
            row = cursor.fetchone()
            
            if row:
                return jsonify({
                    'found': True,
                    'word': row[1],
                    'phonetic': row[2],
                    'definition_en': row[3],
                    'definition_cn': row[4],
                    'level': row[5],
                    'image_url': row[6],
                    'example': row[7]
                })
        
        # 如果数据库中不存在，使用豆包API获取
        word_details = get_word_details(word)
        
        if word_details['found']:
            # 保存到数据库
            with sqlite3.connect(app.config['DATABASE']) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR IGNORE INTO words (word, phonetic, definition_en, definition_cn, level, example_sentence, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    word_details['word'].lower(),
                    word_details.get('phonetic', ''),
                    word_details.get('definition_en', ''),
                    word_details.get('definition_cn', ''),
                    word_details.get('level', 'CET-4'),
                    word_details.get('example', ''),
                    'search'
                ))
                conn.commit()
        
        return jsonify(word_details)
    except Exception as e:
        logger.error(f"Error in api_search_word: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/get_learning_history', methods=['GET'])
def api_get_learning_history():
    """获取学习历史"""
    try:
        user_id = session.get('user_id', 1)
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        with sqlite3.connect(app.config['DATABASE']) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    lh.id,
                    lh.user_id,
                    lh.word_id,
                    lh.action,
                    lh.details,
                    lh.created_at,
                    w.word,
                    w.definition_cn
                FROM learning_history lh
                LEFT JOIN words w ON lh.word_id = w.id
                WHERE lh.user_id = ?
                ORDER BY lh.created_at DESC
                LIMIT ? OFFSET ?
            ''', (user_id, limit, offset))
            
            history = []
            for row in cursor.fetchall():
                history.append({
                    'id': row[0],
                    'user_id': row[1],
                    'word_id': row[2],
                    'action': row[3],
                    'details': row[4],
                    'created_at': row[5],
                    'word': row[6] if row[6] else '',
                    'definition_cn': row[7] if len(row) > 7 and row[7] else ''
                })
            
            # 获取总数量
            cursor.execute('SELECT COUNT(*) FROM learning_history WHERE user_id = ?', (user_id,))
            total = cursor.fetchone()[0]
        
        return jsonify({
            'history': history,
            'total': total,
            'has_more': (offset + len(history)) < total
        })
    except Exception as e:
        logger.error(f"Error in api_get_learning_history: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/get_translation_test', methods=['GET'])
def api_get_translation_test():
    """获取翻译测试"""
    try:
        user_id = session.get('user_id', 1)
        word_id = request.args.get('word_id', type=int)
        
        if not word_id:
            return jsonify({'error': '单词ID不能为空'}), 400
        
        with sqlite3.connect(app.config['DATABASE']) as conn:
            cursor = conn.cursor()
            
            # 获取单词信息
            cursor.execute('SELECT * FROM words WHERE id = ?', (word_id,))
            row = cursor.fetchone()
            
            if not row:
                return jsonify({'error': '单词不存在'}), 404
            
            word_info = {
                'id': row[0],
                'word': row[1],
                'phonetic': row[2],
                'definition_en': row[3],
                'definition_cn': row[4],
                'level': row[5],
                'example_sentence': row[7]
            }
        
        # 生成翻译测试
        test_data = generate_translation_test(word_info)
        
        # 记录测试历史
        with sqlite3.connect(app.config['DATABASE']) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO ai_questions (user_id, word_ids, question, answer, type)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, json.dumps([word_id]), json.dumps(test_data), json.dumps(test_data), 'translation'))
            
            # 记录学习历史
            cursor.execute('''
                INSERT INTO learning_history (user_id, word_id, action, details)
                VALUES (?, ?, ?, ?)
            ''', (user_id, word_id, 'translation_test', f'开始翻译测试: {word_info["word"]}'))
            
            conn.commit()
        
        return jsonify({
            'word': word_info,
            'test': test_data
        })
    except Exception as e:
        logger.error(f"Error in api_get_translation_test: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/submit_translation', methods=['POST'])
def api_submit_translation():
    """提交翻译答案"""
    try:
        data = request.json
        user_id = session.get('user_id', 1)
        
        word_id = data.get('word_id')
        sentence_en = data.get('sentence_en', '')
        user_translation = data.get('user_translation', '')
        correct_translation = data.get('correct_translation', '')
        
        if not word_id or not sentence_en:
            return jsonify({'error': '参数不完整'}), 400
        
        # 简单的翻译检查（实际应用中可以使用更复杂的算法）
        is_correct = False
        if user_translation and correct_translation:
            # 简单的关键词匹配
            keywords = ['重要', '关键', '必要', '需要', '学习', '掌握', '词汇', '单词']
            user_lower = user_translation.lower()
            correct_lower = correct_translation.lower()
            
            # 检查是否包含相同的关键词
            common_keywords = sum(1 for kw in keywords if kw in user_lower and kw in correct_lower)
            is_correct = common_keywords >= 1 or len(user_translation) > 10
        
        # 保存翻译记录
        with sqlite3.connect(app.config['DATABASE']) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO translation_tests (user_id, word_id, sentence_en, sentence_cn, user_translation, is_correct)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, word_id, sentence_en, correct_translation, user_translation, is_correct))
            
            # 记录学习历史
            cursor.execute('''
                INSERT INTO learning_history (user_id, word_id, action, details)
                VALUES (?, ?, ?, ?)
            ''', (user_id, word_id, 'translation_submit', 
                  f'提交翻译测试，用户翻译: {user_translation[:50]}...，正确: {is_correct}'))
            
            conn.commit()
        
        return jsonify({
            'success': True,
            'is_correct': is_correct,
            'correct_translation': correct_translation,
            'user_translation': user_translation
        })
    except Exception as e:
        logger.error(f"Error in api_submit_translation: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/get_test_history', methods=['GET'])
def api_get_test_history():
    """获取测试历史"""
    try:
        user_id = session.get('user_id', 1)
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        with sqlite3.connect(app.config['DATABASE']) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    id,
                    user_id,
                    word_ids,
                    question,
                    answer,
                    user_answers,
                    score,
                    type,
                    created_at
                FROM ai_questions 
                WHERE user_id = ? AND type IN ('test_result', 'translation')
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (user_id, limit, offset))
            
            tests = []
            for row in cursor.fetchall():
                try:
                    question_data = json.loads(row[3]) if row[3] else {}
                    answer_data = json.loads(row[4]) if row[4] else {}
                    user_answers = json.loads(row[5]) if row[5] else {}
                except:
                    question_data = {}
                    answer_data = {}
                    user_answers = {}
                
                tests.append({
                    'id': row[0],
                    'user_id': row[1],
                    'word_ids': json.loads(row[2]) if row[2] and row[2] != '' else [],
                    'question': question_data,
                    'answer': answer_data,
                    'user_answers': user_answers,
                    'score': row[6] if len(row) > 6 else 0,
                    'type': row[7] if len(row) > 7 else '',
                    'created_at': row[8] if len(row) > 8 else ''
                })
            
            # 获取总数量
            cursor.execute('SELECT COUNT(*) FROM ai_questions WHERE user_id = ? AND type IN ("test_result", "translation")', (user_id,))
            total = cursor.fetchone()[0]
        
        return jsonify({
            'tests': tests,
            'total': total,
            'has_more': (offset + len(tests)) < total
        })
    except Exception as e:
        logger.error(f"Error in api_get_test_history: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/get_translation_history', methods=['GET'])
def api_get_translation_history():
    """获取翻译测试历史"""
    try:
        user_id = session.get('user_id', 1)
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        with sqlite3.connect(app.config['DATABASE']) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    tt.id,
                    tt.user_id,
                    tt.word_id,
                    tt.sentence_en,
                    tt.sentence_cn,
                    tt.user_translation,
                    tt.is_correct,
                    tt.created_at,
                    w.word,
                    w.definition_cn
                FROM translation_tests tt
                JOIN words w ON tt.word_id = w.id
                WHERE tt.user_id = ?
                ORDER BY tt.created_at DESC
                LIMIT ? OFFSET ?
            ''', (user_id, limit, offset))
            
            translations = []
            for row in cursor.fetchall():
                translations.append({
                    'id': row[0],
                    'user_id': row[1],
                    'word_id': row[2],
                    'sentence_en': row[3] if row[3] else '',
                    'sentence_cn': row[4] if len(row) > 4 and row[4] else '',
                    'user_translation': row[5] if len(row) > 5 and row[5] else '',
                    'is_correct': bool(row[6]) if len(row) > 6 else False,
                    'created_at': row[7],
                    'word': row[8] if len(row) > 8 and row[8] else '',
                    'definition_cn': row[9] if len(row) > 9 and row[9] else ''
                })
            
            # 获取总数量
            cursor.execute('SELECT COUNT(*) FROM translation_tests WHERE user_id = ?', (user_id,))
            total = cursor.fetchone()[0]
            
            # 获取正确率
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct
                FROM translation_tests 
                WHERE user_id = ?
            ''', (user_id,))
            stats = cursor.fetchone()
            accuracy = (stats[1] / stats[0] * 100) if stats and stats[0] and stats[0] > 0 else 0
        
        return jsonify({
            'translations': translations,
            'total': total,
            'accuracy': round(accuracy, 1)
        })
    except Exception as e:
        logger.error(f"Error in api_get_translation_history: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete_word', methods=['POST'])
def api_delete_word():
    """删除单词（仅限用户自定义单词）"""
    try:
        data = request.json
        user_id = session.get('user_id', 1)
        word_id = data.get('word_id')
        
        if not word_id:
            return jsonify({'error': '单词ID不能为空'}), 400
        
        with sqlite3.connect(app.config['DATABASE']) as conn:
            cursor = conn.cursor()
            
            # 检查单词是否为用户自定义
            cursor.execute('SELECT source FROM words WHERE id = ?', (word_id,))
            word = cursor.fetchone()
            
            if not word:
                return jsonify({'error': '单词不存在'}), 404
            
            if word[0] != 'user' and word[0] != 'custom':
                return jsonify({'error': '只能删除用户自定义的单词'}), 403
            
            # 删除单词
            cursor.execute('DELETE FROM words WHERE id = ?', (word_id,))
            cursor.execute('DELETE FROM user_words WHERE word_id = ? AND user_id = ?', (word_id, user_id))
            
            # 记录学习历史
            cursor.execute('''
                INSERT INTO learning_history (user_id, word_id, action, details)
                VALUES (?, ?, ?, ?)
            ''', (user_id, word_id, 'delete_word', '删除自定义单词'))
            
            conn.commit()
        
        return jsonify({'success': True, 'message': '单词删除成功'})
    except Exception as e:
        logger.error(f"Error in api_delete_word: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/export_data', methods=['GET'])
def api_export_data():
    """导出用户数据"""
    try:
        user_id = session.get('user_id', 1)
        
        with sqlite3.connect(app.config['DATABASE']) as conn:
            cursor = conn.cursor()
            
            # 获取用户信息
            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            user = cursor.fetchone()
            
            # 获取用户学习的单词
            cursor.execute('''
                SELECT w.*, uw.status, uw.mastery_score, uw.last_reviewed, uw.review_count
                FROM user_words uw
                JOIN words w ON uw.word_id = w.id
                WHERE uw.user_id = ?
                ORDER BY uw.last_reviewed DESC
            ''', (user_id,))
            
            learned_words = []
            for row in cursor.fetchall():
                learned_words.append({
                    'word': row[1],
                    'phonetic': row[2],
                    'definition_en': row[3],
                    'definition_cn': row[4],
                    'level': row[5],
                    'example_sentence': row[7],
                    'status': row[10],
                    'mastery_score': row[11],
                    'last_reviewed': row[12],
                    'review_count': row[13]
                })
            
            # 获取学习历史
            cursor.execute('''
                SELECT action, details, created_at 
                FROM learning_history 
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 100
            ''', (user_id,))
            
            history = []
            for row in cursor.fetchall():
                history.append({
                    'action': row[0],
                    'details': row[1],
                    'created_at': row[2]
                })
            
            # 获取测试历史
            cursor.execute('''
                SELECT type, score, created_at 
                FROM ai_questions 
                WHERE user_id = ? AND type = 'test_result'
                ORDER BY created_at DESC
                LIMIT 50
            ''', (user_id,))
            
            tests = []
            for row in cursor.fetchall():
                tests.append({
                    'type': row[0],
                    'score': row[1],
                    'created_at': row[2]
                })
        
        return jsonify({
            'user': {
                'id': user[0],
                'username': user[1],
                'created_at': user[2]
            },
            'learned_words': learned_words,
            'word_count': len(learned_words),
            'history_summary': history[:10],
            'test_summary': tests[:10],
            'exported_at': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error in api_export_data: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

# 健康检查端点
@app.route('/api/health', methods=['GET'])
def api_health():
    try:
        # 检查API密钥是否配置
        api_key_status = "已配置" if ARK_API_KEY and ARK_API_KEY != "您的豆包API密钥" else "未配置"
        
        # 检查数据库连接
        db_status = "正常"
        word_count = 0
        try:
            with sqlite3.connect(app.config['DATABASE']) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM words')
                word_count = cursor.fetchone()[0]
        except Exception as e:
            db_status = f"异常: {str(e)}"
            logger.error(f"Database connection error: {str(e)}")
        
        # 检查上传目录
        upload_dir_status = "正常" if os.path.exists(app.config['UPLOAD_FOLDER']) else "目录不存在"
        
        return jsonify({
            'status': 'healthy',
            'message': 'VisWords API is running',
            'version': '2.0.0',
            'api_key_status': api_key_status,
            'ai_enabled': api_key_status == "已配置",
            'database_status': db_status,
            'upload_dir_status': upload_dir_status,
            'word_count': word_count,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error in health check: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# 添加全局错误处理
@app.errorhandler(Exception)
def handle_exception(e):
    # Return JSON instead of HTML for HTTP errors
    logger.error(f"Unhandled exception: {str(e)}")
    logger.error(traceback.format_exc())
    return jsonify({
        "error": "Internal server error",
        "message": str(e)
    }), 500

@app.route('/api/get_spelling_word', methods=['GET'])
def api_get_spelling_word():
    """获取拼写练习单词"""
    try:
        user_id = session.get('user_id', 1)
        level = request.args.get('level', 'CET-4')
        difficulty = request.args.get('difficulty', 'medium')  # easy, medium, hard
        
        with sqlite3.connect(app.config['DATABASE']) as conn:
            cursor = conn.cursor()
            
            # 根据难度筛选单词
            if difficulty == 'easy':
                # 简单：4-6个字母的单词
                cursor.execute('''
                    SELECT * FROM words 
                    WHERE LENGTH(word) BETWEEN 4 AND 6 
                    AND level = ?
                    ORDER BY RANDOM()
                    LIMIT 1
                ''', (level,))
            elif difficulty == 'hard':
                # 困难：8个字母以上的单词
                cursor.execute('''
                    SELECT * FROM words 
                    WHERE LENGTH(word) >= 8
                    AND level = ?
                    ORDER BY RANDOM()
                    LIMIT 1
                ''', (level,))
            else:
                # 中等：6-8个字母的单词
                cursor.execute('''
                    SELECT * FROM words 
                    WHERE LENGTH(word) BETWEEN 6 AND 8 
                    AND level = ?
                    ORDER BY RANDOM()
                    LIMIT 1
                ''', (level,))
            
            row = cursor.fetchone()
            
            if not row:
                # 如果没有找到单词，返回任意单词
                cursor.execute('''
                    SELECT * FROM words 
                    WHERE level = ?
                    ORDER BY RANDOM()
                    LIMIT 1
                ''', (level,))
                row = cursor.fetchone()
            
            if row:
                word_info = {
                    'id': row[0],
                    'word': row[1],
                    'phonetic': row[2],
                    'definition_en': row[3],
                    'definition_cn': row[4],
                    'level': row[5],
                    'example_sentence': row[7]
                }
                
                # 记录学习历史
                cursor.execute('''
                    INSERT INTO learning_history (user_id, word_id, action, details)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, row[0], 'spelling_practice', f'开始拼写练习: {row[1]}'))
                
                conn.commit()
                
                return jsonify({
                    'success': True,
                    'word': word_info
                })
            else:
                return jsonify({'error': '未找到合适的单词'}), 404
                
    except Exception as e:
        logger.error(f"Error in api_get_spelling_word: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/check_spelling', methods=['POST'])
def api_check_spelling():
    """检查拼写答案"""
    try:
        data = request.json
        user_id = session.get('user_id', 1)
        
        word_id = data.get('word_id')
        user_answer = data.get('user_answer', '').strip().lower()
        correct_word = data.get('correct_word', '').lower()
        
        if not word_id or not user_answer or not correct_word:
            return jsonify({'error': '参数不完整'}), 400
        
        # 检查拼写是否正确
        is_correct = user_answer == correct_word
        
        # 计算相似度（用于提供反馈）
        similarity = calculate_similarity(user_answer, correct_word)
        
        # 记录拼写结果
        with sqlite3.connect(app.config['DATABASE']) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO learning_history (user_id, word_id, action, details)
                VALUES (?, ?, ?, ?)
            ''', (user_id, word_id, 'spelling_result', 
                  f'拼写练习: 用户答案 "{user_answer}", 正确答案 "{correct_word}", 正确: {is_correct}'))
            
            conn.commit()
        
        # 分析错误类型
        error_analysis = None
        if not is_correct:
            error_analysis = analyze_spelling_error(user_answer, correct_word)
        
        return jsonify({
            'success': True,
            'is_correct': is_correct,
            'similarity': similarity,
            'error_analysis': error_analysis,
            'correct_word': correct_word,
            'feedback': get_spelling_feedback(is_correct, similarity, error_analysis)
        })
        
    except Exception as e:
        logger.error(f"Error in api_check_spelling: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

def calculate_similarity(str1, str2):
    """计算两个字符串的相似度"""
    if not str1 or not str2:
        return 0
    
    # 使用编辑距离计算相似度
    def levenshtein_distance(s1, s2):
        if len(s1) < len(s2):
            return levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    distance = levenshtein_distance(str1, str2)
    max_len = max(len(str1), len(str2))
    
    if max_len == 0:
        return 1
    
    return 1 - (distance / max_len)

def analyze_spelling_error(user_answer, correct_word):
    """分析拼写错误类型"""
    errors = []
    
    # 长度错误
    if len(user_answer) != len(correct_word):
        errors.append({
            'type': 'length',
            'user_length': len(user_answer),
            'correct_length': len(correct_word)
        })
    
    # 逐个字母比较
    wrong_positions = []
    min_len = min(len(user_answer), len(correct_word))
    
    for i in range(min_len):
        if user_answer[i] != correct_word[i]:
            wrong_positions.append({
                'position': i + 1,
                'user_char': user_answer[i],
                'correct_char': correct_word[i]
            })
    
    if wrong_positions:
        errors.append({
            'type': 'wrong_letters',
            'positions': wrong_positions
        })
    
    # 检查常见拼写错误模式
    common_errors = {
        'ie': 'ei',
        'ei': 'ie',
        'ph': 'f',
        'f': 'ph',
        'c': 'k',
        'k': 'c',
        's': 'c',
        'c': 's'
    }
    
    for i in range(len(user_answer) - 1):
        pair = user_answer[i:i+2]
        if pair in common_errors:
            errors.append({
                'type': 'common_pattern',
                'user_pair': pair,
                'suggestion': common_errors[pair]
            })
    
    return errors

def get_spelling_feedback(is_correct, similarity, error_analysis):
    """生成拼写反馈"""
    if is_correct:
        return "拼写正确！很棒！"
    
    feedback = "拼写不正确。"
    
    if error_analysis:
        for error in error_analysis:
            if error['type'] == 'length':
                feedback += f" 单词长度错误（你的: {error['user_length']}，正确: {error['correct_length']}）。"
            elif error['type'] == 'wrong_letters':
                positions = [str(p['position']) for p in error['positions'][:3]]  # 只显示前3个错误位置
                feedback += f" 第{', '.join(positions)}个字母错误。"
            elif error['type'] == 'common_pattern':
                feedback += f" 注意 '{error['user_pair']}' 常被误写为 '{error['suggestion']}'。"
    
    if similarity > 0.7:
        feedback += " 已经很接近了，再试一次！"
    elif similarity > 0.5:
        feedback += " 有些字母是正确的，继续努力！"
    else:
        feedback += " 建议多听几遍发音，注意字母顺序。"
    
    return feedback

if __name__ == '__main__':
    print("正在初始化VisWords应用...")
    
    # 确保数据库和表已创建
    init_db()
    
    # 检查是否需要添加示例数据                             
    
    # 检查API密钥
    if not ARK_API_KEY or ARK_API_KEY == "您的豆包API密钥":
        print("\n⚠️ 警告: 未配置豆包API密钥，AI功能将使用模拟数据")
        print("如需使用完整AI功能，请按以下方式配置：")
        print("1. 在app.py中修改ARK_API_KEY变量")
        print("2. 或设置环境变量：export ARK_API_KEY=8'your-actual-api-key'")
        print("3. 或在Windows上：set ARK_API_KEY=your-actual-api-key")
    else:
        print(f"\n✅ 豆包API密钥已配置，AI功能已启用")
    
    print("\nVisWords应用启动成功！")
    print("访问地址: http://127.0.0.1:5000")
    print("API文档: http://127.0.0.1:5000/api/health")
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug, host='0.0.0.0', port=port)