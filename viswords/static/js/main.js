// 全局状态
const AppState = {
    user: null,
    words: [],
    customWords: [],
    learnedWords: [],
    currentWordIndex: 0,
    testData: null,
    currentMode: 'learn',
    translationTest: null,
    learningHistory: [],
    testHistory: [],
    translationHistory: [],
    famousQuotes: [],           // 名人名言数组
    currentQuoteIndex: 0,       // 当前显示的名言索引
    timerInterval: null,        // 计时器间隔
    timerRemaining: 25 * 60,    // 剩余时间（秒）
    timerRunning: false,        // 计时器是否运行中
    timerTotalTime: 25 * 60,    // 总时间（秒）
    currentSpellingWord: null,  // 当前拼写单词
    spellingStats: {            // 拼写统计
        correct: 0,
        wrong: 0,
        total: 0
},
}
// API基础URL - 修改为正确的后端地址
const API_BASE = 'http://localhost:5000/api';

// 初始化应用
document.addEventListener('DOMContentLoaded', function() {
    initEventListeners();
    checkUserSession();
});

// 初始化事件监听器
function initEventListeners() {
    // 模式切换
    document.querySelectorAll('.menu-btn[data-mode]').forEach(btn => {
        btn.addEventListener('click', function() {
            const mode = this.dataset.mode;
            switchMode(mode);
            // 更新按钮状态
            document.querySelectorAll('.menu-btn[data-mode]').forEach(b => {
                b.classList.remove('active');
            });
            this.classList.add('active');
        });
    });

    // 单词库切换
    document.querySelectorAll('.menu-btn[data-level]').forEach(btn => {
        btn.addEventListener('click', function() {
            const level = this.dataset.level;
            loadWordList(level);
        });
    });

    // 开始学习按钮
    const startBtn = document.getElementById('start-learning-btn');
    if (startBtn) {
        startBtn.addEventListener('click', initUser);
    }

    // 单词导航
    const prevBtn = document.getElementById('prev-word');
    const nextBtn = document.getElementById('next-word');
    const shuffleBtn = document.getElementById('shuffle-words');
    
    if (prevBtn) prevBtn.addEventListener('click', showPrevWord);
    if (nextBtn) nextBtn.addEventListener('click', showNextWord);
    if (shuffleBtn) shuffleBtn.addEventListener('click', shuffleWords);

    // 单词状态按钮
    document.querySelectorAll('.status-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const status = this.dataset.status;
            updateWordStatus(status);
        });
    });

    // 音频播放
    const playUk = document.getElementById('play-uk');
    const playUs = document.getElementById('play-us');
    if (playUk) playUk.addEventListener('click', () => playAudio('uk'));
    if (playUs) playUs.addEventListener('click', () => playAudio('us'));

    // 测试相关
    const startTestBtn = document.getElementById('start-test-btn');
    const generateTestBtn = document.getElementById('generate-test-btn');
    const submitTestBtn = document.getElementById('submit-test');
    const retryTestBtn = document.getElementById('retry-test');
    const checkSentenceBtn = document.getElementById('check-sentence');
    const showAnswersBtn = document.getElementById('show-answers-btn');
    
    if (startTestBtn) startTestBtn.addEventListener('click', generateTest);
    if (generateTestBtn) generateTestBtn.addEventListener('click', generateTest);
    if (submitTestBtn) submitTestBtn.addEventListener('click', submitTest);
    if (retryTestBtn) retryTestBtn.addEventListener('click', generateTest);
    if (checkSentenceBtn) checkSentenceBtn.addEventListener('click', checkSentence);
    if (showAnswersBtn) showAnswersBtn.addEventListener('click', showTestAnswers);

    // 图片上传
    const selectImageBtn = document.getElementById('select-image-btn');
    const cameraBtn = document.getElementById('camera-btn');
    const captureBtn = document.getElementById('capture-btn');
    const closeCameraBtn = document.getElementById('close-camera');
    const newImageBtn = document.getElementById('new-image');
    const imageUpload = document.getElementById('image-upload');
    
    if (selectImageBtn) selectImageBtn.addEventListener('click', () => imageUpload.click());
    if (cameraBtn) cameraBtn.addEventListener('click', startCamera);
    if (captureBtn) captureBtn.addEventListener('click', capturePhoto);
    if (closeCameraBtn) closeCameraBtn.addEventListener('click', stopCamera);
    if (newImageBtn) newImageBtn.addEventListener('click', resetImageUpload);
    if (imageUpload) imageUpload.addEventListener('change', handleImageUpload);

    // 拖拽上传
    const uploadBox = document.getElementById('upload-box');
    if (uploadBox) {
        uploadBox.addEventListener('dragover', handleDragOver);
        uploadBox.addEventListener('drop', handleDrop);
    }

    // 新增：自我学习词库按钮
    const learnedWordsBtn = document.getElementById('learned-words-btn');
    const customWordsBtn = document.getElementById('custom-words-btn');
    const translationTestBtn = document.getElementById('translation-test-btn');
    const learningHistoryBtn = document.getElementById('learning-history-btn');
    const testHistoryBtn = document.getElementById('test-history-btn');
    const translationHistoryBtn = document.getElementById('translation-history-btn');
    
    if (learnedWordsBtn) learnedWordsBtn.addEventListener('click', () => switchMode('learned'));
    if (customWordsBtn) customWordsBtn.addEventListener('click', () => switchMode('custom'));
    if (translationTestBtn) translationTestBtn.addEventListener('click', () => switchMode('translation'));
    if (learningHistoryBtn) learningHistoryBtn.addEventListener('click', () => switchMode('history'));
    if (testHistoryBtn) testHistoryBtn.addEventListener('click', () => switchMode('test-history'));
    if (translationHistoryBtn) translationHistoryBtn.addEventListener('click', () => switchMode('translation-history'));

    // 新增：添加自定义单词
    const addCustomWordBtn = document.getElementById('add-custom-word-btn');
    const saveCustomWordBtn = document.getElementById('save-custom-word');
    const cancelCustomWordBtn = document.getElementById('cancel-custom-word');
    
    if (addCustomWordBtn) addCustomWordBtn.addEventListener('click', showAddCustomWordForm);
    if (saveCustomWordBtn) saveCustomWordBtn.addEventListener('click', saveCustomWord);
    if (cancelCustomWordBtn) cancelCustomWordBtn.addEventListener('click', hideAddCustomWordForm);

    // 新增：翻译测试相关
    const startTranslationBtn = document.getElementById('start-translation-btn');
    const startTranslationBtn2 = document.getElementById('start-translation-btn2');
    const submitTranslationBtn = document.getElementById('submit-translation');
    const skipTranslationBtn = document.getElementById('skip-translation');
    const translationHistoryBtn2 = document.getElementById('translation-history-btn2');
    
    if (startTranslationBtn) startTranslationBtn.addEventListener('click', startRandomTranslationTest);
    if (startTranslationBtn2) startTranslationBtn2.addEventListener('click', startRandomTranslationTest);
    if (submitTranslationBtn) submitTranslationBtn.addEventListener('click', submitTranslation);
    if (skipTranslationBtn) skipTranslationBtn.addEventListener('click', skipTranslation);
    if (translationHistoryBtn2) translationHistoryBtn2.addEventListener('click', () => switchMode('translation-history'));

    // 新增：导出和刷新
    const exportLearnedBtn = document.getElementById('export-learned-btn');
    const refreshHistoryBtn = document.getElementById('refresh-history-btn');
    
    if (exportLearnedBtn) exportLearnedBtn.addEventListener('click', exportLearnedWords);
    if (refreshHistoryBtn) refreshHistoryBtn.addEventListener('click', loadLearningHistory);

    // 新增：删除单词
    document.addEventListener('click', function(event) {
        if (event.target.classList.contains('delete-word-btn')) {
            const wordId = event.target.dataset.wordId;
            if (wordId && confirm('确定要删除这个单词吗？')) {
                deleteCustomWord(wordId);
            }
        }
    });

    // 新增：开始特定单词的翻译测试
    document.addEventListener('click', function(event) {
        if (event.target.classList.contains('start-translation-for-word')) {
            const wordId = event.target.dataset.wordId;
            startTranslationForWord(wordId);
        }
    });
 // 新增：名人名言相关
    const showQuoteBtn = document.getElementById('show-quote');
    const modalCloseBtns = document.querySelectorAll('.modal-close');
    const closeQuoteBtn = document.getElementById('close-quote');
    const nextQuoteBtn = document.getElementById('next-quote');
    
    if (showQuoteBtn) showQuoteBtn.addEventListener('click', showQuoteModal);
    if (closeQuoteBtn) closeQuoteBtn.addEventListener('click', hideQuoteModal);
    if (nextQuoteBtn) nextQuoteBtn.addEventListener('click', showNextQuote);
    
    modalCloseBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const modal = this.closest('.modal');
            if (modal) {
                modal.style.display = 'none';
            }
        });
    });
    
    // 新增：倒计时相关
    const showTimerBtn = document.getElementById('show-timer');
    const startTimerBtn = document.getElementById('start-timer');
    const pauseTimerBtn = document.getElementById('pause-timer');
    const resetTimerBtn = document.getElementById('reset-timer');
    const timePresets = document.querySelectorAll('.time-preset');
    const customMinutesInput = document.getElementById('custom-minutes');
    
    if (showTimerBtn) showTimerBtn.addEventListener('click', showTimerModal);
    if (startTimerBtn) startTimerBtn.addEventListener('click', startTimer);
    if (pauseTimerBtn) pauseTimerBtn.addEventListener('click', pauseTimer);
    if (resetTimerBtn) resetTimerBtn.addEventListener('click', resetTimer);
    if (customMinutesInput) customMinutesInput.addEventListener('change', updateCustomTime);
    
    timePresets.forEach(preset => {
        preset.addEventListener('click', function() {
            const minutes = parseInt(this.dataset.minutes);
            setTimerTime(minutes * 60);
            
            // 更新激活状态
            timePresets.forEach(p => p.classList.remove('active'));
            this.classList.add('active');
        });
    });
    
    // 新增：拼写练习相关
    const showSpellingBtn = document.getElementById('show-spelling');
    const checkSpellingBtn = document.getElementById('check-spelling');
    const newSpellingWordBtn = document.getElementById('new-spelling-word');
    const skipSpellingBtn = document.getElementById('skip-spelling');
    const showHintBtn = document.getElementById('show-hint');
    const spellingAnswerInput = document.getElementById('spelling-answer');
    
    if (showSpellingBtn) showSpellingBtn.addEventListener('click', showSpellingModal);
    if (checkSpellingBtn) checkSpellingBtn.addEventListener('click', checkSpelling);
    if (newSpellingWordBtn) newSpellingWordBtn.addEventListener('click', getNewSpellingWord);
    if (skipSpellingBtn) skipSpellingBtn.addEventListener('click', getNewSpellingWord);
    if (showHintBtn) showHintBtn.addEventListener('click', showMoreHint);
    if (spellingAnswerInput) {
        spellingAnswerInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                checkSpelling();
            }
        });
    }
    
    // 点击模态框外部关闭
    window.addEventListener('click', function(event) {
        if (event.target.classList.contains('modal')) {
            event.target.style.display = 'none';
        }
    });
    
    // 页面加载时显示名言弹窗
    setTimeout(() => {
        loadFamousQuotes();
        setTimeout(showQuoteModal, 1000);
    }, 1000);

}

