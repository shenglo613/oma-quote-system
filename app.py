import streamlit as st
import streamlit_authenticator as stauth

st.set_page_config(
    page_title="OMA 零件報價系統",
    page_icon="🔧",
    layout="wide",
)

# ── 認證設定 ──
credentials = {
    "usernames": {
        username: {
            "name": user["name"],
            "password": user["password"],
        }
        for username, user in st.secrets["credentials"]["usernames"].items()
    }
}

# auto_hash=False：secrets.toml 儲存的是 bcrypt 雜湊，不需再次 hash
authenticator = stauth.Authenticate(
    credentials,
    st.secrets["cookie"]["name"],
    st.secrets["cookie"]["key"],
    cookie_expiry_days=int(st.secrets["cookie"]["expiry_days"]),
    auto_hash=True,
)

# 0.4.x: login() 結果存在 st.session_state，不回傳 tuple
authenticator.login(location="main")

authentication_status = st.session_state.get("authentication_status")
name     = st.session_state.get("name")
username = st.session_state.get("username")

if authentication_status is False:
    st.error("帳號或密碼錯誤")
    st.stop()

if authentication_status is None:
    st.info("請輸入帳號與密碼")
    st.stop()

# 登入成功 — 儲存 session
role = st.secrets["credentials"]["usernames"][username]["role"]
st.session_state["role"] = role

# ── 首頁內容 ──
st.title("🔧 OMA 零件報價系統")
st.markdown(f"歡迎，**{name}**（{role}）")
authenticator.logout(location="sidebar")

st.markdown("""
### 快速導覽
- **報價單** — 新增或編輯報價，計算成本與毛利
- **報價記錄** — 查詢歷史報價（V2）
- **系統設定** — 調整工資單價、關稅率等參數

從左側選單選擇功能開始使用。
""")
