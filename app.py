import streamlit as st
import pandas as pd
from openai import OpenAI
from datetime import datetime
import warnings
import streamlit.components.v1 as components
import os
import markdown
import re


#  0. 全局配置
warnings.filterwarnings("ignore")

API_KEY = "sk-iyznjopbdylxmcjtteregjqpeixnsmbnuwfpvaiejpbqdomd"
BASE_URL = "https://api.siliconflow.cn/v1"
MODEL_NAME = "deepseek-ai/DeepSeek-V3"



st.set_page_config(
    page_title="爱选型",
    layout="wide",
    initial_sidebar_state="expanded"
)

#  1. 状态机初始化
if "current_page" not in st.session_state:
    st.session_state.current_page = "💬 选型助理"
if "index_expanded" not in st.session_state:
    st.session_state.index_expanded = False
if "open_components" not in st.session_state:
    st.session_state.open_components = {}
if "history_log" not in st.session_state:
    st.session_state.history_log = []
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_history_idx" not in st.session_state:
    st.session_state.current_history_idx = None


def nav_to(page_name):
    st.session_state.current_page = page_name


def toggle_index():
    st.session_state.index_expanded = not st.session_state.index_expanded


def toggle_comp(comp_name):
    st.session_state.open_components[comp_name] = not st.session_state.open_components.get(comp_name, False)


def generate_short_title(text):
    keywords = ["气缸", "气爪", "电磁阀", "比例阀", "减压阀", "真空", "吸盘", "传感器", "SMC", "亚德客", "Festo",
                "推力", "无杆缸", "滑台", "过滤器", "选型", "气源"]
    found_keys = [k for k in keywords if k in text]
    if found_keys:
        return f"关于【{found_keys[0]}】的咨询"
    else:
        return text[:10] + "..." if len(text) > 10 else text


def load_history(idx):
    st.session_state.messages = list(st.session_state.history_log[idx]["messages"])
    st.session_state.current_history_idx = idx
    st.session_state.current_page = "💬 选型助理"


def new_chat():
    st.session_state.messages = []
    st.session_state.current_history_idx = None
    st.session_state.current_page = "💬 选型助理"


#  2. CSS 样式
st.markdown("""
<style>
    .stException, .stAlert, [data-testid="stException"] { display: none !important; }
    .block-container { padding-top: 2rem !important; padding-bottom: 6rem !important; max-width: 95% !important; }
    .big-title { font-size: 90px !important; font-weight: 900; text-align: left !important; color: #111 !important; margin-top: 10px; margin-bottom: 5px; letter-spacing: 4px; }
    .sub-title { font-size: 36px !important; color: #111 !important; font-weight: 600; margin-bottom: 45px; }
    hr.nav-hr { margin: 4px 0 !important; border: none !important; border-top: 1px solid #ebeef5 !important; }
    [data-testid="stSidebar"] .stButton > button { border: none !important; background-color: transparent !important; color: #333 !important; font-size: 16px !important; font-weight: 600 !important; justify-content: flex-start !important; padding: 8px 12px !important; transition: all 0.2s ease !important; }
    [data-testid="stSidebar"] .stButton > button:hover { background-color: #f0f2f5 !important; color: #1f50ff !important; border-radius: 8px !important; }
    [data-testid="stSidebar"] [data-testid="stExpander"] { border: none !important; background-color: transparent !important; box-shadow: none !important; }
    .user-chat-container { display: flex; justify-content: flex-end; align-items: flex-start; margin-bottom: 20px; width: 100%; }
    .user-bubble { background-color: #95ec69; color: #000; padding: 12px 16px; border-radius: 8px; position: relative; box-shadow: 0 1px 2px rgba(0,0,0,0.1); max-width: 70%; text-align: left; font-size: 16px; margin-right: 12px; }
    .user-bubble::after { content: ''; position: absolute; right: -6px; top: 14px; border-top: 6px solid transparent; border-bottom: 6px solid transparent; border-left: 6px solid #95ec69; }
    .user-avatar { width: 40px; height: 40px; background-color: #f0f0f0; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 24px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); }
    .stChatMessage { background-color: transparent !important; }
    [data-testid="stChatMessageContent"] { background-color: #ffffff !important; border-radius: 8px !important; padding: 15px !important; box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important; border: 1px solid #f0f0f0 !important; }
    [data-testid="stChatInput"] { border: 2px solid #dcdfe6 !important; border-radius: 16px !important; background-color: #ffffff !important; box-shadow: 0 6px 16px rgba(0,0,0,0.08) !important; padding: 5px 10px !important; transition: all 0.3s ease; }
    [data-testid="stChatInput"] > div { border: none !important; box-shadow: none !important; outline: none !important; background-color: transparent !important; }
    [data-testid="stChatInput"] textarea { box-shadow: none !important; outline: none !important; }
    [data-testid="stChatInput"]:focus-within { border-color: #1f50ff !important; box-shadow: 0 6px 16px rgba(31,80,255,0.15) !important; }
    [data-testid="stSidebar"] { background-color: #f7f8fa; border-right: 1px solid #ebeef5; }
</style>
""", unsafe_allow_html=True)

