# AI Senior Companion 👴🤝🤖

> **"Your simple, safe and trusted digital companion."**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.64+-red.svg)](https://streamlit.io/)
[![Google GenAI](https://img.shields.io/badge/Google%20GenAI-Gemini%202.5-brightgreen.svg)](https://aistudio.google.com/)
[![Tests](https://img.shields.io/badge/Tests-21%20Passed-success.svg)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📌 30-Second Overview

- **Who is this for?** Senior citizens who feel overwhelmed, hesitant, or vulnerable navigating digital tasks, complex bills, and online communication.
- **What does it do?** It acts as a patient, calm, trustworthy helper that simplifies complex documents, detects fraudulent messages, guides users step-by-step through tasks, manages medication and bill reminders, and proactively assists without technical jargon.
- **Why is it different?** Unlike generic ChatGPT clones, AI Senior Companion features a **senior-first high-contrast UI**, **inter-connected workflows** (e.g. document analysis auto-triggers reminders and guided payment wizards), **pre-LLM OTP/credential safety shields**, and **instant bilingual support (English & Hindi)**.

```
                    ┌─────────────────────┐
                    │    Senior Citizen   │
                    └──────────┬──────────┘
                               │
                               ▼
                  ┌─────────────────────────┐
                  │   Streamlit Web App     │
                  │                         │
                  │  Senior-friendly UI     │
                  └────────────┬────────────┘
                               │
             ┌─────────────────┼─────────────────┐
             │                 │                 │
             ▼                 ▼                 ▼
       AI Companion      Scam Shield       Explain Anything
             │                 │                 │
             └─────────────────┼─────────────────┘
                               │
                               ▼
                    ┌────────────────────┐
                    │   Gemini AI Layer  │
                    │                    │
                    │ Understanding      │
                    │ Simplification     │
                    │ Classification     │
                    │ Structured Output   │
                    └──────────┬─────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
         Guided Help       Reminder DB       My Day
              │                │                │
              └────────────────┼────────────────┘
                               ▼
                     Proactive Assistance
```

---

## 💡 Core Experience: The Patient Companion Loop

```
UNDERSTAND ➔ SIMPLIFY ➔ PROTECT ➔ GUIDE ➔ REMIND ➔ FOLLOW UP
```

1. **Understand**: Natural language comprehension of colloquial senior queries in English, Hindi, and Hinglish.
2. **Simplify**: Transforms multi-page utility bills and legal notices into 3 essential facts: What is this, Amount to Pay, and Due Date.
3. **Protect**: Scam Shield identifies urgency tactics, lottery scams, and phishing attempts with calibrated probability and actionable safety steps.
4. **Guide**: Converts intimidating digital tasks (paying bills, changing passwords, booking appointments) into bite-sized sequential steps with checkpoints.
5. **Remind**: SQLite-backed scheduler parses speech or text like *"Remind me tomorrow at 10 AM to call Dr. Verma"*.
6. **Follow Up**: "My Day" summarizes daily medications, pending bills, and proactively nudges before deadlines.

---

## ✨ Features & Modules

| Module | Purpose | Senior-Centric Feature |
|---|---|---|
| **🏠 Home / Dashboard** | Central daily hub | Personalized greeting ("Good Morning, Mr. Sharma 👋"), proactive alerts, 4 large action cards. |
| **🤖 AI Companion** | Conversational helper | Warm, respectful persona. Discovers intent and suggests direct 1-click jumps to Scam Shield or Guided Help. |
| **📄 Explain Something** | Document & Bill AI | Upload image, PDF, or text. Extracts amounts, due dates, and offers 1-click **[Set Reminder]** & **[Guide Me]**. |
| **🛡️ Scam Shield** | Anti-fraud & Phishing check | Evaluates SMS/email/URL. Highlights red flags, lists what **NEVER** to do, and provides safe next actions. |
| **🧭 Guided Help** | Step-by-step task wizard | Bite-sized sequential steps with progress bar, patient tips, safety checkpoints, and "I've Done This ->" confirmation. |
| **🔔 My Reminders** | Intelligent scheduler | Natural language date/time parsing (English & Hindi). Categorized into Today, Upcoming, Completed. |
| **📅 My Day** | Proactive morning briefing | Synthesizes daily agenda, active medication schedules, and contextual recommendations. |
| **👥 Trusted Help** | Family caregiver safety net | Pre-drafts WhatsApp/SMS verification requests with 1-click to ask a family member before acting. |
| **⚙️ Accessibility** | Physical accommodation | Text sizing (Standard 18px, Large 22px, Extra Large 26px), High Contrast theme, and English/Hindi toggle. |

---

## 🛡️ AI Safety Architecture

1. **Zero Irreversible Execution**: AI Senior Companion is an **educational and guidance platform**. It never executes money transfers, submits medical bookings, or alters account credentials.
2. **Pre-LLM Credential Masking**: Passwords, 6-digit OTPs, and credit card patterns are masked by `SafetyService` *before* payloads reach external models.
3. **Medical & Financial Disclaimers**: Automatic detection of diagnosis or investment inquiries injects clear non-diagnostic reminders.
4. **Calibrated Uncertainty**: Phishing analyses avoid dangerous overconfidence by using calibrated phrasing: *"This message contains signs commonly associated with scams"*.

---

## 🏗️ System Architecture

```
ai-senior-companion/
│
├── app.py                      # Main Streamlit web application
├── requirements.txt            # Python dependencies
├── README.md                   # Complete documentation
├── .gitignore                  # Git hygiene rules
├── .env.example                # Template for environment variables
│
├── config/
│   └── settings.py             # Settings, paths, and API key loader
│
├── services/
│   ├── gemini_service.py       # Official Google GenAI SDK wrapper & fallback
│   ├── document_service.py     # PDF & image document simplification
│   ├── scam_service.py         # Multi-factor fraud & phishing analyzer
│   ├── reminder_service.py     # NLP reminder extraction & briefing engine
│   ├── guided_service.py       # Sequential task breakdown service
│   └── safety_service.py       # PII/OTP redactor & safety disclaimers
│
├── models/
│   ├── user.py                 # Pydantic models for User & Preferences
│   ├── reminder.py             # Pydantic models for Reminders
│   └── analysis.py             # Pydantic models for Scam & Document analysis
│
├── database/
│   ├── database.py             # SQLite thread-safe CRUD & demo seeder
│   └── schema.py               # Table DDL schemas
│
├── prompts/
│   ├── system_prompt.py        # Central companion persona
│   ├── explain_prompt.py       # Document extraction prompt
│   ├── scam_prompt.py          # Anti-fraud structured prompt
│   ├── guided_task_prompt.py   # Step-by-step task breakdown prompt
│   └── daily_companion_prompt.py # NLP reminder & morning briefing prompt
│
├── utils/
│   ├── accessibility.py        # Dynamic CSS generator (sizing & contrast)
│   ├── helpers.py              # Localization (EN/HI) & WhatsApp links
│   ├── validators.py           # JSON cleanup & intent detection
│   └── generate_assets.py      # Synthetic bill image generator
│
├── assets/
│   ├── sample_bills/           # Sample electricity bill (text & image)
│   └── sample_scams/           # Sample lottery & utility cutoff scams
│
├── docs/
│   └── ai-testing.md           # Prompt engineering log & testing history
│
├── tests/
│   └── test_companion.py       # Pytest suite (21 tests)
│
└── .streamlit/
    └── config.toml             # Streamlit visual theme
```

---

## 🚀 Quickstart: Local Setup

### 1. Clone Repository & Enter Directory
```bash
git clone https://github.com/your-username/ai-senior-companion.git
cd ai-senior-companion
```

### 2. Create and Activate Virtual Environment
```bash
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Gemini API Key
Create a `.env` file in the root directory (or copy from `.env.example`):
```bash
cp .env.example .env
```
Add your Google Gemini API key obtained from [Google AI Studio](https://aistudio.google.com/):
```env
GEMINI_API_KEY=AIzaSyYourActualGeminiApiKeyHere
```
*(Note: If no API key is provided, the application automatically runs in **Intelligent Demo Mode** with realistic offline responses so you can still test every feature seamlessly!)*

### 5. Launch the Web Application
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 🧪 Running Automated Tests

Run the complete test suite with `pytest`:
```bash
python -m pytest tests/ -v
```
All 21 unit, integration, and prompt test cases will run against SQLite, models, Pydantic schemas, and safety guardrails:
```
tests/test_companion.py::test_database_initialization_and_seed PASSED
tests/test_companion.py::test_reminder_crud PASSED
tests/test_companion.py::test_user_preferences_update PASSED
tests/test_companion.py::test_gemini_service_offline_resilience PASSED
tests/test_companion.py::test_scam_lottery_high_risk PASSED
tests/test_companion.py::test_scam_electricity_disconnection_high_risk PASSED
tests/test_companion.py::test_scam_benign_message_low_risk PASSED
tests/test_companion.py::test_explain_electricity_bill PASSED
tests/test_companion.py::test_reminder_extraction_english PASSED
tests/test_companion.py::test_reminder_extraction_hindi PASSED
tests/test_companion.py::test_daily_medicine_reminder PASSED
tests/test_companion.py::test_guided_help_task_steps PASSED
tests/test_companion.py::test_guided_help_hindi PASSED
tests/test_companion.py::test_safety_otp_redaction PASSED
tests/test_companion.py::test_safety_medical_disclaimer PASSED
tests/test_companion.py::test_safety_financial_disclaimer PASSED
tests/test_companion.py::test_accessibility_css_scaling PASSED
tests/test_companion.py::test_localization_dictionary PASSED
tests/test_companion.py::test_json_cleaners_and_intent PASSED
tests/test_companion.py::test_empty_and_invalid_inputs PASSED
tests/test_companion.py::test_database_reset_and_integrity PASSED
============================= 21 passed in 5.15s ==============================
```

---

## 🎬 How to Demonstrate the Application (Evaluator Walkthrough)

Follow this 12-step sequence to experience the full connected workflow:

1. **Open Home Dashboard**: Notice the warm greeting (*"Good Morning, Mr. Sharma 👋"*), proactive electricity bill notice, and 4 large action cards.
2. **Ask Companion a Question**:
   - In the sidebar or cards, click **🤖 Ask Companion**.
   - Click the prompt chip: *"I received a strange bank message about winning a lottery."*
   - Watch the Companion detect fraud intent, offer safety advice, and display a blue button: **[🛡️ Open Scam Shield to Verify]**.
3. **One-Click Jump to Scam Shield**:
   - Click the button to seamlessly transition to **Scam Shield**.
   - Notice the text is pre-filled. Click **[🛡️ Check This for Scams]**.
   - Observe the **HIGH RISK** badge, warning signs, **WHAT YOU SHOULD NEVER DO** box, and the **[📱 WhatsApp Aarav to Verify]** button.
4. **Explain a Bill (Explain Something)**:
   - Click **📄 Explain Something** in the navigation.
   - Click **[📋 Load Sample Electricity Bill]** (or upload `assets/sample_bills/sample_electricity_bill.png`).
   - Click **[🔍 Explain This to Me Simply]**.
   - See the extracted **Amount to Pay (₹2,450)** and **Due Date (25 September 2026)** in large, clear metric cards.
5. **Convert Document to Reminder**:
   - Under the bill explanation, click **[🔔 Set Reminder for this Due Date]**.
   - The app automatically creates a reminder in SQLite and confirms it on screen.
6. **Trigger Guided Help**:
   - Click **[🧭 Guide Me Step-by-Step to Pay This]**.
   - The app routes to **🧭 Guided Help**, starting Step 1 of 4 with a consumer number locator, patient tips, and safety warnings. Step through using **[✅ I've Done This ->]**.
7. **Create a Natural Language Reminder**:
   - Go to **🔔 My Reminders**.
   - Type or speak: *"Remind me tomorrow at 10 AM to call my doctor"*.
   - Click **[➕ Parse & Add Reminder]**; notice the automatic calculation of tomorrow's date and assignment to *Appointments*.
8. **Check Proactive Briefing**:
   - Navigate to **📅 My Day**.
   - View the AI-generated morning briefing incorporating today's medicines and the upcoming electricity bill.
9. **Verify Trusted Contact**:
   - Click **👥 Trusted Help**.
   - View preconfigured son (*Aarav Sharma*). Click **[📲 Send Help Message]** to see the pre-drafted WhatsApp/SMS link.
10. **Test Accessibility Scaling**:
    - Go to **⚙️ Settings**.
    - Change Text Size to **Extra Large** and Theme to **High Contrast**.
    - Notice the immediate dynamic restyling with high-visibility borders and large typography.
11. **Test Multilingual Support**:
    - In the sidebar, toggle language from **English** to **Hindi**.
    - Observe headers, navigation, greetings, and prompts adapting to respectful, natural Hindi (*"सुप्रभात", "साथी से पूछें", "धोखा सुरक्षा"*).
12. **Reset Demo Data**:
    - In **⚙️ Settings**, click **[🔄 Reset Demo Data]** to return the database to its initial state.

---

## ☁️ Public Deployment to Streamlit Community Cloud

1. **Push to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial release of AI Senior Companion"
   git branch -M main
   git remote add origin https://github.com/your-username/ai-senior-companion.git
   git push -u origin main
   ```
2. **Deploy on Streamlit**:
   - Sign in to [share.streamlit.io](https://share.streamlit.io/).
   - Click **"New app"**.
   - Select your repository, branch (`main`), and set Main file path to `app.py`.
3. **Configure Secrets**:
   - In App Settings under **"Secrets"**, add:
     ```toml
     GEMINI_API_KEY = "your_actual_gemini_api_key"
     ```
   - Click **Deploy**!

---

## 🛣️ Future Enhancements

- **Voice Synthesis (TTS)**: Direct text-to-speech playback so seniors with visual impairment can listen to every explanation.
- **Dialectal Hindi & Regional Indian Languages**: Expand from Hindi to Tamil, Telugu, Bengali, Marathi, and Gujarati.
- **Wearable Health Sync**: Bluetooth integration with blood pressure monitors and glucometers to automatically populate health journals.
- **Offline Edge Models**: On-device lightweight models for offline emergency safety checks without internet connectivity.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
