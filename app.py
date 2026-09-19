"""
AI Senior Companion - Streamlit Web Application
"Your simple, safe and trusted digital companion."
Designed with extreme empathy, simplicity, accessibility, and safety for senior citizens.
"""
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import streamlit as st
from PIL import Image

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import (
    APP_NAME,
    APP_TAGLINE,
    APP_VERSION,
    REMINDER_CATEGORIES,
    get_gemini_api_key
)
from database.database import (
    init_db,
    seed_demo_data,
    reset_demo_data,
    get_default_user,
    get_user_preferences,
    update_user_preferences,
    add_reminder,
    update_reminder_status,
    delete_reminder,
    get_trusted_contacts,
    add_trusted_contact,
    delete_trusted_contact
)
from services.gemini_service import gemini_service
from services.document_service import document_service
from services.scam_service import scam_service
from services.reminder_service import reminder_service
from services.guided_service import guided_service, PREDEFINED_TASKS
from services.safety_service import SafetyService
from utils.accessibility import get_accessibility_css
from utils.helpers import (
    t,
    format_friendly_date,
    get_greeting,
    generate_trusted_contact_url
)


# --- INITIALIZATION & SESSION SETUP ---
st.set_page_config(
    page_title=APP_NAME,
    page_icon="👴",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database and seed if empty
seed_demo_data()

# User & Session State
if "user" not in st.session_state:
    st.session_state.user = get_default_user()

if "preferences" not in st.session_state:
    st.session_state.preferences = get_user_preferences(st.session_state.user["id"])

if "current_page" not in st.session_state:
    st.session_state.current_page = "home"

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [
        {
            "role": "assistant",
            "content": f"Hello {st.session_state.user['name']}! I am your personal digital companion. How can I help you today? You can ask me about bills, messages, or everyday digital tasks."
        }
    ]

if "guided_task_name" not in st.session_state:
    st.session_state.guided_task_name = "Pay an electricity bill"
if "guided_step_idx" not in st.session_state:
    st.session_state.guided_step_idx = 0

if "prefill_scam_text" not in st.session_state:
    st.session_state.prefill_scam_text = ""
if "prefill_explain_text" not in st.session_state:
    st.session_state.prefill_explain_text = ""
if "flash_notice" not in st.session_state:
    st.session_state.flash_notice = None

# Current active preferences
pref = st.session_state.preferences
text_size = pref.get("text_size", "Large")
contrast_mode = pref.get("contrast_mode", "Standard")
language = pref.get("language", "English")
user_name = st.session_state.user.get("name", "Mr. Sharma")

# Inject Senior Accessibility CSS
st.markdown(get_accessibility_css(text_size, contrast_mode), unsafe_allow_html=True)


# --- ROUTING HELPER ---
def navigate_to(page_name: str):
    st.session_state.current_page = page_name
    st.rerun()


# --- SIDEBAR NAVIGATION ---
with st.sidebar:
    st.markdown(f"### 👴 {t('app_title', language)}")
    st.caption(f"_{t('tagline', language)}_")
    st.markdown("---")

    # High visibility navigation buttons
    nav_items = [
        ("home", t("nav_home", language)),
        ("companion", t("nav_companion", language)),
        ("explain", t("nav_explain", language)),
        ("scam", t("nav_scam", language)),
        ("guided", t("nav_guided", language)),
        ("reminders", t("nav_reminders", language)),
        ("my_day", t("nav_my_day", language)),
        ("trusted", t("nav_trusted", language)),
        ("settings", t("nav_settings", language))
    ]

    for page_key, label in nav_items:
        is_active = st.session_state.current_page == page_key
        button_label = f"👉 {label}" if is_active else label
        if st.button(button_label, key=f"nav_{page_key}"):
            st.session_state.current_page = page_key
            st.rerun()

    st.markdown("---")
    
    # Quick Language switcher
    st.markdown("**🌐 Language / भाषा**")
    lang_choice = st.radio(
        "Choose Language",
        ["English", "Hindi"],
        index=0 if language == "English" else 1,
        horizontal=True,
        label_visibility="collapsed"
    )
    if lang_choice != language:
        update_user_preferences(
            st.session_state.user["id"],
            text_size,
            contrast_mode,
            lang_choice,
            1
        )
        st.session_state.preferences["language"] = lang_choice
        st.rerun()

    # Trusted Contact Quick Card
    contacts = get_trusted_contacts(st.session_state.user["id"])
    if contacts:
        primary_contact = contacts[0]
        st.markdown(
            f"""
            <div style="background-color: #E0F2FE; border: 1.5px solid #0284C7; border-radius: 10px; padding: 12px; margin-top: 15px;">
                <b style="color: #0369A1;">👥 Trusted Contact:</b><br/>
                <span style="color: #0C4A6E; font-weight: 600;">{primary_contact['name']} ({primary_contact['relationship']})</span><br/>
                <span style="color: #0369A1; font-size: 14px;">📞 {primary_contact['phone']}</span>
            </div>
            """,
            unsafe_allow_html=True
        )

    # API Status Indicator
    st.markdown("<br/>", unsafe_allow_html=True)
    if gemini_service.is_configured():
        st.success("🟢 AI Connected (Gemini 2.5)", icon="✅")
    else:
        st.info("🟡 Demo Mode (Safe Fallback)", icon="ℹ️")


# Display flash messages if any
if st.session_state.flash_notice:
    st.success(st.session_state.flash_notice)
    st.session_state.flash_notice = None


# ==============================================================================
# VIEW 1: HOME PAGE
# ==============================================================================
if st.session_state.current_page == "home":
    greeting = get_greeting(user_name, language)
    st.markdown(f"# {greeting}")
    st.markdown(f"#### {t('how_can_i_help', language)}")

    # Proactive Banner
    st.markdown(
        f"""
        <div class="senior-card" style="border-left: 6px solid #1B4965;">
            <span style="font-size: 20px; font-weight: 700; color: #1B4965;">💡 {t('proactive_banner', language)}</span>
            <p style="margin-top: 6px; margin-bottom: 12px;">
                {'आपका बिजली का बिल 2 दिन में देय है। क्या आप चाहते हैं कि मैं इसे सुरक्षित रूप से जमा करने का तरीका समझाऊँ?' if language == 'Hindi' else 'Your electricity bill is due in 2 days. Would you like me to guide you through checking and paying it safely?'}
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    col_pro1, col_pro2 = st.columns([1, 1])
    with col_pro1:
        if st.button("🧭 " + ("हाँ, मुझे तरीका सिखाएं" if language == "Hindi" else "Yes, Guide Me Step-by-Step"), key="home_guide_btn"):
            st.session_state.guided_task_name = "Pay an electricity bill"
            st.session_state.guided_step_idx = 0
            navigate_to("guided")
    with col_pro2:
        if st.button("📄 " + ("बिल का विवरण देखें" if language == "Hindi" else "View Bill Breakdown"), key="home_view_bill"):
            navigate_to("explain")

    st.markdown("<br/>", unsafe_allow_html=True)

    # Today's Priority Reminders
    categorized = reminder_service.get_categorized_reminders(st.session_state.user["id"])
    today_rems = categorized["today"]

    st.markdown(f"### 📋 {t('today_heading', language)}")
    if today_rems:
        for rem in today_rems:
            cat_icon = "💊" if rem["category"] == "Medicine" else ("🧾" if rem["category"] == "Bills" else "🏥")
            st.markdown(
                f"""
                <div class="senior-card" style="padding: 16px; margin-bottom: 10px;">
                    <span style="font-size: 22px; font-weight: bold;">{cat_icon} {rem['title']}</span><br/>
                    <span style="color: #475569;">⏰ <b>{rem['due_time']}</b> | {rem['category']} | {rem.get('notes', '')}</span>
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        st.info("No more reminders due for today. Have a peaceful day!" if language == "English" else "आज के लिए कोई जरूरी काम शेष नहीं है। आपका दिन सुखद रहे!")

    st.markdown("<br/>", unsafe_allow_html=True)

    # 4 Large Action Cards
    st.markdown(f"### 🚀 {t('quick_help', language)}")
    col1, col2 = st.columns(2)
    with col1:
        if st.button(t("btn_explain", language), key="home_btn_explain"):
            navigate_to("explain")
        if st.button(t("btn_scam", language), key="home_btn_scam"):
            navigate_to("scam")

    with col2:
        if st.button(t("btn_guided", language), key="home_btn_guided"):
            navigate_to("guided")
        if st.button(t("btn_reminder", language), key="home_btn_reminder"):
            navigate_to("reminders")

    st.markdown("<br/>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style="text-align: center; color: #64748B; padding: 20px;">
            <p>💬 <i>"Just tell me what you need in your own words. I am here to help you."</i></p>
        </div>
        """,
        unsafe_allow_html=True
    )


# ==============================================================================
# VIEW 2: AI COMPANION (CHAT)
# ==============================================================================
elif st.session_state.current_page == "companion":
    st.markdown(f"# 🤖 {t('nav_companion', language)}")
    st.caption("Ask me any question in simple everyday words. I explain things patiently without confusing jargon.")

    # Render previous messages
    for msg in st.session_state.chat_messages:
        role_label = "👴 You" if msg["role"] == "user" else "🤖 Companion"
        bg_card = "#F1F5F9" if msg["role"] == "user" else "#FFFFFF"
        border = "1.5px solid #CBD5E1" if msg["role"] == "user" else "2px solid #1B4965"
        st.markdown(
            f"""
            <div style="background-color: {bg_card}; border: {border}; border-radius: 12px; padding: 18px; margin-bottom: 12px;">
                <b style="color: #1B4965;">{role_label}:</b>
                <p style="margin-top: 6px; margin-bottom: 0;">{msg['content']}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        # If assistant recommended a connected workflow
        if msg.get("suggested_action") == "scam_shield":
            st.warning("⚠️ This message looks like it may be a scam. Would you like to check it in Scam Shield?")
            if st.button("🛡️ Open Scam Shield to Verify", key=f"rec_scam_{msg.get('action_id', 1)}"):
                st.session_state.prefill_scam_text = msg.get("original_text", "")
                navigate_to("scam")
        elif msg.get("suggested_action") == "explain":
            st.info("📄 Would you like me to break down this document or bill?")
            if st.button("📄 Open Explain Something", key=f"rec_exp_{msg.get('action_id', 1)}"):
                st.session_state.prefill_explain_text = msg.get("original_text", "")
                navigate_to("explain")
        elif msg.get("suggested_action") == "guided_help":
            st.info("🧭 Would you like step-by-step guidance for this task?")
            if st.button("🧭 Open Guided Help", key=f"rec_gui_{msg.get('action_id', 1)}"):
                navigate_to("guided")

    # Sample prompt buttons for ease of seniors
    st.markdown("<br/>**Quick questions you can ask with one click:**", unsafe_allow_html=True)
    sample_col1, sample_col2 = st.columns(2)
    selected_sample = None
    with sample_col1:
        if st.button("❓ 'I received a strange bank message about winning a lottery.'"):
            selected_sample = "I received a strange bank message saying I won ₹25 lakh and asking for ₹5,000 fee."
        if st.button("❓ 'I don't understand my electricity bill charges.'"):
            selected_sample = "I don't understand my electricity bill charges. Can you help me read it?"
    with sample_col2:
        if st.button("❓ 'Help me book a doctor appointment.'"):
            selected_sample = "How do I book a routine doctor appointment online?"
        if st.button("❓ 'मुझे कल डॉक्टर को कॉल करना है।'"):
            selected_sample = "मुझे कल सुबह 10 बजे डॉक्टर को कॉल करने के लिए याद दिलाना।"

    # User Input Form
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_input(
            "Your Question / आपका सवाल:",
            value=selected_sample if selected_sample else "",
            placeholder=t("ask_input_placeholder", language),
            key="companion_input"
        )
        col_submit, col_voice = st.columns([3, 1])
        with col_submit:
            submitted = st.form_submit_button("💬 Send / पूछें")
        with col_voice:
            voice_hint = st.caption("🎤 " + t("voice_fallback", language))

    if (submitted and user_input.strip()) or selected_sample:
        prompt_text = user_input.strip() if submitted and user_input.strip() else selected_sample
        
        # Guardrail: Mask sensitive credentials
        sanitized_input, detected_sensitive = SafetyService.sanitize_user_input(prompt_text)
        if detected_sensitive:
            st.warning("🔒 For your safety, secret OTPs, PINs, or card numbers have been masked before processing.")

        # Check domain disclaimer
        disclaimer = SafetyService.get_domain_disclaimer(sanitized_input, language)

        # Append User message
        st.session_state.chat_messages.append({"role": "user", "content": sanitized_input})

        # Generate Response
        res = gemini_service.generate_chat_response(
            st.session_state.chat_messages,
            user_name=user_name,
            language=language
        )

        reply_content = res["text"]
        if disclaimer:
            reply_content = f"{disclaimer}\n\n{reply_content}"

        action_id = len(st.session_state.chat_messages)
        st.session_state.chat_messages.append({
            "role": "assistant",
            "content": reply_content,
            "suggested_action": res.get("suggested_action"),
            "original_text": sanitized_input,
            "action_id": action_id
        })
        st.rerun()


# ==============================================================================
# VIEW 3: EXPLAIN SOMETHING
# ==============================================================================
elif st.session_state.current_page == "explain":
    st.markdown(f"# 📄 {t('nav_explain', language)}")
    st.caption("Upload an image, PDF bill, or paste the text of any letter, notice, or message. I will explain it in simple everyday words.")

    tab_text, tab_file = st.tabs(["📝 Paste Text / Load Sample", "📎 Upload Image or PDF"])

    input_text = ""
    input_image = None

    with tab_text:
        col_sample1, col_sample2 = st.columns(2)
        with col_sample1:
            if st.button("📋 Load Sample Electricity Bill (BRPL ₹2,450)"):
                sample_bill_path = os.path.join(os.path.dirname(__file__), "assets", "sample_bills", "sample_electricity_bill.txt")
                if os.path.exists(sample_bill_path):
                    with open(sample_bill_path, "r", encoding="utf-8") as f:
                        st.session_state.prefill_explain_text = f.read()
                    st.rerun()

        with col_sample2:
            if st.button("🔄 Clear Text"):
                st.session_state.prefill_explain_text = ""
                st.rerun()

        input_text = st.text_area(
            "Paste the text of your bill or document here:",
            value=st.session_state.prefill_explain_text,
            height=200,
            placeholder="e.g. BSES Electricity bill due 25 September for Rs 2,450..."
        )

    with tab_file:
        uploaded_file = st.file_uploader(
            "Choose a picture or PDF document:",
            type=["png", "jpg", "jpeg", "pdf"],
            help="You can upload an electricity bill, water bill, medical slip, or bank SMS screenshot."
        )
        if uploaded_file is not None:
            if uploaded_file.name.lower().endswith(".pdf"):
                pdf_text = document_service.extract_text_from_pdf(uploaded_file.read())
                input_text = pdf_text
                st.success(f"Extracted text from PDF: {uploaded_file.name}")
            else:
                input_image = Image.open(uploaded_file)
                st.image(input_image, caption="Uploaded Document", use_column_width=True)

    if st.button("🔍 Explain This to Me Simply", key="btn_run_explain"):
        if not input_text and not input_image:
            st.warning("Please upload a file or paste text first.")
        else:
            with st.spinner("Reading and simplifying the document for you..."):
                explanation = document_service.explain_content(
                    text_content=input_text,
                    image=input_image,
                    language=language
                )
                st.session_state["last_explanation"] = explanation

    # Render Explanation Results
    if "last_explanation" in st.session_state:
        exp = st.session_state["last_explanation"]
        st.markdown("<br/>", unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="senior-card" style="border-top: 6px solid #1B4965;">
                <span class="badge-low" style="margin-bottom: 12px;">📑 {exp.document_type}</span>
                <h2>{exp.simple_summary}</h2>
            </div>
            """,
            unsafe_allow_html=True
        )

        col_amt, col_due, col_sender = st.columns(3)
        with col_amt:
            amt_val = exp.amount_to_pay if exp.amount_to_pay else "N/A"
            st.metric(label="AMOUNT TO PAY / राशि", value=amt_val)
        with col_due:
            due_val = exp.due_date if exp.due_date else "N/A"
            st.metric(label="DUE DATE / अंतिम तिथि", value=due_val)
        with col_sender:
            sender_val = exp.provider_or_sender if exp.provider_or_sender else "N/A"
            st.metric(label="ORGANIZATION / विभाग", value=sender_val)

        st.markdown("### 🔍 Important Information")
        for detail in exp.important_details:
            st.markdown(f"• {detail}")

        st.markdown("### 📌 What You Need To Do")
        for action in exp.what_you_need_to_do:
            st.markdown(f"✅ **{action}**")

        if exp.safety_warning:
            st.warning(f"⚠️ **Safety Note:** {exp.safety_warning}")

        st.markdown("<br/>", unsafe_allow_html=True)
        st.markdown("### 🤝 Next Steps I Can Do For You:")
        col_act1, col_act2 = st.columns(2)
        with col_act1:
            if st.button("🔔 Set Reminder for this Due Date", key="exp_set_rem"):
                today_str = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
                rem_title = f"{exp.document_type} Due: {exp.amount_to_pay or ''}"
                add_reminder(
                    st.session_state.user["id"],
                    title=rem_title,
                    category="Bills",
                    due_date=today_str,
                    due_time="18:00",
                    notes=f"Provider: {exp.provider_or_sender}. Verified via Explain Something."
                )
                st.session_state.flash_notice = f"Reminder set successfully for {rem_title}!"
                navigate_to("reminders")

        with col_act2:
            if st.button("🧭 Guide Me Step-by-Step to Pay This", key="exp_guide"):
                st.session_state.guided_task_name = "Pay an electricity bill"
                st.session_state.guided_step_idx = 0
                navigate_to("guided")


# ==============================================================================
# VIEW 4: SCAM SHIELD
# ==============================================================================
elif st.session_state.current_page == "scam":
    st.markdown(f"# 🛡️ {t('nav_scam', language)}")
    st.caption("Paste any suspicious SMS, WhatsApp message, email, or lottery notice. I will tell you if it shows signs of scam and how to stay safe.")

    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        if st.button("📋 Load Sample: Lottery Prize Scam"):
            scam_path = os.path.join(os.path.dirname(__file__), "assets", "sample_scams", "lottery_scam.txt")
            if os.path.exists(scam_path):
                with open(scam_path, "r", encoding="utf-8") as f:
                    st.session_state.prefill_scam_text = f.read()
                st.rerun()

    with col_s2:
        if st.button("📋 Load Sample: Electricity Cutoff Scam"):
            scam_path = os.path.join(os.path.dirname(__file__), "assets", "sample_scams", "utility_scam.txt")
            if os.path.exists(scam_path):
                with open(scam_path, "r", encoding="utf-8") as f:
                    st.session_state.prefill_scam_text = f.read()
                st.rerun()

    with col_s3:
        if st.button("🔄 Clear Message"):
            st.session_state.prefill_scam_text = ""
            st.rerun()

    scam_input = st.text_area(
        "Enter or paste the suspicious message here:",
        value=st.session_state.prefill_scam_text,
        height=140,
        placeholder="e.g. You have won Rs 25 Lakh. Transfer Rs 5,000 fee to claim..."
    )

    scam_file = st.file_uploader("Or upload screenshot of message:", type=["png", "jpg", "jpeg"])
    scam_img = Image.open(scam_file) if scam_file else None

    if st.button("🛡️ Check This for Scams", key="btn_check_scam"):
        if not scam_input and not scam_img:
            st.warning("Please paste a message or upload a screenshot to check.")
        else:
            with st.spinner("Analyzing message for safety risks..."):
                analysis = scam_service.analyze_scam(
                    message_text=scam_input,
                    image=scam_img,
                    language=language
                )
                st.session_state["last_scam_analysis"] = analysis

    if "last_scam_analysis" in st.session_state:
        res = st.session_state["last_scam_analysis"]
        st.markdown("<br/>", unsafe_allow_html=True)

        badge_class = "badge-high" if res.risk_level == "HIGH" else ("badge-medium" if res.risk_level == "MEDIUM" else "badge-low")
        risk_emoji = "🚨" if res.risk_level == "HIGH" else ("⚠️" if res.risk_level == "MEDIUM" else "✅")
        st.markdown(
            f"""
            <div class="senior-card" style="border-left: 8px solid {'#EF4444' if res.risk_level == 'HIGH' else '#F59E0B'};">
                <span class="{badge_class}" style="font-size: 18px;">{risk_emoji} RISK LEVEL: {res.risk_level}</span>
                <h3 style="margin-top: 12px;">{res.summary}</h3>
                <span style="color: #64748B; font-size: 14px;">Assessment Confidence: {res.confidence.upper()}</span>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("### ⚠️ Why This May Be Risky (Warning Signs):")
        for sign in res.warning_signs:
            st.markdown(f"• 🚩 {sign}")

        st.markdown("<br/>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style="background-color: #FEF2F2; border: 2px solid #F87171; border-radius: 12px; padding: 20px;">
                <b style="color: #991B1B; font-size: 20px;">🚫 WHAT YOU SHOULD NEVER DO:</b>
            """,
            unsafe_allow_html=True
        )
        for d in res.do_not_do:
            st.markdown(f"<span style='color: #B91C1C; font-size: 18px;'>❌ {d}</span>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<br/>", unsafe_allow_html=True)
        st.markdown("### 🛡️ Safe Recommended Next Steps:")
        for step in res.safe_next_steps:
            st.markdown(f"• 🟢 {step}")

        # Connected Action: Ask Trusted Contact
        st.markdown("<br/>", unsafe_allow_html=True)
        contacts = get_trusted_contacts(st.session_state.user["id"])
        if contacts:
            trusted_person = contacts[0]
            st.markdown(
                f"""
                <div class="senior-card" style="background-color: #F0FDF4; border: 1.5px solid #22C55E;">
                    <b style="color: #166534; font-size: 20px;">👥 {t('trusted_contact_alert', language)}</b>
                    <p>You can send this message to <b>{trusted_person['name']} ({trusted_person['relationship']})</b> to help you verify it safely.</p>
                </div>
                """,
                unsafe_allow_html=True
            )
            share_msg = f"Hi {trusted_person['name']}, I received this suspicious message: '{scam_input[:100]}...'. My AI Companion flagged it as {res.risk_level} RISK. Could you please review it for me before I do anything?"
            wa_url = generate_trusted_contact_url(trusted_person["phone"], share_msg)
            
            st.markdown(
                f"""
                <a href="{wa_url}" target="_blank" style="text-decoration: none;">
                    <button style="background-color: #22C55E; color: white; border: none; padding: 14px 24px; font-size: 18px; font-weight: bold; border-radius: 10px; width: 100%; cursor: pointer;">
                        📱 WhatsApp / Message {trusted_person['name']} to Verify
                    </button>
                </a>
                """,
                unsafe_allow_html=True
            )


# ==============================================================================
# VIEW 5: GUIDED HELP
# ==============================================================================
elif st.session_state.current_page == "guided":
    st.markdown(f"# 🧭 {t('nav_guided', language)}")
    st.caption("I break down digital tasks into small, patient steps. Take all the time you need. No real payments or bookings are made here.")

    # Task selector
    preset_tasks = list(PREDEFINED_TASKS.keys())
    current_selection = st.selectbox(
        "Choose a task to learn / काम चुनें:",
        preset_tasks,
        index=0 if st.session_state.guided_task_name not in preset_tasks else preset_tasks.index(st.session_state.guided_task_name)
    )
    if current_selection != st.session_state.guided_task_name:
        st.session_state.guided_task_name = current_selection
        st.session_state.guided_step_idx = 0
        st.rerun()

    guided_task = guided_service.get_task(st.session_state.guided_task_name, language)
    total_steps = len(guided_task.steps)
    step_idx = min(st.session_state.guided_step_idx, total_steps - 1)
    current_step = guided_task.steps[step_idx]

    # Progress bar
    progress_val = (step_idx + 1) / total_steps
    st.progress(progress_val)
    st.markdown(f"**Step {step_idx + 1} of {total_steps}**")

    # Step Card
    st.markdown(
        f"""
        <div class="senior-card" style="border-left: 6px solid #1B4965;">
            <h2 style="color: #1B4965;">Step {current_step.step_number}: {current_step.title}</h2>
            <p style="font-size: 22px; margin-top: 14px; margin-bottom: 14px;">{current_step.description}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    if current_step.helpful_tip:
        st.info(f"💡 **Helpful Tip:** {current_step.helpful_tip}")

    if current_step.safety_reminder:
        st.warning(f"🛡️ **Safety Checkpoint:** {current_step.safety_reminder}")

    col_prev, col_next = st.columns([1, 2])
    with col_prev:
        if step_idx > 0:
            if st.button("← Previous Step", key="btn_prev_step"):
                st.session_state.guided_step_idx -= 1
                st.rerun()

    with col_next:
        if step_idx < total_steps - 1:
            if st.button(f"✅ {current_step.action_button_label}", key="btn_next_step"):
                st.session_state.guided_step_idx += 1
                st.rerun()
        else:
            if st.button("🎉 " + t("finish_button", language), key="btn_finish_step"):
                st.success("Great job! You have successfully completed this task guide.")
                st.session_state.guided_step_idx = 0


# ==============================================================================
# VIEW 6: MY REMINDERS
# ==============================================================================
elif st.session_state.current_page == "reminders":
    st.markdown(f"# 🔔 {t('nav_reminders', language)}")
    st.caption("Tell me what you need to remember in plain English or Hindi, or fill in the simple form below.")

    # Natural Language Quick Add
    with st.expander("🗣️ Speak or Type to Add a Reminder (AI Extraction)", expanded=True):
        nl_text = st.text_input(
            "What would you like me to remind you about?",
            placeholder="e.g. Remind me tomorrow at 10 AM to call Dr. Verma"
        )
        if st.button("➕ Parse & Add Reminder"):
            if nl_text.strip():
                with st.spinner("Understanding reminder details..."):
                    extracted = reminder_service.extract_reminder(nl_text, language)
                    add_reminder(
                        st.session_state.user["id"],
                        title=extracted.title,
                        category=extracted.category,
                        due_date=extracted.date,
                        due_time=extracted.time,
                        recurrence=extracted.recurrence
                    )
                    st.success(f"Added reminder: '{extracted.title}' on {extracted.date} at {extracted.time} ({extracted.category})")
                    st.rerun()

    # Manual Form
    with st.expander("📝 Or Add Using Form"):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            form_title = st.text_input("Reminder Title", placeholder="e.g. Blood Pressure Medicine")
            form_cat = st.selectbox("Category", REMINDER_CATEGORIES)
        with col_f2:
            form_date = st.date_input("Date", min_value=datetime.now().date())
            form_time = st.time_input("Time", value=datetime.strptime("09:00", "%H:%M").time())
        form_notes = st.text_input("Notes (Optional)", placeholder="e.g. Take after lunch with water")
        if st.button("Save Reminder"):
            if form_title.strip():
                add_reminder(
                    st.session_state.user["id"],
                    title=form_title.strip(),
                    category=form_cat,
                    due_date=form_date.strftime("%Y-%m-%d"),
                    due_time=form_time.strftime("%H:%M"),
                    notes=form_notes
                )
                st.success("Reminder saved!")
                st.rerun()

    # Reminder Lists
    cat_rems = reminder_service.get_categorized_reminders(st.session_state.user["id"])
    t_today, t_upcoming, t_completed = st.tabs(["📅 Today", "⏳ Upcoming", "✅ Completed"])

    with t_today:
        if not cat_rems["today"]:
            st.info("No reminders for today!")
        for rem in cat_rems["today"]:
            c_info, c_action = st.columns([3, 1])
            with c_info:
                st.markdown(f"**⏰ {rem['due_time']}** — **{rem['title']}** ({rem['category']})")
                if rem.get("notes"):
                    st.caption(rem["notes"])
            with c_action:
                if st.button("Done ✅", key=f"done_{rem['id']}"):
                    update_reminder_status(rem["id"], "COMPLETED")
                    st.rerun()

    with t_upcoming:
        if not cat_rems["upcoming"]:
            st.info("No upcoming reminders.")
        for rem in cat_rems["upcoming"]:
            c_info, c_action = st.columns([3, 1])
            with c_info:
                friendly_d = format_friendly_date(rem["due_date"], language)
                st.markdown(f"**{friendly_d} at {rem['due_time']}** — **{rem['title']}** ({rem['category']})")
                if rem.get("notes"):
                    st.caption(rem["notes"])
            with c_action:
                if st.button("Delete 🗑️", key=f"del_{rem['id']}"):
                    delete_reminder(rem["id"])
                    st.rerun()

    with t_completed:
        if not cat_rems["completed"]:
            st.info("No completed reminders yet.")
        for rem in cat_rems["completed"]:
            st.markdown(f"~~{rem['title']}~~ (Completed)")


# ==============================================================================
# VIEW 7: MY DAY
# ==============================================================================
elif st.session_state.current_page == "my_day":
    st.markdown(f"# 📅 {t('nav_my_day', language)}")
    
    # Proactive morning check-in briefing
    briefing = reminder_service.generate_proactive_briefing(user_name, st.session_state.user["id"], language)
    st.markdown(
        f"""
        <div class="senior-card" style="border-left: 6px solid #10B981;">
            {briefing}
        </div>
        """,
        unsafe_allow_html=True
    )

    # Proactive Follow-up Actions
    st.markdown("### 🔔 Suggested Quick Actions for Today:")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("💊 Check Today's Medicines"):
            navigate_to("reminders")
    with c2:
        if st.button("🧭 Guide Me to Pay Pending Bill"):
            st.session_state.guided_task_name = "Pay an electricity bill"
            st.session_state.guided_step_idx = 0
            navigate_to("guided")


# ==============================================================================
# VIEW 8: TRUSTED HELP
# ==============================================================================
elif st.session_state.current_page == "trusted":
    st.markdown(f"# 👥 {t('nav_trusted', language)}")
    st.caption("Configure a trusted child, relative, or caregiver whom you can contact with one tap when you need help.")

    contacts = get_trusted_contacts(st.session_state.user["id"])
    if contacts:
        for c in contacts:
            st.markdown(
                f"""
                <div class="senior-card" style="border-left: 6px solid #0284C7;">
                    <h3>👤 {c['name']} ({c['relationship']})</h3>
                    <p><b>Phone:</b> {c['phone']} | <b>Email:</b> {c.get('email', 'N/A')}</p>
                    <p style="color: #64748B;">{c.get('notes', '')}</p>
                </div>
                """,
                unsafe_allow_html=True
            )
            col_msg, col_del = st.columns([3, 1])
            with col_msg:
                draft_msg = f"Hi {c['name']}, I need your help looking at a digital task / message on my phone. Can you please call me when free?"
                wa_url = generate_trusted_contact_url(c["phone"], draft_msg)
                st.markdown(
                    f"""
                    <a href="{wa_url}" target="_blank">
                        <button style="background-color: #0284C7; color: white; border: none; padding: 12px 20px; border-radius: 8px; font-weight: bold; cursor: pointer; width: 100%;">
                            📲 Send Help Message to {c['name']}
                        </button>
                    </a>
                    """,
                    unsafe_allow_html=True
                )
            with col_del:
                if st.button(f"Remove 🗑️", key=f"del_contact_{c['id']}"):
                    delete_trusted_contact(c["id"])
                    st.rerun()

    # Add Contact
    with st.expander("➕ Add a Trusted Family Member"):
        name = st.text_input("Name", placeholder="e.g. Aarav Sharma")
        rel = st.text_input("Relationship", placeholder="e.g. Son, Daughter, Friend")
        phone = st.text_input("Mobile Phone Number", placeholder="e.g. +91 98765 43210")
        notes = st.text_input("Notes", placeholder="e.g. Available after 6 PM")
        if st.button("Save Trusted Person"):
            if name and phone:
                add_trusted_contact(st.session_state.user["id"], name, rel, phone, notes=notes)
                st.success(f"Added {name} to trusted contacts!")
                st.rerun()


# ==============================================================================
# VIEW 9: SETTINGS & ACCESSIBILITY
# ==============================================================================
elif st.session_state.current_page == "settings":
    st.markdown(f"# ⚙️ {t('nav_settings', language)}")
    st.caption("Personalize text size, contrast, and reset demo data.")

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        new_text_size = st.selectbox(
            "Text Size / अक्षरों का आकार:",
            ["Standard", "Large", "Extra Large"],
            index=["Standard", "Large", "Extra Large"].index(text_size)
        )
    with col_s2:
        new_contrast = st.selectbox(
            "Color Theme / इंटरफ़ेस रंग:",
            ["Standard", "High Contrast"],
            index=["Standard", "High Contrast"].index(contrast_mode)
        )

    if (new_text_size != text_size) or (new_contrast != contrast_mode):
        update_user_preferences(
            st.session_state.user["id"],
            new_text_size,
            new_contrast,
            language,
            1
        )
        st.session_state.preferences["text_size"] = new_text_size
        st.session_state.preferences["contrast_mode"] = new_contrast
        st.rerun()

    st.markdown("<br/>", unsafe_allow_html=True)
    st.markdown("### 🔑 AI Connection (Google Gemini)")
    current_key = get_gemini_api_key()
    if current_key:
        masked_key = current_key[:4] + "..." + current_key[-4:] if len(current_key) > 8 else "***"
        st.success(f"Active Gemini API Key: `{masked_key}`")
    else:
        st.warning("No `GEMINI_API_KEY` detected. The application is running in intelligent fallback mode with realistic demo responses. Add `GEMINI_API_KEY=your_key` in `.env` or Streamlit Secrets to enable live Gemini AI generation.")

    st.markdown("<br/>", unsafe_allow_html=True)
    st.markdown("### 🔄 Demo Data Reset")
    st.caption("Evaluators can click this button anytime to reset reminders, preferences, and contacts to the default demo state (Mr. Sharma).")
    if st.button("🔄 " + t("reset_demo", language), key="btn_reset_all"):
        reset_demo_data()
        st.session_state.clear()
        st.success("Demo data reset to original state!")
        st.rerun()