// 检查用户会话
async function checkUserSession() {
    try {
        // 尝试从localStorage获取用户信息
        const userId = localStorage.getItem('userId');
        const username = localStorage.getItem('username');
        
        if (userId && username) {
            AppState.user = { id: userId, username };
            document.getElementById('username').textContent = username;
            
            // 尝试连接到后端验证用户
            try {
                const response = await fetch(`${API_BASE}/get_learning_progress`);
                if (response.ok) {
                    const data = await response.json();
                    if (data.user_id) {
                        await loadWordList('CET-4');
                        switchMode('learn');
                        updateProgress();
                        return;
                    }
                }
            } catch (error) {
                console.log('后端连接失败，使用本地存储的用户信息');
            }
            
            // 如果后端连接失败，仍然显示欢迎界面
            showSection('welcome');
        } else {
            showSection('welcome');
        }
    } catch (error) {
        console.log('检查用户会话失败:', error);
        showSection('welcome');
    }
}

// 初始化用户
async function initUser() {
    const usernameInput = document.getElementById('username-input');
    const username = usernameInput.value || '学习者';
    const level = document.querySelector('input[name="level"]:checked').value;

    try {
        const response = await fetch(`${API_BASE}/init_user`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        
        if (data.user_id) {
            // 保存用户信息到本地存储
            localStorage.setItem('userId', data.user_id);
            localStorage.setItem('username', data.username);
            
            AppState.user = { id: data.user_id, username: data.username, level };
            document.getElementById('username').textContent = data.username;
            
            await loadWordList(level);
            switchMode('learn');
            updateProgress();
        }
    } catch (error) {
        console.error('初始化用户失败:', error);
        alert('初始化失败，请检查后端服务是否启动');
    }
}

// 切换模式
function switchMode(mode) {
    showSection(mode);
    AppState.currentMode = mode;

    switch(mode) {
        case 'learn':
            if (AppState.words.length > 0) {
                showWord(AppState.currentWordIndex);
            }
            break;
        case 'test':
            showTestWelcome();
            break;
        case 'image':
            resetImageUpload();
            break;
        case 'learned':
            loadLearnedWords();
            break;
        case 'custom':
            loadCustomWords();
            break;
        case 'translation':
            showTranslationWelcome();
            break;
        case 'history':
            loadLearningHistory();
            break;
        case 'test-history':
            loadTestHistory();
            break;
        case 'translation-history':
            loadTranslationHistory();
            break;
    }
}

// 显示指定部分
function showSection(sectionId) {
    document.querySelectorAll('.section').forEach(section => {
        section.classList.remove('active');
    });
    
    const sectionElement = document.getElementById(`${sectionId}-section`);
    if (sectionElement) {
        sectionElement.classList.add('active');
    }
}

// 加载单词列表
async function loadWordList(level = 'CET-4') {
    try {
        const response = await fetch(`${API_BASE}/get_word_list?level=${level}&limit=50`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.words) {
            AppState.words = data.words;
            AppState.currentWordIndex = 0;
            
            // 更新计数
            updateWordCounts();
            
            if (AppState.words.length > 0) {
                showWord(0);
            }
        }
    } catch (error) {
        console.error('加载单词列表失败:', error);
        alert('无法加载单词列表，请检查网络连接');
    }
}

// 显示单词
function showWord(index) {
    if (index < 0 || index >= AppState.words.length) return;
    
    AppState.currentWordIndex = index;
    const word = AppState.words[index];
    
    // 更新显示
    const currentWordElement = document.getElementById('current-word');
    const phoneticElement = document.getElementById('word-phonetic');
    const definitionEnElement = document.getElementById('definition-en');
    const definitionCnElement = document.getElementById('definition-cn');
    const levelElement = document.getElementById('word-level');
    const exampleElement = document.getElementById('word-example');
    
    if (currentWordElement) currentWordElement.textContent = word.word;
    if (phoneticElement) phoneticElement.textContent = word.phonetic || '';
    if (definitionEnElement) definitionEnElement.textContent = word.definition_en || '';
    if (definitionCnElement) definitionCnElement.textContent = word.definition_cn || '';
    if (levelElement) levelElement.textContent = word.level || 'CET-4';
    if (exampleElement) exampleElement.textContent = word.example_sentence || '';
    
    // 更新计数器
    const counterElement = document.getElementById('word-counter');
    if (counterElement) {
        counterElement.textContent = `${index + 1}/${AppState.words.length}`;
    }
    
    // 更新状态按钮
    updateStatusButtons(word.user_status || 'new');
    
    // 加载相关单词
    if (word.word) {
        loadRelatedWords(word.word);
    }
}

// 更新状态按钮
function updateStatusButtons(status) {
    document.querySelectorAll('.status-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.status === status) {
            btn.classList.add('active');
        }
    });
}

// 更新单词状态
async function updateWordStatus(status) {
    const word = AppState.words[AppState.currentWordIndex];
    
    try {
        const response = await fetch(`${API_BASE}/update_word_status`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                word_id: word.id,
                status: status
            })
        });

        if (response.ok) {
            // 更新本地状态
            AppState.words[AppState.currentWordIndex].user_status = status;
            updateStatusButtons(status);
            updateProgress();
            
            // 如果标记为已掌握，自动进入下一个单词
            if (status === 'mastered') {
                setTimeout(() => showNextWord(), 500);
            }
        }
    } catch (error) {
        console.error('更新单词状态失败:', error);
        alert('更新状态失败，请重试');
    }
}

// 上一个单词
function showPrevWord() {
    if (AppState.currentWordIndex > 0) {
        showWord(AppState.currentWordIndex - 1);
    }
}

// 下一个单词
function showNextWord() {
    if (AppState.currentWordIndex < AppState.words.length - 1) {
        showWord(AppState.currentWordIndex + 1);
    } else {
        // 如果已经是最后一个，重新开始
        AppState.currentWordIndex = 0;
        showWord(0);
    }
}

// 随机打乱单词
function shuffleWords() {
    for (let i = AppState.words.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [AppState.words[i], AppState.words[j]] = [AppState.words[j], AppState.words[i]];
    }
    AppState.currentWordIndex = 0;
    showWord(0);
}

// 播放音频
function playAudio(type) {
    const word = AppState.words[AppState.currentWordIndex];
    
    if (!word || !word.word) return;
    
    // 使用浏览器TTS
    if ('speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(word.word);
        utterance.lang = type === 'uk' ? 'en-GB' : 'en-US';
        utterance.rate = 0.8;
        utterance.pitch = 1.0;
        utterance.volume = 1.0;
        
        // 停止任何正在播放的语音
        speechSynthesis.cancel();
        
        // 播放新语音
        speechSynthesis.speak(utterance);
    } else {
        alert('您的浏览器不支持语音合成功能');
    }
}

