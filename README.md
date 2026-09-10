# Pranav — Government Scheme & Finance Navigator

Updated SIH prototype with a myScheme/Stand-Up India-inspired government-service UI (original implementation), stronger server-side authentication, richer eligibility profiling, explainable scheme ranking, expanded scheme catalogue, official-source links, scheme videos, and optional nearby partner mapping.

## Run

### Backend
```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend
Serve `frontend/` with a static server on port 8080, e.g.:
```bash
python -m http.server 8080 --directory frontend
```

## Authentication
- Signup/login endpoints are server-side.
- Passwords use PBKDF2-HMAC-SHA256 with a per-user salt.
- Sessions use random bearer tokens with expiry.
- No passwords are stored in localStorage.
- For production, replace the in-memory session store with a durable session/identity provider and add HTTPS, rate limiting, email/phone verification, MFA, CSRF protection, audit logging and secure cookie/session handling.

## Nearby map
The Partners page uses browser geolocation only after the user clicks **Use my current location**. Nearby points are queried through the backend from OpenStreetMap/Overpass. Do not use precise location data without user consent.

## Data and recommendation disclaimer
Scheme data is for discovery and prototype analysis. The official scheme portal/guideline and authorized lender remain the final authority. A displayed maximum is not a promise of sanction. The recommendation score is explainable but not a credit score.

## Live AI + Open Government Data

Pranav AI now uses the OpenAI Responses API with web search enabled. The assistant is instructed to research current information for substantive scheme questions and prioritize official sources such as myScheme, data.gov.in, Ministry/Department portals, PIB, official scheme portals, and official bank websites.

The project is also **data.gov.in-ready**. The Open Government Data Platform India exposes APIs and machine-readable datasets under the Government Open Data License - India. Add `DATA_GOV_API_KEY` if you later connect direct dataset endpoints for beneficiary statistics, geography, trends, or other contextual analysis.

Important: live web research improves freshness, but Pranav remains a discovery/advisory tool. It must not present an individual's eligibility or loan approval as guaranteed.
