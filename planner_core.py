# 核心逻辑
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
import sqlite3
import hashlib
from datetime import datetime, timedelta
from openai import OpenAI
from config import API_KEY, API_BASE, MODEL

class LearningPlanner:
    def __init__(self):
        self.client = OpenAI(api_key=API_KEY, base_url=API_BASE)
        self.setup_database()
    
    def setup_database(self):
        """创建缓存表，避免重复调用API（省钱关键）"""
        conn = sqlite3.connect('plans_cache.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS plans (
                query_hash TEXT PRIMARY KEY,
                skill TEXT,
                deadline TEXT,
                hours_per_week INTEGER,
                plan_content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    
    def get_cache(self, skill, deadline, hours_per_week):
        """检查是否之前生成过相同的计划"""
        query_str = f"{skill}_{deadline}_{hours_per_week}"
        query_hash = hashlib.md5(query_str.encode()).hexdigest()
        
        conn = sqlite3.connect('plans_cache.db')
        cursor = conn.cursor()
        cursor.execute(
            "SELECT plan_content FROM plans WHERE query_hash = ?", 
            (query_hash,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if result:
            print("💾 命中缓存，直接返回（省钱了！）")
            return json.loads(result[0])
        return None
    
    def save_cache(self, skill, deadline, hours_per_week, plan):
        """保存结果到本地"""
        query_str = f"{skill}_{deadline}_{hours_per_week}"
        query_hash = hashlib.md5(query_str.encode()).hexdigest()
        
        conn = sqlite3.connect('plans_cache.db')
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO plans VALUES (?, ?, ?, ?, ?, ?)",
            (query_hash, skill, deadline, hours_per_week, 
             json.dumps(plan, ensure_ascii=False), datetime.now())
        )
        conn.commit()
        conn.close()
    
    def create_plan(self, skill, deadline, hours_per_week):
        """
        核心功能：AI拆解学习任务
        skill: 技能名称，如"Python数据分析"
        deadline: 截止日期，如"2024-06-01"
        hours_per_week: 每周投入小时数，如10
        """
        # 先查缓存
        cached = self.get_cache(skill, deadline, hours_per_week)
        if cached:
            return cached
        
        print("🤖 AI正在思考如何拆解这个技能...（约需10秒）")
        
        # 构造Prompt（这是关键，决定了输出质量）
        prompt = f"""你是一个专业的学习路径规划师。请为学习者制定详细的"{skill}"学习计划。

约束条件：
- 目标日期：{deadline}（距今约{(datetime.strptime(deadline, '%Y-%m-%d') - datetime.now()).days}天）
- 每周可投入：{hours_per_week}小时
- 学习者：零基础初学者

要求：
1. 分3-4个阶段（基础→进阶→实战→复习）
2. 每个阶段包含：具体任务清单、预计耗时、验收标准
3. 必须包含"复习"和"实战项目"环节
4. 考虑遗忘曲线，高难度内容后安排复习
5. 输出标准JSON格式

输出格式示例：
{{
    "skill": "{skill}",
    "total_weeks": 8,
    "stages": [
        {{
            "stage_name": "基础语法掌握",
            "week": "第1-2周",
            "hours": 20,
            "tasks": [
                {{"name": "变量与数据类型", "hours": 3, "type": "学习"}},
                {{"name": "条件循环练习", "hours": 4, "type": "练习"}},
                {{"name": "函数与模块", "hours": 5, "type": "学习"}}
            ],
            "milestone": "能写100行以内的脚本",
            "deliverable": "完成10道LeetCode简单题"
        }}
    ],
    "tips": ["建议每天固定时间学习", "周末做项目实战"]
}}"""

        try:
            response = self.client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": "你是一个专业的学习规划专家，擅长将复杂技能拆解为可执行的学习任务。只输出JSON，不要任何解释。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,  # 创造性适中
                max_tokens=2000   # 足够长的输出
            )
            
            # 解析JSON
            content = response.choices[0].message.content
            
            # 有时候AI会包裹在markdown代码块里，需要清理
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            plan = json.loads(content.strip())
            
            # 保存到缓存
            self.save_cache(skill, deadline, hours_per_week, plan)
            
            # 计算成本（DeepSeek约0.001元/次）
            print(f"✅ 生成成功！本次消耗约 {response.usage.total_tokens} tokens")
            
            return plan
            
        except Exception as e:
            print(f"❌ 出错了：{e}")
            print("提示：检查API密钥是否正确，或网络连接")
            return None
    
    def display_plan(self, plan):
        """美化输出到控制台"""
        if not plan:
            return
        
        print("\n" + "="*50)
        print(f"📚 {plan['skill']} 学习计划")
        print(f"⏱️  总时长：{plan['total_weeks']}周")
        print("="*50)
        
        for i, stage in enumerate(plan['stages'], 1):
            print(f"\n🎯 阶段{i}：{stage['stage_name']} ({stage['week']})")
            print(f"   预计投入：{stage['hours']}小时")
            print(f"   里程碑：{stage['milestone']}")
            print("   任务清单：")
            for task in stage['tasks']:
                icon = "📖" if task['type'] == '学习' else "✏️" if task['type'] == '练习' else "🛠️"
                print(f"   {icon} {task['name']} ({task['hours']}h)")
        
        if 'tips' in plan:
            print(f"\n💡 学习建议：")
            for tip in plan['tips']:
                print(f"   • {tip}")
        print("="*50)

if __name__ == "__main__":
    # 测试运行
    planner = LearningPlanner()
    plan = planner.create_plan("Python数据分析", "2024-06-01", 10)
    planner.display_plan(plan)