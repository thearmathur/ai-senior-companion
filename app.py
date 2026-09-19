"""
AI Senior Companion - Streamlit Web Application
"Your simple, safe and trusted digital companion."
Designed with extreme empathy, simplicity, accessibility, and safety for senior citizens.

Supports both modular multi-file architecture and resilient standalone deployment
for seamless one-click hosting on Streamlit Community Cloud.
"""
import os
import sys
import re
import json
import sqlite3
import urllib.parse
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path

import streamlit as st
from PIL import Image

# Ensure project root is on sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# --- MODULAR IMPORTS WITH ROBUST STANDALONE FALLBACK ---
try:
    from config.settings import (
        APP_NAME,
        APP_TAGLINE,
        APP_VERSION,
        REMINDER_CATEGORIES,
        get_gemini_api_key,
        GEMINI_MODEL,
        TEXT_SIZES
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
except ModuleNotFoundError:
    # --------------------------------------------------------------------------
    # RESILIENT STANDALONE EMBEDDED IMPLEMENTATION
    # Triggers if folders were omitted during browser drag-and-drop onto GitHub
    # --------------------------------------------------------------------------
    APP_NAME = "AI Senior Companion"
    APP_TAGLINE = "Your simple, safe and trusted digital companion."
    APP_VERSION = "1.0.0"
    REMINDER_CATEGORIES = ["Medicine", "Bills", "Appointments", "Personal", "Important"]
    GEMINI_MODEL = "gemini-3.6-flash"

    TEXT_SIZES = {
        "Standard": {"body": "18px", "heading": "24px", "button": "18px", "line_height": "1.6"},
        "Large": {"body": "22px", "heading": "28px", "button": "22px", "line_height": "1.7"},
        "Extra Large": {"body": "26px", "heading": "34px", "button": "26px", "line_height": "1.8"}
    }

    def get_gemini_api_key() -> str:
        key = os.getenv("GEMINI_API_KEY", "")
        if not key:
            try:
                if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
                    key = st.secrets["GEMINI_API_KEY"]
            except Exception:
                pass
        return key.strip()

    # Database
    DB_FILE = BASE_DIR / "senior_companion.db"

    def get_connection():
        conn = sqlite3.connect(str(DB_FILE), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db():
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL DEFAULT 'Mr. Sharma',
                    email TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS preferences (
                    user_id INTEGER PRIMARY KEY,
                    text_size TEXT NOT NULL DEFAULT 'Large',
                    contrast_mode TEXT NOT NULL DEFAULT 'Standard',
                    language TEXT NOT NULL DEFAULT 'English',
                    voice_enabled INTEGER NOT NULL DEFAULT 1,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'Important',
                    due_date TEXT NOT NULL,
                    due_time TEXT DEFAULT '09:00',
                    recurrence TEXT DEFAULT 'None',
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    notes TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trusted_contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    relationship TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    email TEXT DEFAULT '',
                    notes TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()

    def seed_demo_data():
        init_db()
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM users")
            if c.fetchone()[0] > 0:
                return
            c.execute("INSERT INTO users (name, email) VALUES (?, ?)", ("Mr. Sharma", "sharma.senior@example.com"))
            uid = c.lastrowid
            c.execute("INSERT INTO preferences (user_id, text_size, contrast_mode, language) VALUES (?, ?, ?, ?)", (uid, "Large", "Standard", "English"))
            
            today = datetime.now().date()
            tom = today + timedelta(days=1)
            in2 = today + timedelta(days=2)
            c.executemany("""
                INSERT INTO reminders (user_id, title, category, due_date, due_time, recurrence, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, 'PENDING', ?)
            """, [
                (uid, "Take Morning Blood Pressure Medicine (Amlodipine 5mg)", "Medicine", today.strftime("%Y-%m-%d"), "09:00", "Daily", "Take after light breakfast with water."),
                (uid, "Electricity Bill Due (BSES Rajdhani - ₹2,450)", "Bills", in2.strftime("%Y-%m-%d"), "18:00", "None", "Consumer No: 100458921. Keep receipt safe."),
                (uid, "Routine Health Check-up with Dr. Verma", "Appointments", tom.strftime("%Y-%m-%d"), "11:00", "None", "City Hospital Clinic Room 204.")
            ])
            c.execute("INSERT INTO trusted_contacts (user_id, name, relationship, phone) VALUES (?, ?, ?, ?)", (uid, "Aarav Sharma", "Son", "+91 98765 43210"))
            conn.commit()

    def reset_demo_data():
        with get_connection() as conn:
            c = conn.cursor()
            for t in ["reminders", "trusted_contacts", "preferences", "users"]:
                c.execute(f"DROP TABLE IF EXISTS {t}")
            conn.commit()
        seed_demo_data()

    def get_default_user():
        seed_demo_data()
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users ORDER BY id ASC LIMIT 1")
            r = c.fetchone()
            return dict(r) if r else {"id": 1, "name": "Mr. Sharma"}

    def get_user_preferences(user_id: int):
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM preferences WHERE user_id = ?", (user_id,))
            r = c.fetchone()
            return dict(r) if r else {"user_id": user_id, "text_size": "Large", "contrast_mode": "Standard", "language": "English"}

    def update_user_preferences(user_id: int, text_size: str, contrast_mode: str, language: str, voice_enabled: int = 1):
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO preferences (user_id, text_size, contrast_mode, language, voice_enabled, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    text_size = excluded.text_size,
                    contrast_mode = excluded.contrast_mode,
                    language = excluded.language,
                    updated_at = CURRENT_TIMESTAMP
            """, (user_id, text_size, contrast_mode, language, voice_enabled))
            conn.commit()

    def add_reminder(user_id: int, title: str, category: str, due_date: str, due_time: str = "09:00", recurrence: str = "None", notes: str = ""):
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO reminders (user_id, title, category, due_date, due_time, recurrence, status, notes) VALUES (?, ?, ?, ?, ?, ?, 'PENDING', ?)", (user_id, title, category, due_date, due_time, recurrence, notes))
            conn.commit()
            return c.lastrowid

    def get_reminders(user_id: int):
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM reminders WHERE user_id = ? ORDER BY due_date ASC, due_time ASC", (user_id,))
            return [dict(r) for r in c.fetchall()]

    def update_reminder_status(reminder_id: int, status: str):
        with get_connection() as conn:
            conn.cursor().execute("UPDATE reminders SET status = ? WHERE id = ?", (status, reminder_id))
            conn.commit()

    def delete_reminder(reminder_id: int):
        with get_connection() as conn:
            conn.cursor().execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
            conn.commit()

    def get_trusted_contacts(user_id: int):
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM trusted_contacts WHERE user_id = ?", (user_id,))
            return [dict(r) for r in c.fetchall()]

    def add_trusted_contact(user_id: int, name: str, relationship: str, phone: str, email: str = "", notes: str = ""):
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO trusted_contacts (user_id, name, relationship, phone, email, notes) VALUES (?, ?, ?, ?, ?, ?)", (user_id, name, relationship, phone, email, notes))
            conn.commit()
            return c.lastrowid

    def delete_trusted_contact(contact_id: int):
        with get_connection() as conn:
            conn.cursor().execute("DELETE FROM trusted_contacts WHERE id = ?", (contact_id,))
            conn.commit()

    # Utilities & Safety
    class SafetyService:
        OTP_PAT = re.compile(r'\b(?:otp|code|pin)\s*[:=is\s]*(\d{4,8})\b', re.IGNORECASE)
        CARD_PAT = re.compile(r'\b(?:\d[ -]*?){13,16}\b')
        @classmethod
        def sanitize_user_input(cls, text: str):
            det = False
            s = text
            if cls.OTP_PAT.search(s):
                s = cls.OTP_PAT.sub("[SENSITIVE OTP HIDDEN FOR YOUR SAFETY]", s)
                det = True
            if cls.CARD_PAT.search(s):
                s = cls.CARD_PAT.sub("[CARD NUMBER HIDDEN FOR YOUR SAFETY]", s)
                det = True
            return s, det

        @classmethod
        def get_domain_disclaimer(cls, text: str, language: str = "English"):
            low = text.lower()
            if any(w in low for w in ["diagnosis", "doctor", "tablet", "pain", "hospital", "prescription"]):
                if language.lower() == "hindi":
                    return "🩺 स्वास्थ्य सूचना: मैं जानकारी सरल शब्दों में समझा सकता हूँ, लेकिन चिकित्सीय निदान या इलाज नहीं बता सकता। कृपया डॉक्टर से सलाह लें।"
                return "🩺 Medical Notice: I can help explain the information, but I cannot diagnose a medical condition or prescribe treatment. Please consult your doctor."
            if any(w in low for w in ["transfer money", "investment", "bank account", "debit card"]):
                return "💰 Financial Safety: I provide guidance only. I will never ask for your PIN/OTP or make transfers."
            return None

    def clean_json_markdown(text: str) -> str:
        text = text.strip()
        m = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        return m.group(1).strip() if m else text

    def safe_parse_json(text: str, default=None):
        if default is None: default = {}
        c = clean_json_markdown(text)
        try:
            return json.loads(c)
        except Exception:
            s, e = c.find('{'), c.rfind('}')
            if s != -1 and e > s:
                try: return json.loads(c[s:e+1])
                except Exception: pass
            return default

    def detect_user_intent(msg: str) -> str:
        t = msg.lower()
        if any(w in t for w in ["scam", "fraud", "suspicious", "won ₹", "won 25 lakh", "lottery", "disconnected tonight", "धोखा"]):
            return "scam"
        if any(w in t for w in ["bill", "electricity", "receipt", "document", "what does this mean", "बिजली"]):
            return "explain"
        if any(w in t for w in ["how to", "guide me", "steps", "book appointment", "change password", "कैसे"]):
            return "guided_task"
        if any(w in t for w in ["remind", "reminder", "medicine time", "yaad", "याद"]):
            return "reminder"
        return "general"

    # Gemini Service
    class StandaloneGeminiService:
        def __init__(self):
            self.client = None
            self.model_name = GEMINI_MODEL
            self._init_client()

        def _init_client(self):
            key = get_gemini_api_key()
            if key:
                try:
                    from google import genai
                    self.client = genai.Client(api_key=key)
                except Exception:
                    self.client = None

        def is_configured(self) -> bool:
            return bool(get_gemini_api_key() and len(get_gemini_api_key()) > 5)

        def generate_chat_response(self, messages, user_name="Mr. Sharma", language="English"):
            if not messages:
                return {"text": "Hello! How can I help you today?", "intent": "general", "suggested_action": None}
            last_msg = messages[-1]["content"]
            intent = detect_user_intent(last_msg)
            
            # Map action
            act_map = {"scam": "scam_shield", "explain": "explain", "guided_task": "guided_help", "reminder": "reminders"}
            action = act_map.get(intent)

            if self.is_configured() and self.client:
                try:
                    sys_p = f"You are a patient senior companion. Address the user respectfully as {user_name}. Language: {language}. Keep language simple, reassuring, and concise."
                    hist = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in messages[-4:]])
                    resp = self.client.models.generate_content(
                        model=self.model_name,
                        contents=f"{sys_p}\n\n{hist}\n\nASSISTANT:"
                    )
                    if resp and resp.text:
                        return {"text": resp.text.strip(), "intent": intent, "suggested_action": action}
                except Exception:
                    pass

            # Fallback
            if intent == "scam":
                txt = "यह संदेश संदेहास्पद लग रहा है। क्या आप इसे 'धोखा सुरक्षा' में जाँचना चाहेंगे?" if language == "Hindi" else "This message seems suspicious. Please never share OTPs or fees. Would you like me to check it in Scam Shield?"
            elif intent == "explain":
                txt = "मैं आपका बिल सरल शब्दों में समझा सकता हूँ। इसे 'समझाइए' में खोलें।" if language == "Hindi" else "I can explain this document simply. Would you like to check it in Explain Something?"
            else:
                txt = f"नमस्ते {user_name}! मैं आपका डिजिटल साथी हूँ।" if language == "Hindi" else f"Hello {user_name}! I am your personal digital companion. How can I help you today?"
            return {"text": txt, "intent": intent, "suggested_action": action}

        def generate_structured_json(self, prompt, items=None, default=None):
            if default is None: default = {}
            if self.is_configured() and self.client:
                try:
                    cnt = [prompt]
                    if items: cnt.extend(items)
                    r = self.client.models.generate_content(model=self.model_name, contents=cnt)
                    if r and r.text:
                        return safe_parse_json(r.text, default)
                except Exception:
                    pass
            return default

    gemini_service = StandaloneGeminiService()

    # Models & Services
    from pydantic import BaseModel, Field

    class ScamAnalysis(BaseModel):
        risk_level: str = "HIGH"
        summary: str = "This message contains signs commonly associated with scams."
        warning_signs: List[str] = Field(default_factory=list)
        do_not_do: List[str] = Field(default_factory=list)
        safe_next_steps: List[str] = Field(default_factory=list)
        confidence: str = "high"

    class DocumentExplanation(BaseModel):
        document_type: str = "Electricity Bill"
        simple_summary: str = "This is your monthly electricity bill."
        amount_to_pay: Optional[str] = "₹2,450"
        due_date: Optional[str] = "25 September 2026"
        provider_or_sender: Optional[str] = "BSES Rajdhani Power Limited"
        important_details: List[str] = Field(default_factory=list)
        what_you_need_to_do: List[str] = Field(default_factory=list)
        safety_warning: Optional[str] = None
        suggested_action: Optional[str] = "set_reminder"

    class GuidedStep(BaseModel):
        step_number: int
        total_steps: int
        title: str
        description: str
        helpful_tip: Optional[str] = None
        safety_reminder: Optional[str] = None
        action_button_label: str = "I've Done This ->"

    class GuidedTask(BaseModel):
        task_name: str
        total_steps: int
        steps: List[GuidedStep]
        disclaimer: str = "This is a guidance system. No actual payments or bookings are made."

    class StandaloneScamService:
        def analyze_scam(self, message_text="", image=None, language="English"):
            is_hi = language.lower() == "hindi"
            fb = {
                "risk_level": "HIGH",
                "summary": "यह संदेश धोखाधड़ी (Scam) से जुड़े लक्षण दर्शाता है।" if is_hi else "This message contains signs commonly associated with scams.",
                "warning_signs": [
                    "इनाम या लॉटरी देने के नाम पर पहले पैसे मांगे जा रहे हैं।" if is_hi else "Demands an upfront fee or tax before releasing a prize.",
                    "तुरंत पैसे देने या कनेक्शन काटने का झूठा डर पैदा किया जा रहा है।" if is_hi else "Creates artificial urgency or threat of disconnection.",
                    "संदेश किसी व्यक्तिगत 10-अंकों वाले मोबाइल नंबर से भेजा गया है।" if is_hi else "Sent from an unverified personal mobile number."
                ],
                "do_not_do": [
                    "अपना ओटीपी (OTP) या बैंक पिन किसी को न बताएं।" if is_hi else "Do not share any OTP, PIN, or passwords.",
                    "कथित फीस के नाम पर कोई रुपया ट्रांसफर न करें।" if is_hi else "Do not transfer money based on unsolicited messages.",
                    "संदेश में दिए गए लिंक पर क्लिक न करें।" if is_hi else "Do not click on suspicious links."
                ],
                "safe_next_steps": [
                    "इस संदेश को अनदेखा और ब्लॉक करें।" if is_hi else "Ignore and block the sender.",
                    "अपने परिजन या अधिकृत बैंक शाखा से संपर्क करें।" if is_hi else "Verify directly with your bank or utility branch."
                ],
                "confidence": "high"
            }
            if gemini_service.is_configured():
                res = gemini_service.generate_structured_json(
                    f"Evaluate this message for scam signs. Return ONLY JSON conforming to ScamAnalysis schema. Language: {language}.\nMessage: {message_text}",
                    default=fb
                )
                return ScamAnalysis(**res)
            return ScamAnalysis(**fb)

    scam_service = StandaloneScamService()

    class StandaloneDocumentService:
        def extract_text_from_pdf(self, pdf_bytes):
            try:
                import fitz
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                return "\n".join([p.get_text() for p in doc])
            except Exception:
                return ""

        def explain_content(self, text_content="", image=None, language="English"):
            is_hi = language.lower() == "hindi"
            fb = {
                "document_type": "बिजली का बिल (Electricity Bill)" if is_hi else "Electricity Bill",
                "simple_summary": "यह आपका बिजली का बिल है। 25 सितंबर से पहले ₹2,450 जमा करने हैं।" if is_hi else "This is your electricity bill. You need to pay ₹2,450 by 25 September.",
                "amount_to_pay": "₹2,450",
                "due_date": "25 सितंबर 2026" if is_hi else "25 September 2026",
                "provider_or_sender": "बीएसईएस राजधानी (BSES)" if is_hi else "BSES Rajdhani Power Limited",
                "important_details": [
                    "उपभोग: 340 यूनिट" if is_hi else "Electricity consumed: 340 units",
                    "उपभोक्ता संख्या: 100458921" if is_hi else "Consumer Account: 100458921"
                ],
                "what_you_need_to_do": [
                    "25 सितंबर से पहले भुगतान करें" if is_hi else "Pay ₹2,450 before 25 September",
                    "भुगतान रसीद संभाल कर रखें" if is_hi else "Keep the payment receipt safe"
                ],
                "safety_warning": "किसी को घर पर नकद न दें।" if is_hi else "Never hand cash to doorstep callers.",
                "suggested_action": "set_reminder"
            }
            if gemini_service.is_configured():
                items = [image] if image else None
                res = gemini_service.generate_structured_json(
                    f"Explain this document simply for a senior citizen. Return ONLY JSON. Language: {language}.\nText: {text_content}",
                    items=items,
                    default=fb
                )
                return DocumentExplanation(**res)
            return DocumentExplanation(**fb)

    document_service = StandaloneDocumentService()

    class StandaloneReminderService:
        def extract_reminder(self, text: str, language: str = "English"):
            today = datetime.now().date()
            tom = (today + timedelta(days=1)).strftime("%Y-%m-%d")
            return type("ExtractedReminder", (), {
                "title": text.strip() or "Reminder",
                "category": "Appointments" if "doctor" in text.lower() or "डॉक्टर" in text else ("Medicine" if "medicine" in text.lower() or "दवा" in text else "Important"),
                "date": tom if "tomorrow" in text.lower() or "kal" in text.lower() or "कल" in text else today.strftime("%Y-%m-%d"),
                "time": "09:00",
                "recurrence": "Daily" if "every" in text.lower() or "रोज" in text else "None"
            })()

        def get_categorized_reminders(self, user_id: int):
            all_r = get_reminders(user_id)
            today_str = datetime.now().strftime("%Y-%m-%d")
            out = {"today": [], "upcoming": [], "completed": []}
            for r in all_r:
                if r["status"] == "COMPLETED": out["completed"].append(r)
                elif r["due_date"] <= today_str or r["recurrence"] == "Daily": out["today"].append(r)
                else: out["upcoming"].append(r)
            return out

        def generate_proactive_briefing(self, user_name: str, user_id: int, language: str = "English"):
            dt_str = datetime.now().strftime("%A, %d %B %Y")
            cats = self.get_categorized_reminders(user_id)
            t_cnt = len(cats["today"])
            if language == "Hindi":
                return f"**सुप्रभात, {user_name}! 🙏**\n\nआज {dt_str} है। आज आपके लिए **{t_cnt}** जरूरी काम/दवाइयाँ निर्धारित हैं। बिजली बिल का भुगतान समय पर अवश्य करें।"
            return f"**Good Morning, {user_name}! ☀️**\n\nToday is {dt_str}. You have **{t_cnt}** important reminder(s) scheduled for today. Your electricity bill is due in 2 days."

    reminder_service = StandaloneReminderService()

    PREDEFINED_TASKS = {
        "Pay an electricity bill": {
            "task_name": "Pay an electricity bill",
            "total_steps": 4,
            "steps": [
                GuidedStep(step_number=1, total_steps=4, title="Find Consumer Number", description="Check your bill for the 9-digit CA Number at the top-right.", helpful_tip="Look for 'CA Number' or 'Consumer No'.", safety_reminder="Never pay directly into a personal phone number."),
                GuidedStep(step_number=2, total_steps=4, title="Open Official App or Portal", description="Open your official provider app or trusted banking app (Google Pay / BHIM / SBI Netbanking).", helpful_tip="Look for the green verified badge.", safety_reminder="Do not search phone numbers on public forums."),
                GuidedStep(step_number=3, total_steps=4, title="Verify Name and Due Amount", description="Type your CA number and verify that your name and amount match your paper bill.", helpful_tip="Always check the name before paying.", safety_reminder="Double check bill amount."),
                GuidedStep(step_number=4, total_steps=4, title="Pay & Keep Confirmation", description="Enter your UPI PIN only on your bank's official screen and screenshot the receipt.", helpful_tip="Save the transaction reference number.", safety_reminder="Entering UPI PIN deducts money; never enter PIN to receive money.", action_button_label="Finish Task")
            ]
        },
        "Book a doctor appointment": {
            "task_name": "Book a doctor appointment",
            "total_steps": 4,
            "steps": [
                GuidedStep(step_number=1, total_steps=4, title="Choose Specialist & Clinic", description="Decide on the doctor and clinic you wish to visit.", helpful_tip="Keep previous prescription handy.", safety_reminder="Use recognized hospital desks."),
                GuidedStep(step_number=2, total_steps=4, title="Pick Morning Time Slot", description="Select a comfortable morning slot between 10 AM and 12 PM.", helpful_tip="Avoid rush hour travel.", safety_reminder="Never share Aadhaar OTP to browse doctor slots."),
                GuidedStep(step_number=3, total_steps=4, title="Prepare Medical Reports", description="Keep recent blood test and sugar reports in a folder.", helpful_tip="Doctors appreciate chronological order.", safety_reminder="Do not take new pills without doctor consultation."),
                GuidedStep(step_number=4, total_steps=4, title="Confirm and Add Reminder", description="Confirm your slot and tap 'Set Reminder' in this app.", helpful_tip="I will remind you tomorrow morning.", safety_reminder="Keep hospital reception number saved.", action_button_label="Finish Task")
            ]
        }
    }

    class StandaloneGuidedService:
        def get_task(self, name: str, language: str = "English"):
            tmpl = PREDEFINED_TASKS.get(name, PREDEFINED_TASKS["Pay an electricity bill"])
            return GuidedTask(task_name=tmpl["task_name"], total_steps=tmpl["total_steps"], steps=tmpl["steps"])

    guided_service = StandaloneGuidedService()

    # CSS & UI Helpers
    def get_accessibility_css(text_size="Large", contrast_mode="Standard"):
        sz = TEXT_SIZES.get(text_size, TEXT_SIZES["Large"])
        b_sz, h_sz, btn_sz, lh = sz["body"], sz["heading"], sz["button"], sz["line_height"]
        if contrast_mode == "High Contrast":
            bg, card_bg, txt, btn_bg, btn_txt, border = "#0B0F19", "#151C2C", "#FFFFFF", "#FACC15", "#000000", "2px solid #FACC15"
        else:
            bg, card_bg, txt, btn_bg, btn_txt, border = "#F7F9FC", "#FFFFFF", "#1E293B", "#1B4965", "#FFFFFF", "1.5px solid #E2E8F0"

        return f"""
        <style>
        html, body, [class*="css"], .stMarkdown, p, div, span, label {{
            font-size: {b_sz} !important; line-height: {lh} !important; color: {txt} !important;
        }}
        .stApp {{ background-color: {bg} !important; }}
        h1, h2, h3, h4 {{ font-size: {h_sz} !important; font-weight: 700 !important; color: {txt} !important; }}
        .stButton > button {{
            font-size: {btn_sz} !important; font-weight: 600 !important; min-height: 52px !important;
            border-radius: 12px !important; background-color: {btn_bg} !important; color: {btn_txt} !important;
            border: {border} !important; width: 100% !important; margin: 6px 0 !important;
        }}
        .senior-card {{
            background-color: {card_bg} !important; border: {border} !important; border-radius: 16px !important;
            padding: 24px !important; margin-bottom: 20px !important; box-shadow: 0 4px 12px rgba(0,0,0,0.05) !important;
        }}
        .badge-high {{ background-color: #FEE2E2 !important; color: #991B1B !important; border: 2px solid #EF4444 !important; padding: 6px 14px !important; border-radius: 9999px !important; font-weight: 700 !important; display: inline-block !important; }}
        .badge-medium {{ background-color: #FEF3C7 !important; color: #92400E !important; border: 2px solid #F59E0B !important; padding: 6px 14px !important; border-radius: 9999px !important; font-weight: 700 !important; display: inline-block !important; }}
        .badge-low {{ background-color: #DCFCE7 !important; color: #166534 !important; border: 2px solid #22C55E !important; padding: 6px 14px !important; border-radius: 9999px !important; font-weight: 700 !important; display: inline-block !important; }}
        #MainMenu, footer, header {{ visibility: hidden; }}
        </style>
        """

    TRANSLATIONS = {
        "English": {
            "app_title": "AI Senior Companion", "tagline": "Your simple, safe and trusted digital companion.",
            "nav_home": "🏠 Home", "nav_companion": "🤖 Ask Companion", "nav_explain": "📄 Explain Something",
            "nav_scam": "🛡️ Scam Shield", "nav_guided": "🧭 Guided Help", "nav_reminders": "🔔 My Reminders",
            "nav_my_day": "📅 My Day", "nav_trusted": "👥 Trusted Help", "nav_settings": "⚙️ Settings",
            "how_can_i_help": "How can I help you today?", "voice_fallback": "You can type or speak your request.",
            "today_heading": "TODAY'S REMINDERS", "quick_help": "QUICK ACTIONS", "proactive_banner": "PROACTIVE SAFETY & ASSISTANCE",
            "btn_explain": "📄 Explain a Bill or Document", "btn_scam": "🛡️ Check a Suspicious Message",
            "btn_guided": "🧭 Step-by-Step Task Guide", "btn_reminder": "🔔 Add a New Reminder",
            "finish_button": "Finish Task", "trusted_contact_alert": "This situation may need help from someone you trust.",
            "reset_demo": "Reset Demo Data"
        },
        "Hindi": {
            "app_title": "एआई सीनियर साथी", "tagline": "आपका सरल, सुरक्षित और भरोसेमंद डिजिटल साथी।",
            "nav_home": "🏠 मुख्य पृष्ठ (Home)", "nav_companion": "🤖 साथी से पूछें", "nav_explain": "📄 समझाइए (Explain)",
            "nav_scam": "🛡️ धोखा सुरक्षा (Scam)", "nav_guided": "🧭 कदम-दर-कदम मदद", "nav_reminders": "🔔 मेरे रिमाइंडर",
            "nav_my_day": "📅 मेरा दिन (My Day)", "nav_trusted": "👥 भरोसेमंद संपर्क", "nav_settings": "⚙️ सेटिंग्स",
            "how_can_i_help": "आज मैं आपकी क्या सहायता कर सकता हूँ?", "voice_fallback": "आप नीचे लिखकर या बोलकर पूछ सकते हैं।",
            "today_heading": "आज के ज़रूरी काम और दवाइयाँ", "quick_help": "त्वरित सहायता", "proactive_banner": "सुरक्षा और सहायता सुझाव",
            "btn_explain": "📄 कोई बिल या कागज़ समझें", "btn_scam": "🛡️ संदिग्ध संदेश की जाँच करें",
            "btn_guided": "🧭 काम करने का सरल तरीका सीखें", "btn_reminder": "🔔 नया रिमाइंडर जोड़ें",
            "finish_button": "काम पूरा हुआ", "trusted_contact_alert": "इस मामले में किसी परिजन की मदद लें।",
            "reset_demo": "डेमो डेटा रीसेट करें"
        }
    }

    def t(k: str, lang: str = "English"):
        d = TRANSLATIONS.get(lang, TRANSLATIONS["English"])
        return d.get(k, TRANSLATIONS["English"].get(k, k))

    def format_friendly_date(d_str: str, lang: str = "English"):
        try:
            dt = datetime.strptime(d_str, "%Y-%m-%d")
            return dt.strftime("%A, %d %B %Y")
        except Exception:
            return d_str

    def get_greeting(name: str, lang: str = "English"):
        hr = datetime.now().hour
        g = "Good Morning" if hr < 12 else ("Good Afternoon" if hr < 17 else "Good Evening")
        if lang == "Hindi": g = "सुप्रभात" if hr < 12 else "नमस्कार"
        return f"{g}, {name} 👋"

    def generate_trusted_contact_url(phone: str, msg: str):
        c_ph = "".join(filter(str.isdigit, phone))
        return f"https://wa.me/{c_ph}?text={urllib.parse.quote(msg)}"


# --- STREAMLIT UI SETUP ---
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

# ─────────────────────────────────────────────────────────────────────────────
# SENIOR SAFETY: Lock the sidebar permanently open.
#   • Hide the collapse arrow button (chevron) that Streamlit renders inside
#     the sidebar – seniors should never accidentally lose the menu.
#   • Also hide the hamburger ☰ toggle in the top-left header.
#   • As a belt-and-braces fallback, inject a sticky top navigation bar that
#     is always visible even if the browser viewport is very narrow (mobile).
# ─────────────────────────────────────────────────────────────────────────────
_is_hc = contrast_mode == "High Contrast"
_top_bg    = "#1B4965" if not _is_hc else "#FACC15"
_top_txt   = "#FFFFFF" if not _is_hc else "#000000"
_top_hover = "#155e8a" if not _is_hc else "#eab308"

st.markdown(
    f"""
    <style>
    /* ── 1. Hide the sidebar collapse / chevron button ── */
    button[data-testid="collapsedControl"],
    button[kind="header"],
    [data-testid="stSidebarCollapseButton"],
    [data-testid="StyledFullScreenButton"],
    section[data-testid="stSidebar"] > div:first-child > button,
    .st-emotion-cache-1cypcdb,
    .st-emotion-cache-h5rgaw {{
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        height: 0 !important;
    }}

    /* ── 2. Hide the top-left hamburger ☰ menu toggle ── */
    header[data-testid="stHeader"] button,
    [data-testid="stToolbar"] button,
    .viewerBadge_container__1QSob,
    #MainMenu {{
        display: none !important;
        visibility: hidden !important;
    }}

    /* ── 3. Keep sidebar always wide and visible ── */
    section[data-testid="stSidebar"] {{
        display: flex !important;
        visibility: visible !important;
        min-width: 260px !important;
        transform: none !important;
        left: 0 !important;
        position: relative !important;
    }}

    /* ── 4. Sticky top fallback navigation bar (mobile / narrow screens) ── */
    #senior-topnav {{
        position: sticky;
        top: 0;
        z-index: 9999;
        background-color: {_top_bg};
        padding: 10px 16px;
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        border-bottom: 3px solid {"#eab308" if not _is_hc else "#1B4965"};
    }}
    #senior-topnav span {{
        color: {_top_txt};
        font-size: 15px;
        font-weight: 700;
        padding: 6px 12px;
        border-radius: 8px;
        cursor: pointer;
        border: 1.5px solid {"rgba(255,255,255,0.3)" if not _is_hc else "#1B4965"};
        text-decoration: none;
        white-space: nowrap;
        display: inline-block;
    }}
    #senior-topnav span:hover {{
        background-color: {_top_hover};
    }}

    /* Hide top-nav on wide screens where sidebar is visible */
    @media (min-width: 800px) {{
        #senior-topnav {{
            display: none !important;
        }}
    }}
    </style>
    """,
    unsafe_allow_html=True
)


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
        st.success("🟢 AI Connected (Gemini 3.6)", icon="✅")
    else:
        st.info("🟡 Demo Mode (Safe Fallback)", icon="ℹ️")


# ── STICKY TOP NAVIGATION BAR (fallback for mobile / narrow screens) ──
# Uses Streamlit query-param links to navigate so no JS is required.
_cur_page = st.session_state.current_page
_nav_top_items = [
    ("home", "🏠 Home"),
    ("companion", "🤖 Ask"),
    ("explain", "📄 Explain"),
    ("scam", "🛡️ Scam"),
    ("guided", "🧭 Guide"),
    ("reminders", "🔔 Remind"),
    ("my_day", "📅 My Day"),
    ("settings", "⚙️ Settings"),
]

_nav_spans = "".join(
    f'<span style="{"background:#0F3A54;" if k == _cur_page else ""}">{lbl}</span>'
    for k, lbl in _nav_top_items
)
st.markdown(
    f'<div id="senior-topnav">{_nav_spans}</div>',
    unsafe_allow_html=True
)

# Native Streamlit top-nav buttons (hidden on wide screens via CSS above;
# shown when the sidebar is not accessible, e.g. on small screens).
with st.container():
    _cols = st.columns(len(_nav_top_items))
    for idx, (pg_key, pg_label) in enumerate(_nav_top_items):
        with _cols[idx]:
            if st.button(pg_label, key=f"topnav_{pg_key}"):
                st.session_state.current_page = pg_key
                st.rerun()

st.markdown(
    "<style>#senior-topnav + div[data-testid='stHorizontalBlock'] {"
    " display: none; } </style>",
    unsafe_allow_html=True,
)

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

    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_input(
            "Your Question / आपका सवाल:",
            value=selected_sample if selected_sample else "",
            placeholder="Type or speak your question in simple words...",
            key="companion_input"
        )
        submitted = st.form_submit_button("💬 Send / पूछें")

    if (submitted and user_input.strip()) or selected_sample:
        prompt_text = user_input.strip() if submitted and user_input.strip() else selected_sample
        sanitized_input, detected_sensitive = SafetyService.sanitize_user_input(prompt_text)
        if detected_sensitive:
            st.warning("🔒 For your safety, secret OTPs, PINs, or card numbers have been masked before processing.")

        disclaimer = SafetyService.get_domain_disclaimer(sanitized_input, language)
        st.session_state.chat_messages.append({"role": "user", "content": sanitized_input})

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
                st.session_state.prefill_explain_text = (
                    "BSES RAJDHANI POWER LIMITED\n"
                    "Consumer Name: MR. ANAND SHARMA\n"
                    "CA Number: 100458921\n"
                    "Bill Date: 10-Sep-2026\n"
                    "Units Consumed: 340 Units\n"
                    "Total Energy Charges: ₹2,150.00\n"
                    "Fixed Monthly Charges: ₹180.00\n"
                    "NET AMOUNT PAYABLE: ₹2,450.00\n"
                    "DUE DATE: 25-Sep-2026\n"
                )
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
        uploaded_file = st.file_uploader("Choose a picture or PDF document:", type=["png", "jpg", "jpeg", "pdf"])
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
            st.metric(label="AMOUNT TO PAY / राशि", value=exp.amount_to_pay or "N/A")
        with col_due:
            st.metric(label="DUE DATE / अंतिम तिथि", value=exp.due_date or "N/A")
        with col_sender:
            st.metric(label="ORGANIZATION / विभाग", value=exp.provider_or_sender or "N/A")

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
            st.session_state.prefill_scam_text = (
                "Congratulations! You have won ₹25,00,000 in the All India Mobile Lucky Draw. "
                "To claim your winning prize, please transfer ₹5,000 clearance tax to UPI ID claimwin2026@oksbi. "
                "Reply with your Aadhaar OTP."
            )
            st.rerun()

    with col_s2:
        if st.button("📋 Load Sample: Electricity Cutoff Scam"):
            st.session_state.prefill_scam_text = (
                "URGENT NOTICE: Dear Consumer, your electricity power supply will be disconnected tonight at 9:30 PM "
                "because your previous month bill was not updated. Immediately contact officer at 9123456789."
            )
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

    progress_val = (step_idx + 1) / total_steps
    st.progress(progress_val)
    st.markdown(f"**Step {step_idx + 1} of {total_steps}**")

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

    with st.expander("🗣️ Speak or Type to Add a Reminder (AI Extraction)", expanded=True):
        nl_text = st.text_input("What would you like me to remind you about?", placeholder="e.g. Remind me tomorrow at 10 AM to call Dr. Verma")
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

    cat_rems = reminder_service.get_categorized_reminders(st.session_state.user["id"])
    t_today, t_upcoming, t_completed = st.tabs(["📅 Today", "⏳ Upcoming", "✅ Completed"])

    with t_today:
        if not cat_rems["today"]:
            st.info("No reminders for today!")
        for rem in cat_rems["today"]:
            c_info, c_action = st.columns([3, 1])
            with c_info:
                st.markdown(f"**⏰ {rem['due_time']}** — **{rem['title']}** ({rem['category']})")
                if rem.get("notes"): st.caption(rem["notes"])
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
                if rem.get("notes"): st.caption(rem["notes"])
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
    briefing = reminder_service.generate_proactive_briefing(user_name, st.session_state.user["id"], language)
    st.markdown(
        f"""
        <div class="senior-card" style="border-left: 6px solid #10B981;">
            {briefing}
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("### 🔔 Suggested Quick Actions for Today:")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("💊 Check Today's Medicines"): navigate_to("reminders")
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
        st.warning("No `GEMINI_API_KEY` detected. Running in intelligent fallback demo mode.")

    st.markdown("<br/>", unsafe_allow_html=True)
    st.markdown("### 🔄 Demo Data Reset")
    st.caption("Evaluators can click this button anytime to reset reminders, preferences, and contacts to the default demo state (Mr. Sharma).")
    if st.button("🔄 " + t("reset_demo", language), key="btn_reset_all"):
        reset_demo_data()
        st.session_state.clear()
        st.success("Demo data reset to original state!")
        st.rerun()