#  3. 数据加载
try:
    csv_path = r"F:\学校\毕设\我的\0314\Pneumatic_Selection\knowledge_graph_triples.csv"
    if not os.path.exists(csv_path):
        csv_path = 'knowledge_graph_triples.csv'

    df = pd.read_csv(csv_path)

    if len(df.columns) >= 3:
        cols = list(df.columns)
        df.rename(columns={cols[0]: 'Head', cols[1]: 'Relation', cols[2]: 'Tail'}, inplace=True)

    kb_text = df.to_string(index=False)
except Exception as e:
    df = pd.DataFrame()
    kb_text = f"暂无本地知识库"

#  4. 左侧导航栏
with st.sidebar:
    st.markdown("### 系统导航")
    st.button("💬 选型助理", on_click=nav_to, args=("💬 选型助理",), use_container_width=True)
    st.markdown("<hr class='nav-hr'>", unsafe_allow_html=True)
    st.button("🌌 知识图谱", on_click=nav_to, args=("🌌 知识图谱",), use_container_width=True)
    st.markdown("<hr class='nav-hr'>", unsafe_allow_html=True)

    index_icon = "🔽" if st.session_state.index_expanded else "▶️"
    st.button(f"{index_icon} 元件索引", on_click=toggle_index, use_container_width=True)

    if st.session_state.index_expanded:
        if df.empty or 'Tail' not in df.columns:
            st.error("暂未读取到图谱数据")
        else:
            categories_map = {
                "执行件 (Actuators)": ["Actuator", "Actuators", "AirCylinder", "ElectricActuator", "Gripper", "Rodless",
                                       "Rotary", "Slide Table"],
                "控制件 (Valves)": ["Valve", "Valves", "Valve Island", "Proportional", "Fluid Control"],
                "气源处理 (Air Prep)": ["AirPreparation", "AirPrep", "Booster", "Regulator", "Micro Filter"],
                "真空系统 (Vacuum)": ["VacuumComponent", "Vacuum", "Pad", "Filter", "Generator"],
                "传感元件 (Sensors)": ["Sensor", "Sensors", "Position", "Pressure", "Flow"]
            }

            for label, target_classes in categories_map.items():
                with st.expander(label):
                    try:
                        series_list = df[df['Tail'].isin(target_classes)]['Head'].dropna().unique()
                        if len(series_list) > 0:
                            series_list = sorted(series_list)
                            for s in series_list:
                                is_open = st.session_state.open_components.get(s, False)
                                file_icon = "📂" if is_open else "📁"
                                st.button(f"{file_icon} {s}", key=f"comp_{s}", on_click=toggle_comp, args=(s,),
                                          use_container_width=True)

                                if is_open:
                                    params_df = df[df['Head'] == s]
                                    for _, p_row in params_df.iterrows():
                                        if p_row['Relation'] in ['CATEGORY', 'IS_A_CLASS', 'Class']:
                                            continue
                                        st.markdown(
                                            f"<div style='padding-left: 36px; padding-bottom: 4px; font-size: 13px; color: #666; font-family: monospace;'>▪ <b style='color: #444;'>{p_row['Relation']}</b>: {p_row['Tail']}</div>",
                                            unsafe_allow_html=True)
                        else:
                            st.caption("暂未收录该类数据")
                    except:
                        st.caption("加载异常")

    st.markdown("---")
    st.markdown("### 历史记录")
    st.button("⊕新建选型对话", on_click=new_chat, use_container_width=True)

    if len(st.session_state.history_log) == 0:
        st.caption(" ")
    else:
        for idx, item in enumerate(st.session_state.history_log):
            prefix = "🟢" if st.session_state.current_history_idx == idx else "💬"
            st.button(f"{prefix} {item['title']}", key=f"hist_btn_{idx}", on_click=load_history, args=(idx,),
                      use_container_width=True)