// 加载相关单词
async function loadRelatedWords(word) {
    try {
        const response = await fetch(`${API_BASE}/search_word?word=${word}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.found) {
            // 显示相关单词
            const container = document.getElementById('related-words-list');
            if (container) {
                container.innerHTML = '';
                
                // 创建相关单词数组
                const relatedWords = [
                    {word: 'leave', meaning: '离开'},
                    {word: 'desert', meaning: '遗弃'},
                    {word: 'quit', meaning: '放弃'},
                    {word: 'give up', meaning: '放弃'},
                    {word: 'forsake', meaning: '抛弃'}
                ];
                
                relatedWords.forEach(relatedWord => {
                    const tag = document.createElement('span');
                    tag.className = 'tag';
                    tag.textContent = `${relatedWord.word} (${relatedWord.meaning})`;
                    tag.addEventListener('click', () => searchWord(relatedWord.word));
                    container.appendChild(tag);
                });
            }
        }
    } catch (error) {
        console.error('加载相关单词失败:', error);
    }
}

// 搜索单词
// 搜索单词
async function searchWord(word) {
    try {
        const response = await fetch(`${API_BASE}/search_word?word=${word}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.found) {
            // 添加到单词列表并显示
            const newWord = {
                id: data.id || Date.now(), // 使用数据库ID或临时ID
                word: data.word,
                phonetic: data.phonetic || '',
                definition_en: data.definition_en || '',
                definition_cn: data.definition_cn || '',
                level: data.level || 'CET-4',
                example_sentence: data.example || '',
                user_status: 'new'
            };
            
            AppState.words.unshift(newWord);
            AppState.currentWordIndex = 0;
            showWord(0);
            
            // 显示成功消息
            alert(`已添加单词 "${word}" 到学习列表`);
        } else {
            alert(`未找到单词 "${word}"`);
        }
    } catch (error) {
        console.error('搜索单词失败:', error);
        alert('搜索单词失败，请检查网络连接');
    }
}
// 更新单词计数
function updateWordCounts() {
    const counts = {
        'CET-4': 0,
        'CET-6': 0,
        mastered: 0,
        learning: 0,
        known: 0,
        custom: 0
    };
    
    AppState.words.forEach(word => {
        if (word.level === 'CET-4') counts['CET-4']++;
        if (word.level === 'CET-6') counts['CET-6']++;
        if (word.user_status === 'mastered') counts.mastered++;
        if (word.user_status === 'learning') counts.learning++;
        if (word.user_status === 'known') counts.known++;
        if (word.level === 'custom' || word.source === 'user') counts.custom++;
    });
    
    // 更新显示
    const cet4CountElement = document.getElementById('cet4-count');
    const cet6CountElement = document.getElementById('cet6-count');
    const masteredCountElement = document.getElementById('mastered-count');
    const learningCountElement = document.getElementById('learning-count');
    const knownCountElement = document.getElementById('known-count');
    const customCountElement = document.getElementById('custom-count');
    const learnedCountElement = document.getElementById('learned-count');
    
    if (cet4CountElement) cet4CountElement.textContent = counts['CET-4'];
    if (cet6CountElement) cet6CountElement.textContent = counts['CET-6'];
    if (masteredCountElement) masteredCountElement.textContent = counts.mastered;
    if (learningCountElement) learningCountElement.textContent = counts.learning;
    if (knownCountElement) knownCountElement.textContent = counts.known;
    if (customCountElement) customCountElement.textContent = counts.custom;
    if (learnedCountElement) learnedCountElement.textContent = counts.mastered;
}

// 更新学习进度
async function updateProgress() {
    try {
        const response = await fetch(`${API_BASE}/get_learning_progress`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.progress) {
            // 更新进度显示
            const masteredElement = document.getElementById('mastered-count');
            const learningElement = document.getElementById('learning-count');
            const knownElement = document.getElementById('known-count');
            const learnedCountElement = document.getElementById('learned-count');
            const totalWordsElement = document.getElementById('total-words');
            const todayActivitiesElement = document.getElementById('today-activities');
            const streakDaysElement = document.getElementById('streak-days');
            
            if (masteredElement) masteredElement.textContent = data.progress.mastered;
            if (learningElement) learningElement.textContent = data.progress.learning;
            if (knownElement) knownElement.textContent = data.progress.known;
            if (learnedCountElement) learnedCountElement.textContent = data.progress.mastered;
            if (totalWordsElement) totalWordsElement.textContent = data.progress.total;
            if (todayActivitiesElement) todayActivitiesElement.textContent = data.today_activities || 0;
            if (streakDaysElement) streakDaysElement.textContent = `${data.streak_days} 天`;
        }
    } catch (error) {
        console.error('更新进度失败:', error);
    }
}

// 生成测试
async function generateTest() {
    try {
        const response = await fetch(`${API_BASE}/generate_test`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({})
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        AppState.testData = data;
        
        displayTest(data);
        
        // 隐藏欢迎界面，显示测试内容
        const testWelcome = document.getElementById('test-welcome');
        const testContent = document.getElementById('test-content');
        if (testWelcome) testWelcome.style.display = 'none';
        if (testContent) testContent.style.display = 'block';
    } catch (error) {
        console.error('生成测试失败:', error);
        alert('生成测试失败，请先学习一些单词');
        
        // 显示示例测试
        displayExampleTest();
    }
}

// 显示测试
// 显示测试
function displayTest(testData) {
    // 显示句子 - 修复这里
    const sentenceElement = document.getElementById('test-paragraph');
    if (sentenceElement) sentenceElement.textContent = testData.sentence;
    
    // 显示问题
    const questionsList = document.getElementById('questions-list');
    if (questionsList) {
        questionsList.innerHTML = '';
        
        if (testData.questions && Array.isArray(testData.questions)) {
            testData.questions.forEach((question, index) => {
                const questionDiv = document.createElement('div');
                questionDiv.className = 'question-item';
                questionDiv.innerHTML = `
                    <div class="question-text">${index + 1}. ${question.question}</div>
                    <div class="options">
                        ${question.options.map((option, i) => `
                            <button class="option-btn" data-question="${index}" data-option="${i}">
                                ${String.fromCharCode(65 + i)}. ${option}
                            </button>
                        `).join('')}
                    </div>
                `;
                questionsList.appendChild(questionDiv);
            });
        }
    }
    
    // 显示造句练习
    const makeWordElement = document.getElementById('make-word');
    const makeHintElement = document.getElementById('make-hint');
    const sentenceExampleElement = document.getElementById('sentence-example');
    
    if (makeWordElement && testData.make_sentence) {
        makeWordElement.textContent = testData.make_sentence.word;
    }
    if (makeHintElement && testData.make_sentence) {
        makeHintElement.textContent = testData.make_sentence.hint;
    }
    if (sentenceExampleElement && testData.make_sentence && testData.correct_answers && testData.correct_answers.make_sentence) {
        sentenceExampleElement.textContent = `示例: ${testData.correct_answers.make_sentence}`;
    }
    
    // 添加选项选择事件
    setTimeout(() => {
        document.querySelectorAll('.option-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const questionIndex = this.dataset.question;
                const optionIndex = this.dataset.option;
                
                // 移除同一问题的其他选项的选中状态
                document.querySelectorAll(`[data-question="${questionIndex}"]`).forEach(b => {
                    b.classList.remove('selected');
                });
                
                // 选中当前选项
                this.classList.add('selected');
                
                // 保存答案
                if (!AppState.testData.userAnswers) {
                    AppState.testData.userAnswers = {};
                }
                AppState.testData.userAnswers[questionIndex] = String.fromCharCode(65 + parseInt(optionIndex));
            });
        });
    }, 100);
}
// 显示示例测试
function displayExampleTest() {
    const exampleTest = {
        "sentence": "The diligent student prepared for the exam with enthusiasm and determination.",
        "questions": [
            {
                "question": "What is the main purpose of the sentence?",
                "options": ["To describe a student", "To explain an exam", "To show preparation", "All of the above"],
                "answer": "D"
            },
            {
                "question": "Which word shows the student's attitude?",
                "options": ["diligent", "prepared", "exam", "CET-6"],
                "answer": "A"
            },
            {
                "question": "What could be a synonym for 'diligent'?",
                "options": ["lazy", "hardworking", "smart", "quick"],
                "answer": "B"
            }
        ],
        "make_sentence": {
            "word": "study",
            "hint": "Use this word to describe your learning process"
        },
        "correct_answers": {
            "questions": [
                "The sentence describes a student's preparation for an exam, so 'All of the above' is correct.",
                "'Diligent' means hardworking and shows the student's attitude.",
                "A synonym for 'diligent' is 'hardworking'."
            ],
            "make_sentence": "Example: I need to study regularly to improve my English."
        }
    };
    
    AppState.testData = exampleTest;
    displayTest(exampleTest);
    
    const testWelcome = document.getElementById('test-welcome');
    const testContent = document.getElementById('test-content');
    if (testWelcome) testWelcome.style.display = 'none';
    if (testContent) testContent.style.display = 'block';
}

// 检查造句
function checkSentence() {
    const sentenceInput = document.getElementById('sentence-input');
    const makeWordElement = document.getElementById('make-word');
    
    if (!sentenceInput || !makeWordElement) return;
    
    const userSentence = sentenceInput.value.trim();
    const targetWord = makeWordElement.textContent.toLowerCase();
    
    if (!userSentence) {
        alert('请输入一个句子');
        return;
    }
    
    if (userSentence.toLowerCase().includes(targetWord)) {
        alert('✓ 很好！你的句子中包含了目标单词。');
    } else {
        alert('⚠ 你的句子中没有包含目标单词 "' + targetWord + '"，请重新造句。');
    }
}

// 显示测试正确答案
function showTestAnswers() {
    if (!AppState.testData || !AppState.testData.correct_answers) {
        alert('暂无正确答案信息');
        return;
    }
    
    const answers = AppState.testData.correct_answers;
    let message = '📝 正确答案：\n\n';
    
    // 显示选择题答案
    if (answers.questions && Array.isArray(answers.questions)) {
        message += '选择题：\n';
        answers.questions.forEach((answer, index) => {
            const question = AppState.testData.questions[index];
            message += `${index + 1}. ${question.question}\n`;
            message += `   正确答案：${question.answer}\n`;
            message += `   解释：${answer}\n\n`;
        });
    }
    
    // 显示造句答案
    if (answers.make_sentence) {
        message += '造句练习：\n';
        message += `建议例句：${answers.make_sentence}\n`;
    }
    
    alert(message);
}

