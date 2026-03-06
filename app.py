import streamlit as st
from planner_core import LearningPlanner
from datetime import datetime, timedelta
import json
from icalendar import Calendar, Event
import uuid

# 页面设置（标题、图标）
st.set_page_config(
    page_title="AI Learning Planner",
    page_icon="📚",
    layout="centered"
)

# 标题区
st.title("📚 AI Learning Planner")
st.markdown("Enter your learning goal, AI will break it down into daily tasks")

# 侧边栏配置
with st.sidebar:
    st.header("⚙️ Settings")
    api_source = st.selectbox(
        "AI Model",
        ["SiliconFlow (Free)", "DeepSeek", "Moonshot"]
    )
    st.info("Using cached plan if available to save tokens")

# 主表单区
with st.form("learning_plan_form"):
    col1, col2 = st.columns(2)
    
    with col1:
        skill = st.text_input(
            "What skill to learn?",
            placeholder="e.g., Python Data Analysis, IELTS, UI Design",
            value="Python Data Analysis"
        )
        
        # 计算默认日期（3个月后）
        default_end = datetime.now() + timedelta(days=90)
        deadline = st.date_input(
            "Target Date",
            value=default_end
        )
    
    with col2:
        hours = st.slider(
            "Hours per week",
            min_value=5,
            max_value=40,
            value=10,
            step=1
        )
        
        start_date = st.date_input(
            "Start Date",
            value=datetime.now()
        )
    
    # 高级选项
    with st.expander("Advanced Options"):
        focus_area = st.text_input(
            "Focus area (optional)",
            placeholder="e.g., focus on machine learning"
        )
        difficulty = st.select_slider(
            "Difficulty",
            options=["Beginner", "Intermediate", "Advanced"],
            value="Beginner"
        )
    
    submitted = st.form_submit_button("🚀 Generate Learning Plan", use_container_width=True)

# 生成计划逻辑
if submitted:
    if not skill:
        st.error("Please enter a skill name!")
    else:
        # 进度条
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # 检查缓存（避免重复调用）
            planner = LearningPlanner()
            
            # 格式化日期
            deadline_str = deadline.strftime("%Y-%m-%d")
            
            # 检查是否有缓存
            cached_plan = planner.get_cache(skill, deadline_str, hours)
            
            if cached_plan:
                status_text.info("Loading from cache... (Free)")
                progress_bar.progress(50)
                plan = cached_plan
            else:
                status_text.info("AI is analyzing your skill... (May take 10s)")
                progress_bar.progress(30)
                
                # 调用AI
                plan = planner.create_plan(skill, deadline_str, hours)
                progress_bar.progress(100)
            
            if plan:
                status_text.success("Plan generated successfully!")
                
                # 保存到session_state，方便后面下载
                st.session_state['current_plan'] = plan
                st.session_state['skill'] = skill
                
                # 展示结果区
                st.divider()
                st.subheader(f"📋 Learning Roadmap: {plan['skill']}")
                st.caption(f"Duration: {plan['total_weeks']} weeks | Weekly: {hours}h")
                
                # 统计卡片
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Stages", len(plan['stages']))
                with col2:
                    total_tasks = sum(len(s['tasks']) for s in plan['stages'])
                    st.metric("Total Tasks", total_tasks)
                with col3:
                    total_hours = sum(s['hours'] for s in plan['stages'])
                    st.metric("Total Hours", total_hours)
                
                # 展示每个阶段
                for i, stage in enumerate(plan['stages'], 1):
                    with st.expander(f"Stage {i}: {stage['stage_name']} ({stage['week']})", expanded=i==1):
                        st.markdown(f"**🎯 Milestone:** {stage['milestone']}")
                        st.markdown(f"**⏱️ Hours:** {stage['hours']}h")
                        
                        # 任务表格
                        tasks_data = []
                        for task in stage['tasks']:
                            tasks_data.append({
                                "Task": task['name'],
                                "Hours": task['hours'],
                                "Type": task['type'].capitalize()
                            })
                        
                        st.table(tasks_data)
                        
                        st.markdown(f"**📦 Deliverable:** {stage['deliverable']}")
                
                # 建议部分
                if 'tips' in plan and plan['tips']:
                    st.divider()
                    st.subheader("💡 Pro Tips")
                    for tip in plan['tips']:
                        st.markdown(f"- {tip}")
                
                # 导出功能
                st.divider()
                st.subheader("📤 Export")
                
                col1, col2 = st.columns(2)
                
                # 导出JSON
                with col1:
                    json_str = json.dumps(plan, indent=2, ensure_ascii=False)
                    st.download_button(
                        label="Download JSON",
                        data=json_str,
                        file_name=f"learning_plan_{skill.replace(' ', '_')}.json",
                        mime="application/json"
                    )
                
                # 导出ICS（日历文件）
                with col2:
                    if st.button("Generate Calendar (.ics)"):
                        cal = Calendar()
                        cal.add('prodid', '-//AI Learning Planner//')
                        cal.add('version', '2.0')
                        
                        # 为每个任务创建日历事件（简化版：均匀分布在时间段内）
                        current_date = start_date
                        end_date = deadline
                        days_span = (end_date - current_date).days
                        
                        task_count = 0
                        for stage in plan['stages']:
                            for task in stage['tasks']:
                                # 简单分配日期（实际可以优化算法）
                                if days_span > 0:
                                    task_day = current_date + timedelta(days=(task_count * days_span // total_tasks))
                                else:
                                    task_day = current_date
                                
                                event = Event()
                                event.add('summary', f"[{plan['skill']}] {task['name']}")
                                event.add('dtstart', task_day)
                                event.add('dtend', task_day + timedelta(hours=task['hours']))
                                event.add('description', f"Stage: {stage['stage_name']}\nType: {task['type']}")
                                event['uid'] = str(uuid.uuid4())
                                
                                cal.add_component(event)
                                task_count += 1
                        
                        ics_content = cal.to_ical()
                        st.download_button(
                            label="Download Calendar",
                            data=ics_content,
                            file_name=f"learning_plan_{skill.replace(' ', '_')}.ics",
                            mime="text/calendar"
                        )
            
            else:
                st.error("Failed to generate plan. Please check your API key.")
                
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.info("Please check if API key is correct in config.py")

# 页脚
st.divider()
st.caption("Made with ❤️ using Streamlit + DeepSeek | Cache enabled to save costs")