#  5. 主页面路由分发
if st.session_state.current_page == "💬 选型助理":
    if len(st.session_state.messages) == 0:
        st.markdown('<p class="big-title">爱选型(^_−)☆</p>', unsafe_allow_html=True)
        st.markdown('<p class="sub-title">更懂你的气动元件智能选型助手 —— Leslie in SCUT 2026</p>',
                    unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("收录参数", f"{len(df)} 条")
        c2.metric("覆盖品牌", "SMC, AirTAC, Festo")
        c3.metric("大模型已连接", "DeepSeek-V3")
        st.write("")
        st.write("")
    else:
        st.markdown("### 💬 爱选型 - 智能助理")
        st.divider()

    #对话与按钮渲染区
    for i, message in enumerate(st.session_state.messages):
        if message["role"] == "user":
            st.markdown(f"""
            <div class="user-chat-container">
                <div class="user-bubble">{message["content"]}</div>
                <div class="user-avatar">🐱</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(message["content"])

                c1, c2, c3 = st.columns([0.05, 0.05, 0.9])

                with c1:
                    if st.button("📋", key=f"c_{i}", help="复制"):
                        safe_content = message['content'].replace('`', '\\`')
                        components.html(f"<script>navigator.clipboard.writeText(`{safe_content}`);</script>", height=0)
                        st.toast("已复制")

                with c2:
                    save_clicked = st.button("💾", key=f"s_{i}", help="生成规格书")

                if save_clicked:
                    user_question = st.session_state.messages[i - 1]["content"] if i > 0 else "未提供具体工况"

                    # --- 修改 app.py 里的文档生成逻辑（约 180-200 行） ---
with st.spinner("正在执行特征抽离与公式渲染重构..."):
    # 1. 提取 AI 回复内容
    ai_raw_content = message['content']
    
    # 2. 调用之前的特征抽离函数（落实论文 4.3.1）
    bom_only_content = extract_bom_matrix(ai_raw_content)

    # 3. 构造规格书 Markdown 源码
    raw_md = f"# 气动系统选型技术报告\n\n> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n" + bom_only_content

    # 4. 执行交叉编译，注意这里我们不再依赖复杂的扩展，只确保基础 HTML 生成
    html_body = markdown.markdown(raw_md, extensions=['tables'])

    # 5. 注入“学术级”公式渲染引擎 MathJax 3.0 配置
    html_template = f"""<!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <script src="https://cdn.staticfile.net/mathjax/3.2.2/es5/tex-mml-chtml.min.js"></script>
    <script>
      window.MathJax = {{
        tex: {{
          inlineMath: [['$', '$']],
          displayMath: [['$$', '$$']],
          processEscapes: true
        }}
      }};
    </script>
    ... (保持 CSS 样式不变)

                        try:
                            client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
                            res = client.chat.completions.create(
                                model=MODEL_NAME,
                                messages=[{"role": "user", "content": doc_prompt}],
                                stream=False,
                                timeout=90
                            )

                            raw_md = f"# 选型技术规格书\n\n> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')} （UTC+8）\n\n" + \
                                     res.choices[0].message.content

                            html_body = markdown.markdown(raw_md, extensions=['tables'])

                            # 模拟论文中提到的 f_extract 映射函数
                            def extract_bom_matrix(text):
                                # 查找 Markdown 表格特征的正则
                                table_pattern = r'\|.*\|'
                                tables = re.findall(table_pattern, text)
                                if tables:
                                    # 这里模拟将非结构化文本降维过滤，仅保留表格核心内容
                                    return "\n".join(tables)
                                return text

                            bom_only_content = extract_bom_matrix(res.choices[0].message.content)

                            raw_md = f"# 选型技术规格书\n\n> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')} (UTC+0)\n\n" + bom_only_content

                            # --- 替换你的 HTML 模板定义部分 ---
                            # --- 替换你的 HTML 模板定义部分 ---
                            html_template = f"""<!DOCTYPE html>
                            <html>
                            <head>
                            <meta charset="utf-8">
                            <title>爱选型 - 技术报告</title>

                            <script src="https://cdn.staticfile.net/mathjax/3.2.2/es5/tex-mml-chtml.min.js"></script>
                            <script>
                              MathJax = {{
                                tex: {{
                                  inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],  // 识别行内公式
                                  displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']] // 识别独立行公式
                                }}
                              }};
                            </script>

                            <style>
                                body {{ font-family: 'Microsoft YaHei', sans-serif; line-height: 1.6; color: #333; max-width: 900px; margin: 40px auto; padding: 20px; }}
                                h1 {{ text-align: center; color: #1f50ff; border-bottom: 2px solid #1f50ff; padding-bottom: 10px; }}
                                h2 {{ color: #222; margin-top: 30px; border-left: 4px solid #1f50ff; padding-left: 10px; }}
                                table {{ width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 20px; font-size: 14px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }}
                                th, td {{ border: 1px solid #dcdfe6; padding: 12px 15px; text-align: left; }}
                                th {{ background-color: #f4f6f9; color: #333; font-weight: bold; text-transform: uppercase; }}
                                tr:nth-child(even) {{ background-color: #fafafa; }}
                                tr:hover {{ background-color: #f0f4ff; transition: 0.2s; }}
                                blockquote {{ border-left: 4px solid #ccc; margin: 15px 0; padding-left: 15px; color: #666; background: #f9f9f9; padding: 10px; }}
                            </style>
                            </head>
                            <body>
                            {html_body}
                            </body>
                            </html>"""

                            st.session_state["active_idx"] = i
                            st.session_state["active_content"] = html_template
                            st.rerun()
                        except Exception as e:
                            st.toast(f"云端网络超时或接口异常: {str(e)}", icon="⚠️")

            if st.session_state.get("active_idx") == i:
                    st.download_button(
                        label="下载报告 (.html)",
                        data=st.session_state.get("active_content", ""),
                        file_name=f"Spec_Report_{datetime.now().strftime('%m%d_%H%M')}.html",
                        mime="text/html",
                        key=f"d_{i}"
                    )

    user_input = st.chat_input("今天有什么是我可以帮到你的呢(*^▽^*)", accept_file=True)

    if user_input:
        chat_text = user_input.text if user_input.text else ""

        if user_input.files:
            uploaded_file = user_input.files[0]
            file_name = uploaded_file.name
            st.toast(f"成功接收附件: {file_name}", icon=" ")
            file_content = ""
            try:
                if file_name.endswith('.txt') or file_name.endswith('.md'):
                    file_content = uploaded_file.read().decode('utf-8')
                elif file_name.endswith('.csv'):
                    file_content = pd.read_csv(uploaded_file).to_markdown(index=False)
                elif file_name.endswith('.xlsx') or file_name.endswith('.xls'):
                    file_content = pd.read_excel(uploaded_file).to_markdown(index=False)
                else:
                    file_content = "请上传 .txt, .csv 或 .xlsx 格式。"
            except Exception as e:
                file_content = f"文件解析失败: {str(e)}"
            chat_text += f"\n\n*(📎 附件: {file_name})*\n\n**【文件内容如下】**：\n```\n{file_content}\n```"

        if chat_text.strip():
            st.session_state.messages.append({"role": "user", "content": chat_text.strip()})

            if st.session_state.current_history_idx is None:
                new_title = generate_short_title(chat_text.strip())
                st.session_state.history_log.insert(0,
                                                    {"title": new_title, "messages": list(st.session_state.messages)})
                st.session_state.current_history_idx = 0
                if len(st.session_state.history_log) > 5:
                    st.session_state.history_log = st.session_state.history_log[:5]
            else:
                st.session_state.history_log[st.session_state.current_history_idx]["messages"] = list(
                    st.session_state.messages)
            st.rerun()

    # AI 生成回复处理
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
        safe_kb = kb_text[:15000]

        system_prompt = f"""
        你是一个精通【机电一体化】的气动选型专家。

        【核心事实约束】：
        禁止检索外部网络与自身语料，必须且仅能从下列【知识库】提供的气动三元组矩阵中提取受力与耐压参数，当查询不到对应元件时，必须回复“抱歉，本地库暂中无对应参数，请等待补充”。

        【物理逻辑思维链 (CoT) 强制要求】：
        在进行任何代数计算前，必须严格遵守以下换算常量，不可使用近似值：
        1. 压力换算：1 MPa = 10^6 Pa = 10 bar。
        2. 长度换算：参与截面积计算前，毫米(mm)必须转换为米(m)，即 1 mm = 0.001 m，1 m^2 = 10^6 mm^2
        3. 常数：质量(kg)转化为力(N)时，必须使用 g = 9.81 N/kg，且圆周率取3.1415
        在进行选型推荐前，你必须在回复中显式执行以下校核：
        1. 计算推力需求 F_req：F = (m * g * μ + F_a)。
        2. 负载率 (η) 强制约束：
           - 静载荷或低速 (v < 100 mm/s)：η ≤ 0.8
           - 垂直顶升或中速 (v ≈ 300 mm/s)：η ≤ 0.5
           - 高速冲击 (v > 500 mm/s)：η ≤ 0.3
        3. 安全推力校核：理论推力 F_t 必须满足 F_t ≥ F / η。
        
        【最优解筛选策略（Tie-breaker Rules）】
        如果在知识库中匹配到多个满足推力与负载率要求的气缸型号，你必须严格按照以下优先级的顺序进行唯一解过滤，不可随机挑选：
        1. 能效最优原则：优先推荐满足条件的前提下，缸径（Bore Size）最小的那一款（以减少系统耗气量）。
        2. 轻量化原则：如果缸径相同，优先推荐属于“薄型气缸/紧凑型气缸”分类的型号。
        3. 经济性原则：综合考虑成本及使用寿命等因素推荐。
        4. 如果在上述选型原则中各有优势，则按元件名称（注意是器件名，不是品牌名，如CP96）的首字母排序优先推荐。此条原则仅作为评判，严禁在对话中体现。
        
        【物理计算输出模板】
        你的物理计算推理过程必须严格采用以下结构进行输出，不得擅自改变顺序：
        1. 实际负荷确认
        2. 负载率读取
        3. 物理计算推理
        4. 数据库匹配
        5. 工程建议（针对有特殊工况如粉尘环境时，需自动追加对应的工程建议；针对在本地知识库中有关联的多个元件时，给出配套建议；如以上均无则省略此条）

        【输出格式规训】：
        1. 必须输出包含【项号】、【元件类别】、【品牌型号】、【技术规格】的 Markdown 表格。
        2. 严禁使用 Emoji。
        3. 最终输出前执行 FCheck 自检，确保表格闭合且无非法字符。
        4. 必须使用 Streamlit 能够识别的 LaTeX 符号。在 LaTeX 中表示乘法请统一使用 \\cdot 或 \\times。当出现任何公式和字母系数，必须使用标准的 LaTeX 语法。行内公式请务必使用单个美元符号（例如 $E=mc^2$）包裹，独立行公式请务必使用双美元符号（例如$$F=ma$$）包裹。 严禁使用 \[ ... \] 或 \( ... \) 等定界符。”
        5. 严禁使用 <sub>、<sup> 或任何 HTML 标签来表示下标或指数。
        【知识库】
        {safe_kb}
        """


        with st.chat_message("assistant", avatar="🤖"):
            try:
                clean_messages = [{"role": "system", "content": system_prompt}]
                for msg in st.session_state.messages[-4:]:
                    clean_messages.append({"role": str(msg["role"]), "content": str(msg["content"])})

                stream = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=clean_messages,
                    stream=True,
                    temperature=0.0,
                    top_p=0.1,
                    timeout=30
                )


                def stream_data():
                    for chunk in stream:
                        if chunk.choices[0].delta.content:
                            yield chunk.choices[0].delta.content

                ai_reply = st.write_stream(stream_data)
                st.session_state.messages.append({"role": "assistant", "content": ai_reply})

                if st.session_state.current_history_idx is not None:
                    st.session_state.history_log[st.session_state.current_history_idx]["messages"] = list(
                        st.session_state.messages)

                st.rerun()

            except Exception as e:
                st.error(f"系统报错: {str(e)}")

elif st.session_state.current_page == "🌌 知识图谱":
    html_path = "knowledge_graph_interactive.html"
    if os.path.exists(html_path):
        try:
            with open(html_path, "r", encoding="utf-8") as f:
                html_data = f.read()
        except UnicodeDecodeError:
            with open(html_path, "r", encoding="gbk") as f:
                html_data = f.read()
        components.html(html_data, height=900, scrolling=False)
    else:
        st.error("系统缺失 `knowledge_graph_interactive.html`。")