// 提交测试
async function submitTest() {
    if (!AppState.testData) return;
    
    const userAnswers = AppState.testData.userAnswers || {};
    const userSentence = document.getElementById('sentence-input').value.trim();
    
    try {
        const response = await fetch(`${API_BASE}/submit_test`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                test_data: AppState.testData,
                user_answers: userAnswers,
                user_sentence: userSentence
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        
        let message = `测试完成！\n得分: ${data.score}/${data.total} (${data.percentage.toFixed(1)}%)\n\n`;
        
        // 显示每道题的对错
        if (data.correct_answers && Array.isArray(data.correct_answers)) {
            message += '详细结果：\n';
            data.correct_answers.forEach((isCorrect, index) => {
                message += `第${index + 1}题: ${isCorrect ? '✓ 正确' : '✗ 错误'}\n`;
            });
        }
        
        alert(message);
        
        // 询问是否查看正确答案
        if (confirm('是否查看详细答案解析？')) {
            showTestAnswers();
        }
        
        // 重置测试界面
        showTestWelcome();
    } catch (error) {
        console.error('提交测试失败:', error);
        alert('提交测试失败，请重试');
    }
}

// 显示测试欢迎界面
function showTestWelcome() {
    const testWelcome = document.getElementById('test-welcome');
    const testContent = document.getElementById('test-content');
    const sentenceInput = document.getElementById('sentence-input');
    
    if (testWelcome) testWelcome.style.display = 'block';
    if (testContent) testContent.style.display = 'none';
    if (sentenceInput) sentenceInput.value = '';
    
    if (AppState.testData?.userAnswers) {
        delete AppState.testData.userAnswers;
    }
}

// 处理图片上传
function handleImageUpload(event) {
    const file = event.target.files[0];
    if (file) {
        // 检查文件类型
        if (!file.type.match('image.*')) {
            alert('请选择图片文件');
            return;
        }
        
        // 检查文件大小（最大16MB）
        if (file.size > 16 * 1024 * 1024) {
            alert('图片文件过大，请选择小于16MB的图片');
            return;
        }
        
        processImage(file);
    }
}

// 开始摄像头
async function startCamera() {
    try {
        const constraints = {
            video: {
                facingMode: 'environment',
                width: { ideal: 1280 },
                height: { ideal: 720 }
            }
        };
        
        const stream = await navigator.mediaDevices.getUserMedia(constraints);
        
        const video = document.getElementById('camera-video');
        if (video) {
            video.srcObject = stream;
            video.play();
        }
        
        const uploadBox = document.getElementById('upload-box');
        const cameraContainer = document.getElementById('camera-container');
        
        if (uploadBox) uploadBox.style.display = 'none';
        if (cameraContainer) cameraContainer.style.display = 'block';
    } catch (error) {
        console.error('摄像头访问失败:', error);
        alert('无法访问摄像头，请检查权限设置或使用文件上传功能');
    }
}

// 拍照
function capturePhoto() {
    const video = document.getElementById('camera-video');
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    canvas.toBlob(function(blob) {
        processImage(blob);
    }, 'image/jpeg', 0.8);
    
    // 停止摄像头
    stopCamera();
}

// 停止摄像头
function stopCamera() {
    const video = document.getElementById('camera-video');
    const stream = video.srcObject;
    
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
        video.srcObject = null;
    }
    
    const uploadBox = document.getElementById('upload-box');
    const cameraContainer = document.getElementById('camera-container');
    
    if (uploadBox) uploadBox.style.display = 'block';
    if (cameraContainer) cameraContainer.style.display = 'none';
}

