# -*- coding: utf-8 -*-
"""内置工具定义"""

BUILTIN_TOOLS = [
    {
        'id': 'audio', 'author': 'hjlarry', 'package': 'audio', 'name': 'Audio',
        'description': '一个用于文本转语音和语音转文本的工具。',
        'icon': '🎙️', 'icon_bg': '#FFECE8', 'labels': ['工具', '生产力'],
        'tools': [
            {'name': 'text_to_speech', 'label': 'Text To Speech', 'description': '将文本转换为音频文件。',
             'parameters': [
                 {'name': 'text', 'label': '文本', 'type': 'string', 'required': True, 'description': '要转换为语音的文本。'},
                 {'name': 'model', 'label': '模型', 'type': 'string', 'required': False, 'description': '语音合成模型。'}
             ]},
            {'name': 'speech_to_text', 'label': 'Speech To Text', 'description': '将音频文件转换为文本。',
             'parameters': [
                 {'name': 'audio_file', 'label': '音频文件', 'type': 'file', 'required': True, 'description': '要识别的音频文件。'},
                 {'name': 'model', 'label': '模型', 'type': 'string', 'required': False, 'description': '语音识别模型。'}
             ]}
        ]
    },
    {
        'id': 'code', 'author': 'Dify', 'package': 'code', 'name': '代码解释器',
        'description': '运行一段代码并返回结果。',
        'icon': '&lt;/&gt;', 'icon_bg': '#EAF1FE', 'icon_fg': '#1C64F2', 'labels': ['工具', '生产力'],
        'tools': [
            {'name': 'run_code', 'label': 'Run Code', 'description': '运行一段代码并返回结果。',
             'parameters': [
                 {'name': 'code', 'label': '代码', 'type': 'string', 'required': True, 'description': '要运行的代码。'},
                 {'name': 'language', 'label': '语言', 'type': 'string', 'required': False, 'description': '代码语言，如 python / javascript。'}
             ]}
        ]
    },
    {
        'id': 'time', 'author': 'Dify', 'package': 'time', 'name': '时间',
        'description': '一个用于获取当前时间的工具。',
        'icon': '🕐', 'icon_bg': '#FFF7E8', 'labels': ['工具', '生产力'],
        'tools': [
            {'name': 'current_time', 'label': 'Current Time', 'description': '获取当前时间。',
             'parameters': [
                 {'name': 'format', 'label': '格式', 'type': 'string', 'required': False, 'description': '时间格式模板，如 %%Y-%%m-%%d %%H:%%M:%%S。'}
             ]}
        ]
    },
    {
        'id': 'webscraper', 'author': 'Dify', 'package': 'webscraper', 'name': '网页抓取',
        'description': '一个用于抓取网页的工具。',
        'icon': '🌐', 'icon_bg': '#FFECE8', 'labels': ['工具', '搜索'],
        'tools': [
            {'name': 'web_scraper', 'label': 'Web Scraper', 'description': '抓取指定网页的正文内容。',
             'parameters': [
                 {'name': 'url', 'label': '网页地址', 'type': 'string', 'required': True, 'description': '要抓取的网页 URL。'},
                 {'name': 'user_agent', 'label': '请求头', 'type': 'string', 'required': False, 'description': '自定义 User-Agent。'}
             ]}
        ]
    },
    {
        'id': 'search', 'author': 'Dify', 'package': 'search', 'name': '网页搜索',
        'description': '通过搜索引擎获取实时信息。',
        'icon': '🔍', 'icon_bg': '#EAF1FE', 'labels': ['搜索', '工具'],
        'tools': [
            {'name': 'web_search', 'label': 'Web Search', 'description': '搜索互联网获取实时信息。',
             'parameters': [
                 {'name': 'query', 'label': '搜索关键词', 'type': 'string', 'required': True, 'description': '搜索查询内容。'},
                 {'name': 'num_results', 'label': '结果数量', 'type': 'number', 'required': False, 'description': '返回结果数量，默认 5。'}
             ]},
            {'name': 'fetch_url', 'label': 'Fetch URL', 'description': '获取指定 URL 的内容。',
             'parameters': [
                 {'name': 'url', 'label': '网页地址', 'type': 'string', 'required': True, 'description': '要获取内容的 URL。'}
             ]}
        ]
    },
    {
        'id': 'weather', 'author': 'Dify', 'package': 'weather', 'name': '天气查询',
        'description': '查询指定城市的实时天气或天气预报。',
        'icon': '🌤️', 'icon_bg': '#FFF7E8', 'labels': ['工具', '生活'],
        'tools': [
            {'name': 'get_weather', 'label': 'Get Weather', 'description': '查询指定城市的天气。',
             'parameters': [
                 {'name': 'city', 'label': '城市', 'type': 'string', 'required': True, 'description': '城市名称，如 北京、上海。'},
                 {'name': 'days', 'label': '天数', 'type': 'number', 'required': False, 'description': '预报天数，默认 1（当前天气）。'}
             ]}
        ]
    },
    {
        'id': 'translate', 'author': 'Dify', 'package': 'translate', 'name': '翻译',
        'description': '在多种语言之间翻译文本。',
        'icon': '🌐', 'icon_bg': '#E8FFEA', 'labels': ['工具', '生产力'],
        'tools': [
            {'name': 'translate_text', 'label': 'Translate', 'description': '翻译文本到目标语言。',
             'parameters': [
                 {'name': 'text', 'label': '原文', 'type': 'string', 'required': True, 'description': '要翻译的文本。'},
                 {'name': 'target_lang', 'label': '目标语言', 'type': 'string', 'required': True, 'description': '目标语言，如 en、ja、ko。'},
                 {'name': 'source_lang', 'label': '源语言', 'type': 'string', 'required': False, 'description': '源语言，默认 auto（自动检测）。'}
             ]}
        ]
    },
    {
        'id': 'calculator', 'author': 'Dify', 'package': 'calculator', 'name': '计算器',
        'description': '执行数学计算和公式求解。',
        'icon': '🧮', 'icon_bg': '#F5E8FF', 'labels': ['工具', '生产力'],
        'tools': [
            {'name': 'calculate', 'label': 'Calculate', 'description': '计算数学表达式。',
             'parameters': [
                 {'name': 'expression', 'label': '表达式', 'type': 'string', 'required': True, 'description': '数学表达式，如 2^10、sqrt(144)。'}
             ]},
            {'name': 'convert_unit', 'label': 'Unit Convert', 'description': '单位换算。',
             'parameters': [
                 {'name': 'value', 'label': '数值', 'type': 'number', 'required': True, 'description': '要转换的数值。'},
                 {'name': 'from_unit', 'label': '源单位', 'type': 'string', 'required': True, 'description': '源单位，如 km、kg。'},
                 {'name': 'to_unit', 'label': '目标单位', 'type': 'string', 'required': True, 'description': '目标单位，如 mi、lb。'}
             ]}
        ]
    },
    {
        'id': 'file', 'author': 'Dify', 'package': 'file', 'name': '文件处理',
        'description': '读取、写入和转换文件格式。',
        'icon': '📄', 'icon_bg': '#FFECE8', 'labels': ['工具', '生产力'],
        'tools': [
            {'name': 'read_file', 'label': 'Read File', 'description': '读取文本文件内容。',
             'parameters': [
                 {'name': 'file_path', 'label': '文件路径', 'type': 'string', 'required': True, 'description': '要读取的文件路径。'}
             ]},
            {'name': 'write_file', 'label': 'Write File', 'description': '写入内容到文件。',
             'parameters': [
                 {'name': 'file_path', 'label': '文件路径', 'type': 'string', 'required': True, 'description': '目标文件路径。'},
                 {'name': 'content', 'label': '内容', 'type': 'string', 'required': True, 'description': '要写入的内容。'}
             ]}
        ]
    },
    {
        'id': 'json', 'author': 'Dify', 'package': 'json', 'name': 'JSON 处理',
        'description': '解析、生成和转换 JSON 数据。',
        'icon': '{ }', 'icon_bg': '#EAF1FE', 'icon_fg': '#1C64F2', 'labels': ['工具', '开发'],
        'tools': [
            {'name': 'parse_json', 'label': 'Parse JSON', 'description': '解析 JSON 字符串并提取字段。',
             'parameters': [
                 {'name': 'json_str', 'label': 'JSON 字符串', 'type': 'string', 'required': True, 'description': '要解析的 JSON。'},
                 {'name': 'field_path', 'label': '字段路径', 'type': 'string', 'required': False, 'description': '要提取的字段路径，如 data.items[0].name。'}
             ]},
            {'name': 'to_json', 'label': 'To JSON', 'description': '将文本转换为 JSON 格式。',
             'parameters': [
                 {'name': 'text', 'label': '文本', 'type': 'string', 'required': True, 'description': '要转换的文本。'}
             ]}
        ]
    },
    {
        'id': 'email', 'author': 'Dify', 'package': 'email', 'name': '邮件',
        'description': '发送电子邮件或获取邮件列表。',
        'icon': '📧', 'icon_bg': '#FFF7E8', 'labels': ['工具', '商业'],
        'tools': [
            {'name': 'send_email', 'label': 'Send Email', 'description': '发送电子邮件。',
             'parameters': [
                 {'name': 'to', 'label': '收件人', 'type': 'string', 'required': True, 'description': '收件人邮箱地址。'},
                 {'name': 'subject', 'label': '主题', 'type': 'string', 'required': True, 'description': '邮件主题。'},
                 {'name': 'body', 'label': '正文', 'type': 'string', 'required': True, 'description': '邮件正文。'}
             ]}
        ]
    },
    {
        'id': 'database', 'author': 'Dify', 'package': 'database', 'name': '数据库',
        'description': '执行 SQL 查询和数据库操作。',
        'icon': '🗄️', 'icon_bg': '#E8FFEA', 'labels': ['工具', '开发'],
        'tools': [
            {'name': 'execute_sql', 'label': 'Execute SQL', 'description': '执行 SQL 查询。',
             'parameters': [
                 {'name': 'sql', 'label': 'SQL 语句', 'type': 'string', 'required': True, 'description': '要执行的 SQL 查询。'},
                 {'name': 'database', 'label': '数据库', 'type': 'string', 'required': False, 'description': '目标数据库连接名。'}
             ]}
        ]
    },
    {
        'id': 'image_generator', 'author': 'Dify', 'package': 'image_generator', 'name': '图片生成',
        'description': '根据文本描述生成 AI 图片（DALL-E / Stable Diffusion）。',
        'icon': '🎨', 'icon_bg': '#FFF0F6', 'labels': ['工具', '设计'],
        'tools': [
            {'name': 'generate_image', 'label': 'Generate Image', 'description': '根据文本描述生成图片。',
             'parameters': [
                 {'name': 'prompt', 'label': '图片描述', 'type': 'string', 'required': True, 'description': '图片的文本描述，越详细越好。'},
                 {'name': 'size', 'label': '尺寸', 'type': 'string', 'required': False, 'description': '图片尺寸：256x256、512x512、1024x1024。'},
                 {'name': 'model', 'label': '模型', 'type': 'string', 'required': False, 'description': '生成模型，如 dall-e-2、dall-e-3。'},
                 {'name': 'quality', 'label': '质量', 'type': 'string', 'required': False, 'description': '图片质量：standard 或 hd。'}
             ]}
        ]
    },
    {
        'id': 'web_reader', 'author': 'Dify', 'package': 'web_reader', 'name': '网页阅读',
        'description': '智能提取网页正文内容，自动去除广告和导航。',
        'icon': '📖', 'icon_bg': '#EAF1FE', 'labels': ['工具', '搜索'],
        'tools': [
            {'name': 'read_url', 'label': 'Read URL', 'description': '读取并提取网页正文内容。',
             'parameters': [
                 {'name': 'url', 'label': '网页地址', 'type': 'string', 'required': True, 'description': '要读取的网页 URL。'},
                 {'name': 'extract_mode', 'label': '提取模式', 'type': 'string', 'required': False, 'description': '提取模式：markdown、text、html。'},
                 {'name': 'max_length', 'label': '最大长度', 'type': 'number', 'required': False, 'description': '返回内容最大字符数，默认 5000。'}
             ]}
        ]
    },
    {
        'id': 'chart', 'author': 'Dify', 'package': 'chart', 'name': '图表生成',
        'description': '根据数据生成可视化图表（折线图、柱状图、饼图等）。',
        'icon': '📊', 'icon_bg': '#FFF7E8', 'labels': ['工具', '数据分析'],
        'tools': [
            {'name': 'generate_chart', 'label': 'Generate Chart', 'description': '根据数据生成图表。',
             'parameters': [
                 {'name': 'chart_type', 'label': '图表类型', 'type': 'string', 'required': True, 'description': '图表类型：line、bar、pie、scatter、area。'},
                 {'name': 'data', 'label': '数据', 'type': 'string', 'required': True, 'description': '图表数据，JSON 格式，如 [{"name":"A","value":10},{"name":"B","value":20}]。'},
                 {'name': 'title', 'label': '标题', 'type': 'string', 'required': False, 'description': '图表标题。'},
                 {'name': 'x_label', 'label': 'X轴标签', 'type': 'string', 'required': False, 'description': 'X 轴标签。'},
                 {'name': 'y_label', 'label': 'Y轴标签', 'type': 'string', 'required': False, 'description': 'Y 轴标签。'}
             ]}
        ]
    },
    {
        'id': 'pdf', 'author': 'Dify', 'package': 'pdf', 'name': 'PDF 处理',
        'description': '提取 PDF 文本、合并/拆分 PDF、生成 PDF。',
        'icon': '📕', 'icon_bg': '#FFECE8', 'labels': ['工具', '办公文档'],
        'tools': [
            {'name': 'extract_pdf_text', 'label': 'Extract PDF Text', 'description': '提取 PDF 文件中的文本内容。',
             'parameters': [
                 {'name': 'pdf_file', 'label': 'PDF 文件', 'type': 'file', 'required': True, 'description': '要提取文本的 PDF 文件。'},
                 {'name': 'page_range', 'label': '页码范围', 'type': 'string', 'required': False, 'description': '页码范围，如 1-5 或 1,3,5。'}
             ]},
            {'name': 'generate_pdf', 'label': 'Generate PDF', 'description': '从文本或 Markdown 生成 PDF 文件。',
             'parameters': [
                 {'name': 'content', 'label': '内容', 'type': 'string', 'required': True, 'description': '要转换为 PDF 的文本或 Markdown 内容。'},
                 {'name': 'title', 'label': '标题', 'type': 'string', 'required': False, 'description': 'PDF 文档标题。'}
             ]}
        ]
    },
    {
        'id': 'text_analyzer', 'author': 'Dify', 'package': 'text_analyzer', 'name': '文本分析',
        'description': '分析文本的情感、关键词、摘要和实体。',
        'icon': '🔬', 'icon_bg': '#F5E8FF', 'labels': ['工具', '数据分析'],
        'tools': [
            {'name': 'sentiment_analysis', 'label': 'Sentiment Analysis', 'description': '分析文本的情感倾向。',
             'parameters': [
                 {'name': 'text', 'label': '文本', 'type': 'string', 'required': True, 'description': '要分析的文本。'}
             ]},
            {'name': 'summarize', 'label': 'Summarize', 'description': '生成文本摘要。',
             'parameters': [
                 {'name': 'text', 'label': '文本', 'type': 'string', 'required': True, 'description': '要摘要的长文本。'},
                 {'name': 'max_length', 'label': '最大长度', 'type': 'number', 'required': False, 'description': '摘要最大字数，默认 200。'}
             ]},
            {'name': 'extract_keywords', 'label': 'Extract Keywords', 'description': '提取文本关键词。',
             'parameters': [
                 {'name': 'text', 'label': '文本', 'type': 'string', 'required': True, 'description': '要分析的文本。'},
                 {'name': 'top_n', 'label': '关键词数量', 'type': 'number', 'required': False, 'description': '返回关键词数量，默认 10。'}
             ]}
        ]
    },
    {
        'id': 'file_converter', 'author': 'Dify', 'package': 'file_converter', 'name': '文件转换',
        'description': '在不同文件格式之间转换（Markdown、HTML、CSV、JSON）。',
        'icon': '🔄', 'icon_bg': '#E8FFEA', 'labels': ['工具', '生产力'],
        'tools': [
            {'name': 'html_to_markdown', 'label': 'HTML to Markdown', 'description': '将 HTML 转换为 Markdown。',
             'parameters': [
                 {'name': 'html', 'label': 'HTML 内容', 'type': 'string', 'required': True, 'description': '要转换的 HTML 内容。'}
             ]},
            {'name': 'csv_to_json', 'label': 'CSV to JSON', 'description': '将 CSV 转换为 JSON 数组。',
             'parameters': [
                 {'name': 'csv', 'label': 'CSV 内容', 'type': 'string', 'required': True, 'description': '要转换的 CSV 内容。'},
                 {'name': 'delimiter', 'label': '分隔符', 'type': 'string', 'required': False, 'description': 'CSV 分隔符，默认逗号。'}
             ]},
            {'name': 'json_to_csv', 'label': 'JSON to CSV', 'description': '将 JSON 数组转换为 CSV。',
             'parameters': [
                 {'name': 'json_data', 'label': 'JSON 数据', 'type': 'string', 'required': True, 'description': '要转换的 JSON 数组字符串。'}
             ]}
        ]
    },
    {
        'id': 'email_reader', 'author': 'Dify', 'package': 'email_reader', 'name': '邮件读取',
        'description': '读取和管理电子邮件（IMAP 协议）。',
        'icon': '📬', 'icon_bg': '#FFF7E8', 'labels': ['工具', '商业'],
        'tools': [
            {'name': 'fetch_emails', 'label': 'Fetch Emails', 'description': '获取邮件列表。',
             'parameters': [
                 {'name': 'folder', 'label': '文件夹', 'type': 'string', 'required': False, 'description': '邮件文件夹，默认 INBOX。'},
                 {'name': 'limit', 'label': '数量', 'type': 'number', 'required': False, 'description': '获取邮件数量，默认 10。'},
                 {'name': 'unread_only', 'label': '仅未读', 'type': 'boolean', 'required': False, 'description': '是否只获取未读邮件。'}
             ]},
            {'name': 'read_email', 'label': 'Read Email', 'description': '读取指定邮件的完整内容。',
             'parameters': [
                 {'name': 'email_id', 'label': '邮件 ID', 'type': 'string', 'required': True, 'description': '要读取的邮件 ID。'}
             ]}
        ]
    }
]

TOOL_AUTO_UPDATE_DEFAULT = {'mode': 'patch', 'update_time': '19:45', 'scope': 'all'}
