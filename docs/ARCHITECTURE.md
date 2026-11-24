# 🏗️ AeroLife System Architecture & Engineering Specifications

This document outlines the software architecture, design patterns, and prompt engineering protocols implemented in AeroLife for the **Google PromptWars 2026** competition.

---

## 1. Architectural Patterns

### 1.1 Separation of Concerns (SoC)
- **Configuration Layer (`config.py`):** Centralizes all environmental thresholds (CPCB, WHO), caching policies (TTL), and external API endpoints.
- **Service Layer (`air_quality_service.py`):** Interfaces with real-time geospatial atmospheric sensors. Manages connection pooling, HTTP retries, and offline caching.
- **AI Engine Layer (`gemini_engine.py`):** Encapsulates prompt synthesis, schema validation (Pydantic), and fallback logic.
- **Presentation Layer (`app.py`):** Streamlit-based reactive UI applying WCAG 2.1 dark-mode design, Plotly indicators, and responsive tab layout.

### 1.2 Performance & Efficiency Architecture
- **In-Memory Caching (`@lru_cache`):** Memorizes AQI classifications and geospatial coordinate resolutions.
- **Application-Level Caching (`@st.cache_data`):** Caches atmospheric API responses and Gemini prompt outputs for 10 minutes (`TTL=600s`).
- **Connection Pooling (`urllib3.HTTPAdapter`):** Reuses TCP connections with automatic exponential backoff retry for network resilience.

---

## 2. Prompt Engineering Design

```
+-------------------------------------------------------+
|  User Context (City, Household Profile, Lifestyle)    |
+-------------------------------------------------------+
                           |
                           v
+-------------------------------------------------------+
|  Environmental Grounding (Live PM2.5, PM10, AQI Tier)  |
+-------------------------------------------------------+
                           |
                           v
+-------------------------------------------------------+
|  System Instruction (AeroLife Specialist Persona)     |
|  - WHO 2021 Air Quality Guidelines Grounding         |
|  - Thermal Inversion Scheduling Protocols             |
|  - Non-Medical Disclaimer Guardrail                   |
+-------------------------------------------------------+
                           |
                           v
+-------------------------------------------------------+
|  Output Constraint: response_mime_type="application/json"
|  Pydantic Validation: AirQualityAdvisoryResponse       |
+-------------------------------------------------------+
```

---

## 3. Security & Resilience Strategy

1. **Secret Isolation:** Environment secrets (`GEMINI_API_KEY`) are managed strictly through `.env` and `os.getenv()`.
2. **Zero-Crash Offline Engine:** When operating in restricted environments or during network drops, the application falls back seamlessly to deterministic benchmark data.
3. **Automated CI/CD:** GitHub Actions executes `pytest` test suites on every branch push, verifying code stability and prompt schema compliance.