// 处理图片
async function processImage(blob) {
    // 显示加载状态
    const uploadBox = document.getElementById('upload-box');
    if (uploadBox) {
        uploadBox.innerHTML = '<i class="fas fa-spinner fa-spin"></i><h3>正在识别图片...</h3>';
    }
    
    const formData = new FormData();
    formData.append('image', blob, 'photo.jpg');
    
    try {
        const response = await fetch(`${API_BASE}/analyze_image`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        displayImageResult(blob, data);
    } catch (error) {
        console.error('图片处理失败:', error);
        
        // 恢复上传界面
        resetImageUpload();
        
        // 显示示例数据
        const exampleData = {
            description: "这是一个示例图片描述，因为AI识别功能需要API密钥。请在后端app.py中配置豆包API密钥以启用完整功能。",
            words: [
                {"word": "landscape", "phonetic": "/ˈlændskeɪp/", "definition_en": "all the visible features of an area of land", "definition_cn": "风景, 景观"},
                {"word": "nature", "phonetic": "/ˈneɪtʃər/", "definition_en": "the physical world and everything in it", "definition_cn": "自然, 自然界"},
                {"word": "mountain", "phonetic": "/ˈmaʊntən/", "definition_en": "a large natural elevation of the earth's surface", "definition_cn": "山, 山脉"},
                {"word": "tree", "phonetic": "/triː/", "definition_en": "a woody perennial plant", "definition_cn": "树, 树木"},
                {"word": "sky", "phonetic": "/skaɪ/", "definition_en": "the region of the atmosphere above the earth", "definition_cn": "天空"}
            ],
            image_url: ""
        };
        
        displayImageResult(blob, exampleData);
        alert('AI识别功能需要API密钥。请在后端app.py中配置豆包API密钥以启用完整功能。');
    }
}

// 显示图片识别结果
function displayImageResult(blob, result) {
    // 显示图片
    const imageUrl = URL.createObjectURL(blob);
    const resultImage = document.getElementById('result-image');
    if (resultImage) {
        resultImage.src = imageUrl;
        resultImage.onload = () => URL.revokeObjectURL(imageUrl);
    }
    
    // 显示描述
    const descriptionElement = document.getElementById('image-description');
    if (descriptionElement) {
        descriptionElement.textContent = result.description || 'AI识别了图片内容';
    }
    
    // 显示推荐单词
    displaySuggestedWords(result.words || []);
    
    // 显示结果区域
    const uploadBox = document.getElementById('upload-box');
    const imageResult = document.getElementById('image-result');
    
    if (uploadBox) {
        // 恢复上传界面内容
        uploadBox.innerHTML = `
            <i class="fas fa-cloud-upload-alt"></i>
            <h3>拖拽图片到此处，或点击选择</h3>
            <p>支持 JPG, PNG, GIF 格式，最大16MB</p>
            <button id="select-image-btn" class="btn-primary">
                <i class="fas fa-folder-open"></i> 选择图片
            </button>
            <button id="camera-btn" class="btn-secondary">
                <i class="fas fa-camera"></i> 拍照
            </button>
        `;
        
        // 重新绑定事件
        const selectImageBtn = document.getElementById('select-image-btn');
        const cameraBtn = document.getElementById('camera-btn');
        const imageUpload = document.getElementById('image-upload');
        
        if (selectImageBtn) selectImageBtn.addEventListener('click', () => imageUpload.click());
        if (cameraBtn) cameraBtn.addEventListener('click', startCamera);
    }
    
    if (imageResult) imageResult.style.display = 'block';
}

// 显示推荐单词
function displaySuggestedWords(words) {
    const container = document.getElementById('suggested-words');
    if (!container) return;
    
    container.innerHTML = '';
    
    // 限制显示5个单词
    const displayWords = words.slice(0, 5);
    
    displayWords.forEach(word => {
        const wordCard = document.createElement('div');
        wordCard.className = 'word-card';
        wordCard.innerHTML = `
            <h4>${word.word}</h4>
            <p class="phonetic">${word.phonetic || ''}</p>
            <p class="definition-en">${word.definition_en || ''}</p>
            <p class="definition-cn">${word.definition_cn || ''}</p>
            <button class="learn-btn">学习这个单词</button>
        `;
        
        // 添加学习按钮事件
        const learnBtn = wordCard.querySelector('.learn-btn');
        if (learnBtn) {
            learnBtn.addEventListener('click', () => {
                searchWord(word.word);
                switchMode('learn');
            });
        }
        
        // 点击整个卡片也可以学习单词
        wordCard.addEventListener('click', (e) => {
            if (e.target !== learnBtn) {
                searchWord(word.word);
                switchMode('learn');
            }
        });
        
        container.appendChild(wordCard);
    });
    
    // 如果没有单词，显示提示
    if (displayWords.length === 0) {
        container.innerHTML = '<p class="no-words">未识别到相关单词</p>';
    }
}

// 重置图片上传
function resetImageUpload() {
    const uploadBox = document.getElementById('upload-box');
    const cameraContainer = document.getElementById('camera-container');
    const imageResult = document.getElementById('image-result');
    const imageUpload = document.getElementById('image-upload');
    
    if (uploadBox) {
        uploadBox.innerHTML = `
            <i class="fas fa-cloud-upload-alt"></i>
            <h3>拖拽图片到此处，或点击选择</h3>
            <p>支持 JPG, PNG, GIF 格式，最大16MB</p>
            <button id="select-image-btn" class="btn-primary">
                <i class="fas fa-folder-open"></i> 选择图片
            </button>
            <button id="camera-btn" class="btn-secondary">
                <i class="fas fa-camera"></i> 拍照
            </button>
        `;
        
        // 重新绑定事件
        const selectImageBtn = document.getElementById('select-image-btn');
        const cameraBtn = document.getElementById('camera-btn');
        
        if (selectImageBtn) selectImageBtn.addEventListener('click', () => imageUpload.click());
        if (cameraBtn) cameraBtn.addEventListener('click', startCamera);
    }
    
    if (cameraContainer) cameraContainer.style.display = 'none';
    if (imageResult) imageResult.style.display = 'none';
    if (imageUpload) imageUpload.value = '';
}

// 拖拽处理
function handleDragOver(event) {
    event.preventDefault();
    event.stopPropagation();
    event.dataTransfer.dropEffect = 'copy';
}

function handleDrop(event) {
    event.preventDefault();
    event.stopPropagation();
    
    const files = event.dataTransfer.files;
    if (files.length > 0) {
        const file = files[0];
        if (file.type.match('image.*')) {
            processImage(file);
        } else {
            alert('请拖拽图片文件');
        }
    }
}

// =============== 新增功能：自我学习词库 ===============

// 显示已掌握的单词
async function loadLearnedWords() {
    try {
        const response = await fetch(`${API_BASE}/get_word_list?level=learned&limit=100`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        AppState.learnedWords = data.words;
        displayLearnedWords();
    } catch (error) {
        console.error('加载已掌握单词失败:', error);
        alert('加载已掌握单词失败');
    }
}

function displayLearnedWords() {
    const container = document.getElementById('learned-words-list');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (AppState.learnedWords.length === 0) {
        container.innerHTML = '<p class="no-words">暂无已掌握的单词</p>';
        return;
    }
    
    AppState.learnedWords.forEach(word => {
        const wordCard = document.createElement('div');
        wordCard.className = 'word-card';
        wordCard.innerHTML = `
            <h4>${word.word}</h4>
            <p class="phonetic">${word.phonetic || ''}</p>
            <p class="definition">${word.definition_cn || ''}</p>
            ${word.example_sentence ? `<p class="example">${word.example_sentence}</p>` : ''}
            <div class="mastery-info">
                <span class="mastery-score">掌握度: ${word.mastery_score || 0}%</span>
                <span class="review-count">复习: ${word.review_count || 0}次</span>
            </div>
            <div class="actions">
                <button class="btn-secondary start-translation-for-word" data-word-id="${word.id}">
                    翻译测试
                </button>
            </div>
        `;
        
        container.appendChild(wordCard);
    });
}

// 显示自定义单词
async function loadCustomWords() {
    try {
        const response = await fetch(`${API_BASE}/get_word_list?level=custom&limit=100`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        AppState.customWords = data.words;
        displayCustomWords();
    } catch (error) {
        console.error('加载自定义单词失败:', error);
        alert('加载自定义单词失败');
    }
}

function displayCustomWords() {
    const container = document.getElementById('custom-words-list');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (AppState.customWords.length === 0) {
        container.innerHTML = '<p class="no-words">暂无自定义单词，点击"添加新单词"按钮添加</p>';
        return;
    }
    
    AppState.customWords.forEach(word => {
        const wordCard = document.createElement('div');
        wordCard.className = 'word-card';
        wordCard.innerHTML = `
            <h4>${word.word}</h4>
            <p class="phonetic">${word.phonetic || ''}</p>
            <p class="definition">${word.definition_cn || ''}</p>
            ${word.example_sentence ? `<p class="example">${word.example_sentence}</p>` : ''}
            <div class="actions">
                <button class="btn-secondary start-translation-for-word" data-word-id="${word.id}">
                    翻译测试
                </button>
                <button class="btn-danger delete-word-btn" data-word-id="${word.id}">
                    删除
                </button>
            </div>
        `;
        
        container.appendChild(wordCard);
    });
}

// 显示添加自定义单词表单
function showAddCustomWordForm() {
    const form = document.getElementById('add-custom-word-form');
    if (form) {
        form.style.display = 'block';
    }
}

// 隐藏添加自定义单词表单
function hideAddCustomWordForm() {
    const form = document.getElementById('add-custom-word-form');
    if (form) {
        form.style.display = 'none';
        // 清空表单
        document.getElementById('custom-word-input').value = '';
        document.getElementById('custom-phonetic-input').value = '';
        document.getElementById('custom-definition-en-input').value = '';
        document.getElementById('custom-definition-cn-input').value = '';
        document.getElementById('custom-example-input').value = '';
    }
}

// 保存自定义单词
async function saveCustomWord() {
    const word = document.getElementById('custom-word-input').value.trim();
    const phonetic = document.getElementById('custom-phonetic-input').value.trim();
    const definitionEn = document.getElementById('custom-definition-en-input').value.trim();
    const definitionCn = document.getElementById('custom-definition-cn-input').value.trim();
    const example = document.getElementById('custom-example-input').value.trim();
    
    if (!word) {
        alert('请输入单词');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/add_custom_word`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                word: word,
                phonetic: phonetic,
                definition_en: definitionEn,
                definition_cn: definitionCn,
                example_sentence: example
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        alert('自定义单词添加成功！');
        
        // 隐藏表单并重新加载
        hideAddCustomWordForm();
        await loadCustomWords();
        updateProgress();
    } catch (error) {
        console.error('添加自定义单词失败:', error);
        alert('添加失败，请重试');
    }
}

// 删除自定义单词
async function deleteCustomWord(wordId) {
    try {
        const response = await fetch(`${API_BASE}/delete_word`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                word_id: wordId
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        if (data.success) {
            alert('单词删除成功');
            // 重新加载自定义单词
            await loadCustomWords();
            updateProgress();
        }
    } catch (error) {
        console.error('删除单词失败:', error);
        alert('删除失败，请重试');
    }
}

// 导出已掌握的单词
async function exportLearnedWords() {
    try {
        const response = await fetch(`${API_BASE}/export_data`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // 创建JSON文件
        const jsonStr = JSON.stringify(data, null, 2);
        const blob = new Blob([jsonStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        // 创建下载链接
        const a = document.createElement('a');
        a.href = url;
        a.download = `viswords_export_${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        
        // 清理URL
        setTimeout(() => URL.revokeObjectURL(url), 100);
        
        alert(`导出成功！共导出 ${data.word_count} 个单词。`);
    } catch (error) {
        console.error('导出数据失败:', error);
        alert('导出失败，请重试');
    }
}

// =============== 新增功能：翻译测试 ===============

// 显示翻译测试欢迎界面
function showTranslationWelcome() {
    const translationWelcome = document.getElementById('translation-welcome');
    const translationContent = document.getElementById('translation-content');
    
    if (translationWelcome) translationWelcome.style.display = 'block';
    if (translationContent) translationContent.style.display = 'none';
    
    AppState.translationTest = null;
}

// 开始随机翻译测试
async function startRandomTranslationTest() {
    // 先加载已掌握的单词
    await loadLearnedWords();
    
    if (AppState.learnedWords.length === 0) {
        alert('请先掌握一些单词');
        return;
    }
    
    // 随机选择一个已掌握的单词
    const randomIndex = Math.floor(Math.random() * AppState.learnedWords.length);
    const word = AppState.learnedWords[randomIndex];
    
    await startTranslationForWord(word.id);
}

// 开始特定单词的翻译测试
async function startTranslationForWord(wordId) {
    try {
        const response = await fetch(`${API_BASE}/get_translation_test?word_id=${wordId}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        AppState.translationTest = data;
        displayTranslationTest();
    } catch (error) {
        console.error('获取翻译测试失败:', error);
        alert('获取翻译测试失败');
    }
}

// 显示翻译测试
function displayTranslationTest() {
    if (!AppState.translationTest) return;
    
    const translationWelcome = document.getElementById('translation-welcome');
    const translationContent = document.getElementById('translation-content');
    
    if (translationWelcome) translationWelcome.style.display = 'none';
    if (translationContent) translationContent.style.display = 'block';
    
    const word = AppState.translationTest.word;
    const test = AppState.translationTest.test;
    
    // 更新显示
    document.getElementById('translation-word').textContent = word.word;
    document.getElementById('translation-phonetic').textContent = word.phonetic || '';
    document.getElementById('translation-definition').textContent = word.definition_cn || '';
    document.getElementById('translation-sentence-en').textContent = test.sentence_en || '';
    document.getElementById('translation-hint').textContent = test.hint || '注意句子结构和单词用法';
    
    // 清空输入框
    document.getElementById('translation-input').value = '';
}

// 提交翻译
async function submitTranslation() {
    if (!AppState.translationTest) return;
    
    const userTranslation = document.getElementById('translation-input').value.trim();
    
    if (!userTranslation) {
        alert('请输入翻译');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/submit_translation`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                word_id: AppState.translationTest.word.id,
                sentence_en: AppState.translationTest.test.sentence_en,
                user_translation: userTranslation,
                correct_translation: AppState.translationTest.test.sentence_cn
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.is_correct) {
            alert('✓ 翻译正确！');
        } else {
            alert(`⚠ 翻译有待改进。\n你的翻译：${userTranslation}\n参考翻译：${data.correct_translation}`);
        }
        
        // 可以选择开始新的测试
        if (confirm('是否开始新的翻译测试？')) {
            startRandomTranslationTest();
        }
    } catch (error) {
        console.error('提交翻译失败:', error);
        alert('提交翻译失败，请重试');
    }
}

// 跳过翻译测试
function skipTranslation() {
    startRandomTranslationTest();
}

// =============== 新增功能：学习历史 ===============

// 加载学习历史
async function loadLearningHistory() {
    try {
        const response = await fetch(`${API_BASE}/get_learning_history?limit=50`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        AppState.learningHistory = data.history;
        displayLearningHistory();
    } catch (error) {
        console.error('加载学习历史失败:', error);
        alert('加载学习历史失败');
    }
}

function displayLearningHistory() {
    const container = document.getElementById('history-list');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (AppState.learningHistory.length === 0) {
        container.innerHTML = '<p class="no-history">暂无学习历史</p>';
        return;
    }
    
    AppState.learningHistory.forEach(record => {
        const historyItem = document.createElement('div');
        historyItem.className = 'history-item';
        
        // 根据动作类型选择图标
        let icon = 'fas fa-history';
        let color = '#4361ee';
        
        switch(record.action) {
            case 'login':
                icon = 'fas fa-sign-in-alt';
                color = '#4caf50';
                break;
            case 'update_status':
                icon = 'fas fa-flag';
                color = '#ff9800';
                break;
            case 'test_submit':
                icon = 'fas fa-file-alt';
                color = '#9c27b0';
                break;
            case 'translation_test':
            case 'translation_submit':
                icon = 'fas fa-language';
                color = '#3f51b5';
                break;
            case 'custom_add':
                icon = 'fas fa-plus-circle';
                color = '#00bcd4';
                break;
            case 'image_analysis':
                icon = 'fas fa-camera';
                color = '#795548';
                break;
            case 'delete_word':
                icon = 'fas fa-trash';
                color = '#f44336';
                break;
        }
        
        // 格式化时间
        const date = new Date(record.created_at);
        const timeStr = date.toLocaleString();
        
        historyItem.innerHTML = `
            <div class="history-icon" style="background-color: ${color}20; color: ${color};">
                <i class="${icon}"></i>
            </div>
            <div class="history-content">
                <div class="history-action">${getActionText(record.action)}</div>
                <div class="history-details">${record.details || ''}</div>
                ${record.word ? `<div class="history-word">单词: ${record.word} - ${record.definition_cn || ''}</div>` : ''}
            </div>
            <div class="history-time">${timeStr}</div>
        `;
        
        container.appendChild(historyItem);
    });
}

function getActionText(action) {
    const actionMap = {
        'login': '用户登录',
        'update_status': '更新单词状态',
        'test_submit': '提交测试',
        'translation_test': '开始翻译测试',
        'translation_submit': '提交翻译',
        'custom_add': '添加自定义单词',
        'image_analysis': '图片识别',
        'delete_word': '删除单词'
    };
    
    return actionMap[action] || action;
}

// 加载测试历史
async function loadTestHistory() {
    try {
        const response = await fetch(`${API_BASE}/get_test_history?limit=20`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        AppState.testHistory = data.tests;
        displayTestHistory();
    } catch (error) {
        console.error('加载测试历史失败:', error);
        alert('加载测试历史失败');
    }
}

function displayTestHistory() {
    const container = document.getElementById('test-history-list');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (AppState.testHistory.length === 0) {
        container.innerHTML = '<p class="no-history">暂无测试历史</p>';
        return;
    }
    
    AppState.testHistory.forEach(test => {
        const testItem = document.createElement('div');
        testItem.className = 'test-history-item';
        
        // 格式化时间
        const date = new Date(test.created_at);
        const timeStr = date.toLocaleString();
        
        let content = '';
        if (test.type === 'test_result') {
            content = `测试得分: ${test.score || 0}%`;
        } else if (test.type === 'translation') {
            content = '翻译测试';
        }
        
        testItem.innerHTML = `
            <div class="test-history-icon">
                <i class="fas fa-${test.type === 'test_result' ? 'file-alt' : 'language'}"></i>
            </div>
            <div class="test-history-content">
                <div class="test-history-type">${test.type === 'test_result' ? 'AI测试' : '翻译测试'}</div>
                <div class="test-history-details">${content}</div>
            </div>
            <div class="test-history-time">${timeStr}</div>
        `;
        
        container.appendChild(testItem);
    });
}

// 加载翻译历史
async function loadTranslationHistory() {
    try {
        const response = await fetch(`${API_BASE}/get_translation_history?limit=20`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        AppState.translationHistory = data.translations;
        displayTranslationHistory(data.accuracy);
    } catch (error) {
        console.error('加载翻译历史失败:', error);
        alert('加载翻译历史失败');
    }
}

function displayTranslationHistory(accuracy) {
    const container = document.getElementById('translation-history-list');
    if (!container) return;
    
    container.innerHTML = '';
    
    // 显示正确率
    const accuracyElement = document.getElementById('translation-accuracy');
    if (accuracyElement) {
        accuracyElement.textContent = `正确率: ${accuracy || 0}%`;
    }
    
    if (AppState.translationHistory.length === 0) {
        container.innerHTML = '<p class="no-history">暂无翻译测试历史</p>';
        return;
    }
    
    AppState.translationHistory.forEach(translation => {
        const translationItem = document.createElement('div');
        translationItem.className = 'translation-history-item';
        
        // 格式化时间
        const date = new Date(translation.created_at);
        const timeStr = date.toLocaleString();
        
        translationItem.innerHTML = `
            <div class="translation-history-word">
                <strong>${translation.word}</strong> - ${translation.definition_cn || ''}
            </div>
            <div class="translation-history-sentence">
                <div class="sentence-en">${translation.sentence_en || ''}</div>
                <div class="sentence-cn">参考翻译: ${translation.sentence_cn || ''}</div>
                <div class="user-translation">你的翻译: ${translation.user_translation || ''}</div>
            </div>
            <div class="translation-history-result">
                <span class="result-badge ${translation.is_correct ? 'correct' : 'incorrect'}">
                    ${translation.is_correct ? '✓ 正确' : '✗ 错误'}
                </span>
                <span class="translation-history-time">${timeStr}</span>
            </div>
        `;
        
        container.appendChild(translationItem);
    });
}
// 添加新的翻译测试按钮事件监听
document.addEventListener('DOMContentLoaded', function() {
    // 新增：下一题按钮
    const newTranslationTestBtn = document.getElementById('new-translation-test');
    if (newTranslationTestBtn) {
        newTranslationTestBtn.addEventListener('click', startRandomTranslationTest);
    }
    
    // 新增：键盘快捷键支持
    document.addEventListener('keydown', function(event) {
        if (AppState.currentMode === 'translation' && AppState.translationTest) {
            // Ctrl + Enter 提交翻译
            if (event.ctrlKey && event.key === 'Enter') {
                event.preventDefault();
                submitTranslation();
            }
            // Esc 键跳过
            if (event.key === 'Escape') {
                event.preventDefault();
                skipTranslation();
            }
            // Alt + N 下一题
            if (event.altKey && event.key === 'n') {
                event.preventDefault();
                startRandomTranslationTest();
            }
        }
    });
});

function loadFamousQuotes() {
    // 预设的英语学习相关名人名言
    AppState.famousQuotes = [
        {
            text: "The limits of my language are the limits of my world.",
            author: "Ludwig Wittgenstein",
            translation: "语言的限制就是我的世界的限制。"
        },
        {
            text: "To have another language is to possess a second soul.",
            author: "Charlemagne",
            translation: "掌握另一门语言，就拥有了第二个灵魂。"
        },
        {
            text: "Language is the road map of a culture. It tells you where its people come from and where they are going.",
            author: "Rita Mae Brown",
            translation: "语言是文化的路线图，它告诉你这个民族从哪里来，到哪里去。"
        },
        {
            text: "One language sets you in a corridor for life. Two languages open every door along the way.",
            author: "Frank Smith",
            translation: "一种语言让你踏上人生的走廊，两种语言为你打开沿途的每一扇门。"
        },
        {
            text: "Learning another language is not only learning different words for the same things, but learning another way to think about things.",
            author: "Flora Lewis",
            translation: "学习另一种语言不仅仅是学习相同事物的不同词汇，更是学习另一种思考方式。"
        },
        {
            text: "The more languages you know, the more you are human.",
            author: "Tomáš Garrigue Masaryk",
            translation: "你掌握的语言越多，你就越能体现人性。"
        },
        {
            text: "Knowledge of languages is the doorway to wisdom.",
            author: "Roger Bacon",
            translation: "语言知识是通往智慧的大门。"
        },
        {
            text: "Language is the blood of the soul into which thoughts run and out of which they grow.",
            author: "Oliver Wendell Holmes",
            translation: "语言是灵魂的血液，思想在其中流淌并成长。"
        },
        {
            text: "A different language is a different vision of life.",
            author: "Federico Fellini",
            translation: "不同的语言是对生活的不同看法。"
        },
        {
            text: "You can never understand one language until you understand at least two.",
            author: "Geoffrey Willans",
            translation: "除非你至少懂两门语言，否则你无法真正理解一门语言。"
        }
    ];
    
    // 打乱顺序
    AppState.famousQuotes.sort(() => Math.random() - 0.5);
}

// 新增：显示名人名言弹窗
function showQuoteModal() {
    const modal = document.getElementById('quote-modal');
    if (!modal) return;
    
    // 更新当前名言
    const quote = AppState.famousQuotes[AppState.currentQuoteIndex];
    if (quote) {
        document.getElementById('quote-text').textContent = `"${quote.text}"`;
        document.getElementById('quote-author').textContent = `- ${quote.author}`;
    }
    
    modal.style.display = 'block';
}

function hideQuoteModal() {
    const modal = document.getElementById('quote-modal');
    if (modal) modal.style.display = 'none';
}

function showNextQuote() {
    AppState.currentQuoteIndex = (AppState.currentQuoteIndex + 1) % AppState.famousQuotes.length;
    showQuoteModal();
}

// 新增：倒计时学习功能
function showTimerModal() {
    const modal = document.getElementById('timer-modal');
    if (modal) modal.style.display = 'block';
    updateTimerDisplay();
}

function setTimerTime(totalSeconds) {
    AppState.timerTotalTime = totalSeconds;
    AppState.timerRemaining = totalSeconds;
    updateTimerDisplay();
}

function updateCustomTime() {
    const minutes = parseInt(document.getElementById('custom-minutes').value) || 25;
    setTimerTime(minutes * 60);
    
    // 取消所有预设按钮的激活状态
    document.querySelectorAll('.time-preset').forEach(p => p.classList.remove('active'));
}

function startTimer() {
    if (AppState.timerRunning) return;
    
    AppState.timerRunning = true;
    document.getElementById('timer-status').textContent = '专注学习中...';
    
    // 播放开始音效
    playTimerSound('start');
    
    AppState.timerInterval = setInterval(() => {
        AppState.timerRemaining--;
        updateTimerDisplay();
        
        if (AppState.timerRemaining <= 0) {
            clearInterval(AppState.timerInterval);
            AppState.timerRunning = false;
            document.getElementById('timer-status').textContent = '时间到！';
            
            // 播放完成音效
            playTimerSound('complete');
            
            // 显示通知
            if (Notification.permission === 'granted') {
                new Notification('VisWords 计时器', {
                    body: '专注学习时间已结束！休息一下吧。',
                    icon: '/favicon.ico'
                });
            } else {
                alert('⏰ 专注学习时间已结束！休息一下吧。');
            }
        }
    }, 1000);
}

function pauseTimer() {
    if (!AppState.timerRunning) return;
    
    AppState.timerRunning = false;
    clearInterval(AppState.timerInterval);
    document.getElementById('timer-status').textContent = '已暂停';
}

function resetTimer() {
    AppState.timerRunning = false;
    clearInterval(AppState.timerInterval);
    AppState.timerRemaining = AppState.timerTotalTime;
    document.getElementById('timer-status').textContent = '准备开始';
    updateTimerDisplay();
}

function updateTimerDisplay() {
    const minutes = Math.floor(AppState.timerRemaining / 60);
    const seconds = AppState.timerRemaining % 60;
    
    document.getElementById('timer-minutes').textContent = minutes.toString().padStart(2, '0');
    document.getElementById('timer-seconds').textContent = seconds.toString().padStart(2, '0');
    
    // 更新进度圆环
    const progress = 100 - (AppState.timerRemaining / AppState.timerTotalTime) * 100;
    const progressElement = document.querySelector('.timer-progress');
    if (progressElement) {
        progressElement.style.background = `conic-gradient(#0d9488 ${progress}%, #e9ecef ${progress}%)`;
    }
}

function playTimerSound(type) {
    try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        if (type === 'start') {
            oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
        } else if (type === 'complete') {
            oscillator.frequency.setValueAtTime(600, audioContext.currentTime);
            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 1);
        }
        
        oscillator.start();
        oscillator.stop(audioContext.currentTime + 0.5);
    } catch (e) {
        console.log('音频播放失败:', e);
    }
}

// 新增：单词拼写功能
function showSpellingModal() {
    const modal = document.getElementById('spelling-modal');
    if (modal) modal.style.display = 'block';
    getNewSpellingWord();
    
    // 更新统计显示
    updateSpellingStats();
    
    // 初始化虚拟键盘
    createVirtualKeyboard();
}

function updateSpellingDisplay() {
    if (!AppState.currentSpellingWord) {
        console.error('没有当前拼写单词');
        return;
    }
    
    const word = AppState.currentSpellingWord;
    
    // 更新所有提示元素
    const elements = {
        'spelling-hint-cn': word.definition_cn || '未知',
        'spelling-hint-en': word.definition_en || 'Unknown',
        'spelling-first-letter': word.word.charAt(0).toUpperCase(),
        'spelling-length': word.word.length.toString()
    };
    
    // 更新词性（使用简单的判断）
    const partOfSpeech = getPartOfSpeech(word.word);
    
    // 更新DOM元素
    for (const [id, value] of Object.entries(elements)) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    }
    
    const partOfSpeechElement = document.getElementById('spelling-part-of-speech');
    if (partOfSpeechElement) {
        partOfSpeechElement.textContent = partOfSpeech;
    }
    
    // 清空输入框
    const answerInput = document.getElementById('spelling-answer');
    if (answerInput) {
        answerInput.value = '';
        answerInput.focus();
    }
    
    // 清空消息
    const messageElement = document.getElementById('spelling-message');
    if (messageElement) {
        messageElement.textContent = '请输入单词拼写';
        messageElement.style.color = '#666';
    }
}

// 判断词性
function getPartOfSpeech(word) {
    if (!word || word.length < 3) return 'noun';
    
    const wordLower = word.toLowerCase();
    
    // 常见的词性后缀规则
    const suffixes = {
        // 名词后缀
        'tion': 'noun',
        'sion': 'noun',
        'ment': 'noun',
        'ness': 'noun',
        'ity': 'noun',
        'ance': 'noun',
        'ence': 'noun',
        'hood': 'noun',
        'ship': 'noun',
        'ism': 'noun',
        'ist': 'noun',
        
        // 动词后缀
        'ize': 'verb',
        'ise': 'verb',
        'ify': 'verb',
        'ate': 'verb',
        'en': 'verb',
        
        // 形容词后缀
        'able': 'adjective',
        'ible': 'adjective',
        'al': 'adjective',
        'ic': 'adjective',
        'ical': 'adjective',
        'ive': 'adjective',
        'ous': 'adjective',
        'ious': 'adjective',
        'ful': 'adjective',
        'less': 'adjective',
        'ish': 'adjective',
        
        // 副词后缀
        'ly': 'adverb'
    };
    
    // 检查后缀
    for (const [suffix, pos] of Object.entries(suffixes)) {
        if (wordLower.endsWith(suffix)) {
            return pos;
        }
    }
    
    // 默认返回 noun
    return 'noun';
}
// 更新 getNewSpellingWord 函数，使用后端 API
// 更新 getNewSpellingWord 函数
// 更新 getNewSpellingWord 函数
async function getNewSpellingWord() {
    try {
        console.log('开始获取拼写单词...');
        
        // 显示加载状态
        showSpellingMessage('正在加载单词...', 'info');
        
        // 清空当前单词
        AppState.currentSpellingWord = null;
        
        // 尝试使用后端API
        try {
            console.log('尝试调用API...');
            const response = await fetch(`${API_BASE}/get_spelling_word?level=CET-4&difficulty=medium`);
            
            if (response.ok) {
                const data = await response.json();
                console.log('API响应:', data);
                
                if (data.success && data.word) {
                    AppState.currentSpellingWord = data.word;
                    console.log('获取到API单词:', AppState.currentSpellingWord.word);
                    
                    // 更新显示
                    updateSpellingDisplay();
                    
                    // 更新统计
                    AppState.spellingStats.total++;
                    updateSpellingStats();
                    
                    showSpellingMessage('请输入单词拼写', 'info');
                    return;
                }
            } else {
                console.warn('API响应失败:', response.status);
            }
        } catch (apiError) {
            console.warn('API获取失败，使用本地单词:', apiError.message);
        }
        
        // 如果API失败，使用本地单词列表
        console.log('使用本地单词列表...');
        
        // 确保有单词数据
        if (AppState.words.length === 0) {
            console.log('加载默认单词列表...');
            await loadWordList('CET-4');
        }
        
        // 创建示例单词作为后备
        const exampleWords = [
            {
                id: 1001,
                word: 'apple',
                phonetic: '/ˈæpl/',
                definition_en: 'a round fruit with red, yellow, or green skin',
                definition_cn: '苹果',
                level: 'CET-4',
                example_sentence: 'I eat an apple every day.'
            },
            {
                id: 1002,
                word: 'book',
                phonetic: '/bʊk/',
                definition_en: 'a written or printed work consisting of pages',
                definition_cn: '书',
                level: 'CET-4',
                example_sentence: 'She is reading a book.'
            },
            {
                id: 1003,
                word: 'computer',
                phonetic: '/kəmˈpjuːtə(r)/',
                definition_en: 'an electronic device for storing and processing data',
                definition_cn: '计算机',
                level: 'CET-4',
                example_sentence: 'He works on a computer.'
            },
            {
                id: 1004,
                word: 'student',
                phonetic: '/ˈstjuːdnt/',
                definition_en: 'a person who is studying',
                definition_cn: '学生',
                level: 'CET-4',
                example_sentence: 'She is a good student.'
            },
            {
                id: 1005,
                word: 'teacher',
                phonetic: '/ˈtiːtʃə(r)/',
                definition_en: 'a person who teaches',
                definition_cn: '老师',
                level: 'CET-4',
                example_sentence: 'My teacher is very kind.'
            },
            {
                id: 1006,
                word: 'school',
                phonetic: '/skuːl/',
                definition_en: 'an institution for educating children',
                definition_cn: '学校',
                level: 'CET-4',
                example_sentence: 'I go to school every day.'
            },
            {
                id: 1007,
                word: 'learn',
                phonetic: '/lɜːn/',
                definition_en: 'gain or acquire knowledge of or skill in',
                definition_cn: '学习',
                level: 'CET-4',
                example_sentence: 'Children learn quickly.'
            },
            {
                id: 1008,
                word: 'study',
                phonetic: '/ˈstʌdi/',
                definition_en: 'the devotion of time and attention to acquiring knowledge',
                definition_cn: '学习，研究',
                level: 'CET-4',
                example_sentence: 'I need to study for the exam.'
            }
        ];
        
        // 合并单词列表
        let availableWords = [...exampleWords];
        if (AppState.words.length > 0) {
            availableWords = [...availableWords, ...AppState.words];
        }
        
        // 过滤掉太短的单词
        const suitableWords = availableWords.filter(word => 
            word && word.word && word.word.length >= 3 && word.word.length <= 12
        );
        
        console.log('可用单词数:', suitableWords.length);
        
        if (suitableWords.length === 0) {
            showSpellingMessage('没有找到合适的单词', 'warning');
            return;
        }
        
        // 随机选择一个单词
        const randomIndex = Math.floor(Math.random() * suitableWords.length);
        AppState.currentSpellingWord = suitableWords[randomIndex];
        
        console.log('选择的单词:', AppState.currentSpellingWord.word);
        
        // 更新显示
        updateSpellingDisplay();
        
        // 更新统计
        AppState.spellingStats.total++;
        updateSpellingStats();
        
        showSpellingMessage('请输入单词拼写', 'info');
        
    } catch (error) {
        console.error('获取拼写单词失败:', error);
        showSpellingMessage('获取单词失败: ' + error.message, 'error');
    }
}
async function checkSpelling() {
    const userAnswer = document.getElementById('spelling-answer').value.trim().toLowerCase();
    const correctWord = AppState.currentSpellingWord?.word.toLowerCase();
    
    if (!userAnswer) {
        showSpellingMessage('请输入单词', 'warning');
        return;
    }
    
    if (!correctWord || !AppState.currentSpellingWord.id) {
        showSpellingMessage('没有当前单词，请点击"新单词"', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/check_spelling`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                word_id: AppState.currentSpellingWord.id,
                user_answer: userAnswer,
                correct_word: correctWord
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.is_correct) {
            showSpellingMessage(`✓ 正确！单词 "${AppState.currentSpellingWord.word}" 拼写正确！`, 'success');
            document.getElementById('spelling-answer').style.borderColor = '#10b981';
            AppState.spellingStats.correct++;
            playSpellingSound('correct');
            
            setTimeout(() => {
                getNewSpellingWord();
                document.getElementById('spelling-answer').style.borderColor = '#e9ecef';
            }, 1000);
        } else {
            let message = `✗ 不正确！`;
            
            if (data.error_analysis) {
                data.error_analysis.forEach(error => {
                    if (error.type === 'length') {
                        message += ` 长度错误（你的: ${error.user_length}，正确: ${error.correct_length}）`;
                    } else if (error.type === 'wrong_letters') {
                        const positions = error.positions.map(p => `位置 ${p.position}: "${p.user_char}"→"${p.correct_char}"`);
                        message += ` 错误的字母：${positions.join(', ')}`;
                    }
                });
            }
            
            message += ` ${data.feedback}`;
            
            showSpellingMessage(message, 'error');
            document.getElementById('spelling-answer').style.borderColor = '#ef4444';
            AppState.spellingStats.wrong++;
            playSpellingSound('wrong');
        }
        
        updateSpellingStats();
        
    } catch (error) {
        console.error('API验证拼写失败，使用本地验证:', error);
        // 使用本地验证作为备选
        checkSpellingLocal(userAnswer, correctWord);
    }
}

function checkSpellingLocal(userAnswer, correctWord) {
    // 原有的本地验证逻辑
    if (userAnswer === correctWord) {
        showSpellingMessage(`✓ 正确！单词 "${AppState.currentSpellingWord.word}" 拼写正确！`, 'success');
        document.getElementById('spelling-answer').style.borderColor = '#10b981';
        AppState.spellingStats.correct++;
        playSpellingSound('correct');
        
        setTimeout(() => {
            getNewSpellingWord();
            document.getElementById('spelling-answer').style.borderColor = '#e9ecef';
        }, 1000);
    } else {
        let message = `✗ 不正确！`;
        
        if (userAnswer.length !== correctWord.length) {
            message += ` 长度错误（你的: ${userAnswer.length}，正确: ${correctWord.length}）`;
        } else {
            let differences = [];
            for (let i = 0; i < Math.max(userAnswer.length, correctWord.length); i++) {
                if (userAnswer[i] !== correctWord[i]) {
                    differences.push(`位置 ${i+1}: 你输入了 "${userAnswer[i] || ''}"，应该是 "${correctWord[i]}"`);
                }
            }
            if (differences.length > 0) {
                message += ` 错误的字母位置：${differences.join(', ')}`;
            }
        }
        
        message += ` 正确单词是：${AppState.currentSpellingWord.word}`;
        
        showSpellingMessage(message, 'error');
        document.getElementById('spelling-answer').style.borderColor = '#ef4444';
        AppState.spellingStats.wrong++;
        playSpellingSound('wrong');
    }
    
    updateSpellingStats();
}
function highlightSpellingErrors(userAnswer, correctWord) {
    const input = document.getElementById('spelling-answer');
    let highlightedHTML = '';
    
    for (let i = 0; i < Math.max(userAnswer.length, correctWord.length); i++) {
        const userChar = userAnswer[i] || '';
        const correctChar = correctWord[i] || '';
        
        if (userChar === correctChar) {
            highlightedHTML += `<span class="correct-char">${userChar}</span>`;
        } else {
            highlightedHTML += `<span class="wrong-char">${userChar}</span>`;
        }
    }
    
    // 临时显示高亮效果
    const originalValue = input.value;
    const tempDiv = document.createElement('div');
    tempDiv.className = 'spelling-highlight';
    tempDiv.innerHTML = highlightedHTML;
    tempDiv.style.position = 'absolute';
    tempDiv.style.top = '0';
    tempDiv.style.left = '0';
    tempDiv.style.padding = '1rem';
    tempDiv.style.fontSize = '1.2rem';
    tempDiv.style.letterSpacing = '2px';
    tempDiv.style.pointerEvents = 'none';
    
    input.parentNode.style.position = 'relative';
    input.parentNode.appendChild(tempDiv);
    
    setTimeout(() => {
        if (tempDiv.parentNode) {
            tempDiv.parentNode.removeChild(tempDiv);
        }
    }, 2000);
}

function showMoreHint() {
    if (!AppState.currentSpellingWord) return;
    
    const word = AppState.currentSpellingWord.word;
    const hints = [
        `音标：${AppState.currentSpellingWord.phonetic || '无'}`,
        `例句：${AppState.currentSpellingWord.example_sentence || '无'}`,
        `单词等级：${AppState.currentSpellingWord.level || '未知'}`
    ];
    
    // 显示更多字母提示
    let hintLetters = '';
    for (let i = 0; i < word.length; i++) {
        if (i % 2 === 0) {
            hintLetters += word[i];
        } else {
            hintLetters += '_';
        }
    }
    hints.push(`部分字母：${hintLetters}`);
    
    const randomHint = hints[Math.floor(Math.random() * hints.length)];
    showSpellingMessage(`💡 提示：${randomHint}`, 'info');
}

function showSpellingMessage(message, type) {
    const messageElement = document.getElementById('spelling-message');
    if (!messageElement) return;
    
    messageElement.textContent = message;
    messageElement.className = '';
    
    switch(type) {
        case 'success':
            messageElement.style.color = '#10b981';
            break;
        case 'error':
            messageElement.style.color = '#ef4444';
            break;
        case 'warning':
            messageElement.style.color = '#f59e0b';
            break;
        case 'info':
            messageElement.style.color = '#3b82f6';
            break;
    }
}

function updateSpellingStats() {
    document.getElementById('spelling-correct').textContent = AppState.spellingStats.correct;
    document.getElementById('spelling-wrong').textContent = AppState.spellingStats.wrong;
    document.getElementById('spelling-total').textContent = AppState.spellingStats.total;
}

function createVirtualKeyboard() {
    const keyboardElement = document.querySelector('.spelling-keyboard');
    if (!keyboardElement) return;
    
    const keyboardLayout = [
        ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
        ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l'],
        ['z', 'x', 'c', 'v', 'b', 'n', 'm']
    ];
    
    keyboardElement.innerHTML = '';
    
    keyboardLayout.forEach(row => {
        const rowDiv = document.createElement('div');
        rowDiv.style.gridColumn = '1 / -1';
        rowDiv.style.display = 'flex';
        rowDiv.style.justifyContent = 'center';
        rowDiv.style.gap = '5px';
        rowDiv.style.marginBottom = '5px';
        
        row.forEach(key => {
            const keyButton = document.createElement('button');
            keyButton.className = 'keyboard-key';
            keyButton.textContent = key.toUpperCase();
            keyButton.dataset.key = key;
            
            keyButton.addEventListener('click', () => {
                const input = document.getElementById('spelling-answer');
                const cursorPos = input.selectionStart;
                const currentValue = input.value;
                
                // 插入字符到光标位置
                const newValue = currentValue.substring(0, cursorPos) + 
                                key + 
                                currentValue.substring(cursorPos);
                
                input.value = newValue;
                
                // 移动光标到插入位置后
                setTimeout(() => {
                    input.setSelectionRange(cursorPos + 1, cursorPos + 1);
                    input.focus();
                }, 10);
            });
            
            rowDiv.appendChild(keyButton);
        });
        
        keyboardElement.appendChild(rowDiv);
    });
    
    // 添加特殊功能键
    const specialKeysRow = document.createElement('div');
    specialKeysRow.style.gridColumn = '1 / -1';
    specialKeysRow.style.display = 'flex';
    specialKeysRow.style.justifyContent = 'center';
    specialKeysRow.style.gap = '5px';
    specialKeysRow.style.marginTop = '10px';
    
    // 删除键
    const deleteKey = document.createElement('button');
    deleteKey.className = 'keyboard-key';
    deleteKey.innerHTML = '<i class="fas fa-backspace"></i>';
    deleteKey.style.padding = '10px 20px';
    
    deleteKey.addEventListener('click', () => {
        const input = document.getElementById('spelling-answer');
        const cursorPos = input.selectionStart;
        const currentValue = input.value;
        
        if (cursorPos > 0) {
            const newValue = currentValue.substring(0, cursorPos - 1) + 
                           currentValue.substring(cursorPos);
            
            input.value = newValue;
            
            setTimeout(() => {
                input.setSelectionRange(cursorPos - 1, cursorPos - 1);
                input.focus();
            }, 10);
        }
    });
    
    // 空格键
    const spaceKey = document.createElement('button');
    spaceKey.className = 'keyboard-key';
    spaceKey.textContent = '空格';
    spaceKey.style.flex = '2';
    
    spaceKey.addEventListener('click', () => {
        const input = document.getElementById('spelling-answer');
        const cursorPos = input.selectionStart;
        const currentValue = input.value;
        
        const newValue = currentValue.substring(0, cursorPos) + 
                        ' ' + 
                        currentValue.substring(cursorPos);
        
        input.value = newValue;
        
        setTimeout(() => {
            input.setSelectionRange(cursorPos + 1, cursorPos + 1);
            input.focus();
        }, 10);
    });
    
    // 清空键
    const clearKey = document.createElement('button');
    clearKey.className = 'keyboard-key';
    clearKey.innerHTML = '<i class="fas fa-times"></i>';
    clearKey.style.padding = '10px 20px';
    
    clearKey.addEventListener('click', () => {
        document.getElementById('spelling-answer').value = '';
        document.getElementById('spelling-answer').focus();
    });
    
    specialKeysRow.appendChild(deleteKey);
    specialKeysRow.appendChild(spaceKey);
    specialKeysRow.appendChild(clearKey);
    
    keyboardElement.appendChild(specialKeysRow);
}

function playSpellingSound(type) {
    try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        if (type === 'correct') {
            // 上升音调表示正确
            oscillator.frequency.setValueAtTime(400, audioContext.currentTime);
            oscillator.frequency.linearRampToValueAtTime(800, audioContext.currentTime + 0.2);
            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
        } else if (type === 'wrong') {
            // 下降音调表示错误
            oscillator.frequency.setValueAtTime(600, audioContext.currentTime);
            oscillator.frequency.linearRampToValueAtTime(300, audioContext.currentTime + 0.3);
            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.4);
        }
        
        oscillator.start();
        oscillator.stop(audioContext.currentTime + 0.5);
    } catch (e) {
        console.log('拼写音效播放失败:', e);
    }
}

// 在页面加载时请求通知权限
if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
}

// 在原有的 DOMContentLoaded 监听器中添加初始化
document.addEventListener('DOMContentLoaded', function() {
    // ... 原有的初始化代码 ...
    
    // 新增初始化
    loadFamousQuotes();
    
    // 请求通知权限
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
});
// 应用启动
console.log('VisWords应用已加载');