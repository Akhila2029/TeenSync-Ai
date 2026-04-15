# 🧠 TeenSync – AI-Powered Mental Health Companion

TeenSync is a full-stack AI-powered mental health support platform designed to provide empathetic, context-aware conversations using **NLP, Retrieval-Augmented Generation (RAG), and crisis detection systems**.

It acts as a virtual companion ("Luna AI") that understands user emotions, retrieves relevant mental health knowledge, and responds safely and intelligently.

---

## 🚀 Features

* 💬 **AI Chatbot (Luna AI)**

  * Conversational assistant with empathetic responses
  * Context-aware replies using RAG

* 🧠 **Emotion & Sentiment Detection**

  * Detects user emotions (happy, sad, anxious, etc.)
  * Adapts responses accordingly

* 🚨 **Crisis Detection System**

  * Identifies high-risk inputs (e.g., self-harm signals)
  * Provides immediate support and helpline resources

* 📚 **RAG (Retrieval-Augmented Generation)**

  * Retrieves relevant mental health documents
  * Enhances response quality using FAISS + embeddings

* 🔐 **Authentication System**

  * User registration and login
  * Session-based access to chatbot

* 🌐 **Full-Stack Integration**

  * FastAPI backend
  * Frontend chat interface (React/HTML)
  * API-based communication

---

## 🏗️ Architecture

User Input → NLP Analysis → Crisis Detection → RAG Retrieval → LLM → Response

### Detailed Flow:

1. User sends message
2. NLP module detects:

   * Emotion
   * Sentiment
3. Crisis check:

   * If critical → immediate safe response
4. RAG pipeline:

   * Retrieve relevant documents (FAISS)
5. LLM generates response using:

   * Context + user input + emotion
6. Response returned to frontend

---

## 🧠 Tech Stack

### Backend:

* Python
* FastAPI
* FAISS (Vector Database)
* Sentence Transformers (Embeddings)
* OpenAI / Gemini API (optional)

### Frontend:

* HTML / CSS / JavaScript (or React)
* Fetch API / Axios

### AI Components:

* NLP (Sentiment + Emotion Detection)
* RAG Pipeline
* Crisis Detection Logic

---

## 📁 Project Structure

```
TeenSync/
│
├── app/
│   ├── services/
│   │   ├── chatbot_service.py
│   │   ├── nlp_service.py
│   │   ├── rag_service.py
│   │
│   ├── models/
│   │   ├── chat.py
│   │
│   ├── schemas/
│   │   ├── chat.py
│
├── data/
│   └── mental_health_docs/
│
├── frontend/
│   ├── LandingPage
│   ├── LoginPage
│   ├── RegisterPage
│   ├── ChatUI
│
├── main.py
└── README.md
```

---

## ⚙️ Installation & Setup

### 1. Clone the repository

```
git clone https://github.com/Akhila2029/TeenSync Ai.git
cd teensync
```

### 2. Create virtual environment

```
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```
pip install -r requirements.txt
```

### 4. Run backend server

```
uvicorn main:app --reload
```

Server runs at:
👉 http://localhost:8000

---

## 🧪 API Testing

Go to:
👉 http://localhost:8000/docs

Test `/chat` endpoint with:

```
{
  "message": "I feel anxious"
}
```

---

## 🔗 Frontend Setup

* Open frontend folder
* Run:

```
npm install
npm start
```

OR open HTML file directly

Ensure API calls point to:

```
http://localhost:8000/chat
```

---

## 🔐 Authentication Flow

* Landing Page → Login/Register
* On login:

  * User session stored
  * Redirect to chatbot dashboard
* Protected routes:

  * Chat accessible only after login

---

## 📊 Example API Response

```
{
  "response": "I understand you're feeling anxious. Try taking slow breaths...",
  "emotion": "anxious",
  "confidence": 0.92,
  "source_docs": ["breathing_exercises.txt"]
}
```

---

## 🧠 RAG Pipeline Details

* Documents stored in `/data/mental_health_docs`
* Embeddings generated using Sentence Transformers
* FAISS used for similarity search
* Top relevant documents injected into prompt

---

## 🚨 Safety & Ethics

* Crisis detection overrides AI generation
* No harmful or unsafe advice provided
* Encourages professional help when needed
* Designed with user well-being as priority

---

## 🔮 Future Enhancements

* 📱 Mobile app version
* 🗣️ Voice-based interaction
* 📊 Mood tracking dashboard
* 🧑‍⚕️ Therapist integration
* 🌍 Multi-language support
* 🧠 Memory-based personalized conversations

---

## 🎯 Use Cases

* Mental health support for students
* Stress and anxiety management
* AI-assisted emotional guidance
* Safe conversational companion

---

## 👩‍💻 Author

**Akhila Krishnan**
B.Tech CSE (AI & ML)
Aurora Higher Education and Research Academy

---

## ⭐ Contribution

Feel free to fork, contribute, and improve the project!

---

## 📌 Note

This project is for educational purposes and is not a replacement for professional mental health care.

---
