# API配置
# 先用DeepSeek的免费额度（注册送500万tokens，够用几个月）
# 官网：https://platform.deepseek.com/
API_KEY = "sk-bbc6c35e24fa46a18062207258a1cc0f"  # 先去这里复制：https://platform.deepseek.com/api_keys

# 如果DeepSeek不稳定，备用方案：
# API_KEY = "sk-你的OpenAI密钥"  # OpenAI稍贵但稳定
# API_BASE = "https://api.openai.com/v1"
# MODEL = "gpt-3.5-turbo"

# DeepSeek配置（便宜，1元=100万tokens，够用很久）
API_BASE = "https://api.deepseek.com"
MODEL = "deepseek-chat"  # 或 deepseek-reasoner（推理更强但慢一点）