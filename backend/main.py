from __future__ import annotations

import math
import os
import re
import secrets
import sqlite3
import hashlib
import base64
import time
import httpx
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

app = FastAPI(
    title="Pranav Finance API — SIH Prototype",
    version="0.2.0",
    description="Pranav AI scheme discovery with live web research, open-government-data hooks, recommendation scoring, calculator, and partner routing.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:8080,http://127.0.0.1:8080").split(",")],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

SCHEMES = [
    {"id":"pmmy","name":"Pradhan Mantri MUDRA Yojana (PMMY)","type":"Business Loan","maximum_loan":2000000,"interest_rate":None,"income_limit":None,"moratorium":0,"tenure":84,"purposes":["micro","retail","services","dairy","handicraft"],"education":["not_applicable","school","graduate"],"states":["ALL"],"source_url":"https://www.myscheme.gov.in/schemes/pradhan-mantri-mudra-yojana","is_prototype_data":False},
    {"id":"pmegp","name":"Prime Minister's Employment Generation Programme (PMEGP)","type":"Business Loan + Subsidy","maximum_loan":5000000,"interest_rate":None,"income_limit":None,"moratorium":0,"tenure":84,"purposes":["micro","retail","services","dairy","handicraft"],"education":["not_applicable","school","graduate"],"states":["ALL"],"source_url":"https://www.kviconline.gov.in/pmegpeportal/dashboard/notification/Revised_PMEGP_Scheme_Guidelines_07122023_compressed.pdf","is_prototype_data":False},
    {"id":"svanidhi","name":"PM Street Vendor's AtmaNirbhar Nidhi (PM SVANidhi)","type":"Street Vendor Credit","maximum_loan":50000,"interest_rate":None,"income_limit":None,"moratorium":0,"tenure":36,"purposes":["retail","services","micro"],"education":["not_applicable","school","graduate"],"states":["ALL"],"source_url":"https://www.myscheme.gov.in/schemes/pm-svanidhi","is_prototype_data":False},
    {"id":"vishwakarma","name":"PM Vishwakarma","type":"Artisan Credit + Support","maximum_loan":300000,"interest_rate":5.0,"income_limit":None,"moratorium":18,"tenure":36,"purposes":["handicraft","services","micro"],"education":["not_applicable","school","graduate"],"states":["ALL"],"source_url":"https://www.myscheme.gov.in/schemes/pm-vishwakarma","is_prototype_data":False},
    {"id":"standup","name":"Stand-Up India","type":"Composite Bank Loan","maximum_loan":10000000,"interest_rate":None,"income_limit":None,"moratorium":18,"tenure":84,"purposes":["micro","retail","services"],"education":["not_applicable","school","graduate"],"states":["ALL"],"source_url":"https://www.standupmitra.in/","is_prototype_data":False},
    {"id":"pmfme","name":"PM Formalisation of Micro Food Processing Enterprises (PMFME)","type":"Food Processing Subsidy","maximum_loan":1000000,"interest_rate":None,"income_limit":None,"moratorium":0,"tenure":84,"purposes":["micro","retail","services"],"education":["not_applicable","school","graduate"],"states":["ALL"],"source_url":"https://pmfme.mofpi.gov.in/","is_prototype_data":False},
    {"id":"kcc","name":"Kisan Credit Card (KCC)","type":"Agriculture Credit","maximum_loan":300000,"interest_rate":None,"income_limit":None,"moratorium":0,"tenure":60,"purposes":["agriculture","dairy","micro"],"education":["not_applicable","school","graduate"],"states":["ALL"],"source_url":"https://www.myscheme.gov.in/","is_prototype_data":False},
    {"id":"pmayu2","name":"PMAY-U 2.0","type":"Housing Assistance","maximum_loan":2500000,"interest_rate":None,"income_limit":900000,"moratorium":0,"tenure":240,"purposes":["housing","micro"],"education":["not_applicable","school","graduate"],"states":["ALL"],"source_url":"https://pmay-urban.gov.in/","is_prototype_data":False},
    {"id":"pmmvy","name":"Pradhan Mantri Matru Vandana Yojana (PMMVY)","type":"Women & Child Benefit","maximum_loan":0,"interest_rate":0,"income_limit":None,"moratorium":0,"tenure":0,"purposes":["welfare"],"education":["not_applicable","school","graduate"],"states":["ALL"],"source_url":"https://www.myscheme.gov.in/","is_prototype_data":False},
    {"id":"nsnm","name":"Namo Shetkari Mahasanman Nidhi Yojana","type":"Farmer Benefit","maximum_loan":0,"interest_rate":0,"income_limit":None,"moratorium":0,"tenure":0,"purposes":["agriculture","welfare"],"education":["not_applicable","school","graduate"],"states":["Maharashtra"],"source_url":"https://www.myscheme.gov.in/schemes/namo-shetkari-mahasanman-nidhi-yojana","is_prototype_data":False}
]

PARTNERS = [
    {"id":"ubi","name":"Union Bank of India","type":"Public Sector Bank","distance_km":0,"address":"Official bank website / branch locator","phone":"1800 2333","supported_schemes":["pmmy","pmegp","svanidhi","vishwakarma","standup"],"operational":True,"fund_status":"Check official portal","npa_restriction":False,"latitude":18.52,"longitude":73.85,"source_url":"https://www.unionbankofindia.bank.in/","is_prototype_data":False},
    {"id":"bom","name":"Bank of Maharashtra","type":"Public Sector Bank","distance_km":0,"address":"Maharashtra-focused public sector bank","phone":"See official website","supported_schemes":["pmegp"],"operational":True,"fund_status":"Check official portal","npa_restriction":False,"latitude":18.52,"longitude":73.85,"source_url":"https://bankofmaharashtra.in/","is_prototype_data":False},
    {"id":"sbi","name":"State Bank of India","type":"Public Sector Bank","distance_km":0,"address":"Official bank website / branch locator","phone":"See official website","supported_schemes":["pmmy","pmegp","vishwakarma","standup","pmfme"],"operational":True,"fund_status":"Check official portal","npa_restriction":False,"latitude":18.52,"longitude":73.85,"source_url":"https://sbi.co.in/","is_prototype_data":False},
]


DB_PATH=os.getenv("PRANAV_DB", os.path.join(os.path.dirname(__file__), "pranav_auth.db"))
SESSIONS: dict[str, dict] = {}

def db():
    conn=sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, identifier TEXT UNIQUE NOT NULL, name TEXT NOT NULL, password_hash TEXT NOT NULL, created_at INTEGER NOT NULL)")
    conn.commit(); return conn

def hash_password(password:str)->str:
    salt=secrets.token_bytes(16); rounds=210000
    dk=hashlib.pbkdf2_hmac('sha256', password.encode(), salt, rounds)
    return f"pbkdf2_sha256${rounds}${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(dk).decode()}"

def verify_password(password:str, stored:str)->bool:
    try:
        _,rounds,salt,expected=stored.split('$'); dk=hashlib.pbkdf2_hmac('sha256',password.encode(),base64.urlsafe_b64decode(salt),int(rounds)); return secrets.compare_digest(base64.urlsafe_b64encode(dk).decode(),expected)
    except Exception: return False

def strong_password(p:str)->bool:
    return len(p)>=10 and bool(re.search(r'[A-Z]',p)) and bool(re.search(r'[a-z]',p)) and bool(re.search(r'\d',p)) and bool(re.search(r'[^A-Za-z0-9]',p))

class AuthIn(BaseModel):
    identifier:str=Field(min_length=5,max_length=120)
    password:str=Field(min_length=10,max_length=128)
    name:str|None=Field(default=None,max_length=120)
    confirm_password:str|None=None

@app.post('/auth/signup')
def auth_signup(inp:AuthIn):
    if not strong_password(inp.password): raise HTTPException(400,'Password must be 10+ characters and include uppercase, lowercase, number and symbol.')
    if inp.password != inp.confirm_password: raise HTTPException(400,'Passwords do not match.')
    name=(inp.name or '').strip()
    if len(name)<2: raise HTTPException(400,'Full name is required.')
    conn=db()
    try:
        cur=conn.execute('INSERT INTO users(identifier,name,password_hash,created_at) VALUES(?,?,?,?)',(inp.identifier.strip().lower(),name,hash_password(inp.password),int(time.time())))
        uid=cur.lastrowid; conn.commit()
    except sqlite3.IntegrityError: raise HTTPException(409,'An account with this email/mobile already exists.')
    finally: conn.close()
    token=secrets.token_urlsafe(32); SESSIONS[token]={'user_id':uid,'name':name,'expires':time.time()+86400}
    return {'token':token,'user':{'id':uid,'name':name,'identifier':inp.identifier.strip().lower()}}

@app.post('/auth/login')
def auth_login(inp:AuthIn):
    conn=db(); row=conn.execute('SELECT id,name,identifier,password_hash FROM users WHERE identifier=?',(inp.identifier.strip().lower(),)).fetchone(); conn.close()
    if not row or not verify_password(inp.password,row[3]): raise HTTPException(401,'Invalid credentials.')
    token=secrets.token_urlsafe(32); SESSIONS[token]={'user_id':row[0],'name':row[1],'expires':time.time()+86400}
    return {'token':token,'user':{'id':row[0],'name':row[1],'identifier':row[2]}}

@app.post('/auth/logout')
def auth_logout(authorization:str|None=Header(default=None)):
    token=(authorization or '').removeprefix('Bearer ').strip(); SESSIONS.pop(token,None); return {'ok':True}

@app.get('/auth/me')
def auth_me(authorization:str|None=Header(default=None)):
    token=(authorization or '').removeprefix('Bearer ').strip(); session=SESSIONS.get(token)
    if not session or session['expires']<time.time(): SESSIONS.pop(token,None); raise HTTPException(401,'Session expired.')
    return {'user':{'id':session['user_id'],'name':session['name']}}

class Beneficiary(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    gender: Literal["male","female","other"] = "other"
    marital_status: Literal["married","unmarried"] = "unmarried"
    social_category: str = "general"
    disability: Literal["yes","no"] = "no"
    residence: Literal["urban","rural"] = "urban"
    occupation: str = ""
    existing_loan: Literal["yes","no"] = "no"
    age: int = Field(ge=18, le=80)
    annual_family_income: float = Field(ge=0, le=10_000_000)
    purpose: Literal["business", "education"]
    project_type: str = Field(min_length=2, max_length=80)
    project_cost: float = Field(gt=0, le=100_000_000)
    required_loan_amount: float = Field(gt=0, le=100_000_000)
    education_status: str = Field(min_length=2, max_length=80)
    state: str = Field(min_length=2, max_length=80)
    district: str = Field(min_length=2, max_length=80)
    pincode: str
    preferred_language: Literal["en", "hi", "mr"] = "en"

    @field_validator("pincode")
    @classmethod
    def valid_pin(cls, value: str) -> str:
        if not re.fullmatch(r"[1-9][0-9]{5}", value):
            raise ValueError("pincode must be a valid 6-digit Indian PIN code")
        return value

class CalculatorIn(BaseModel):
    loan_amount: float = Field(gt=0, le=100_000_000)
    annual_interest_rate: float = Field(ge=0, le=40)
    tenure_months: int = Field(ge=1, le=360)
    moratorium_months: int = Field(ge=0, le=60)

class NLPIn(BaseModel):
    text: str = Field(min_length=2, max_length=1000)


def evaluate(user: Beneficiary, scheme: dict) -> dict:
    score = 100
    reasons: list[str] = []
    blockers: list[str] = []
    if scheme["income_limit"] is None or user.annual_family_income <= scheme["income_limit"]:
        reasons.append("Annual family income satisfies the prototype income condition.")
    else:
        score -= 40; blockers.append("Income exceeds the prototype scheme limit.")
    if user.required_loan_amount <= scheme["maximum_loan"]:
        reasons.append("Requested amount is within the prototype loan limit.")
    else:
        score -= 35; blockers.append("Requested amount exceeds the prototype scheme maximum.")
    if user.required_loan_amount <= user.project_cost * 1.1:
        reasons.append("Requested finance is proportionate to stated project cost.")
    else:
        score -= 10; blockers.append("Requested finance is high compared with project cost.")
    purpose_key = "education" if user.purpose == "education" else user.project_type
    if purpose_key in scheme["purposes"] or (user.purpose == "business" and "micro" in scheme["purposes"]):
        reasons.append("Project/purpose category is supported.")
    else:
        score -= 30; blockers.append("Purpose does not closely match the scheme profile.")
    if user.purpose != "education" or user.education_status in scheme["education"]:
        reasons.append("Education/profile information is consistent with this prototype rule set.")
    else:
        score -= 15; blockers.append("Education status requires further verification.")
    if "ALL" in scheme["states"] or user.state in scheme["states"]:
        reasons.append("Prototype location rule includes the selected state.")
    else:
        score -= 45; blockers.append("Selected state is outside the prototype scheme footprint.")
    score = max(8, min(99, score))
    hard_failures = sum(any(word in b.lower() for word in ("exceeds", "outside", "does not")) for b in blockers)
    status = "Not Eligible" if hard_failures >= 2 else "Eligible" if score >= 76 else "Possibly Eligible" if score >= 50 else "Not Eligible"
    return {**scheme, "match_score": score, "eligibility_status": status, "reasons": reasons, "cautions": blockers, "advisory_only": True}


def calculate(inp: CalculatorIn) -> dict:
    if inp.moratorium_months >= inp.tenure_months:
        raise HTTPException(422, "moratorium_months must be less than tenure_months")
    r = inp.annual_interest_rate / 12 / 100
    repay_months = inp.tenure_months - inp.moratorium_months
    moratorium_interest = inp.loan_amount * r * inp.moratorium_months
    financed = inp.loan_amount + moratorium_interest
    emi = financed / repay_months if r == 0 else financed * r * (1 + r) ** repay_months / ((1 + r) ** repay_months - 1)
    total = emi * repay_months
    return {
        "estimated_monthly_emi": round(emi, 2),
        "principal": inp.loan_amount,
        "estimated_total_interest": round(total - inp.loan_amount, 2),
        "estimated_total_repayment": round(total, 2),
        "repayment_months": repay_months,
        "moratorium_months": inp.moratorium_months,
        "estimated_moratorium_interest": round(moratorium_interest, 2),
        "disclaimer": "Estimate only; official scheme and authorized-partner terms prevail.",
    }


def route_partner(scheme_id: str) -> list[dict]:
    ranked = []
    for p in PARTNERS:
        compatible = scheme_id in p["supported_schemes"]
        currently_eligible = p["operational"] and not p["npa_restriction"] and p["fund_status"] not in {"Paused", "Temporarily paused"}
        routing_score = (60 if compatible else 0) + (30 if currently_eligible else 0) + max(0, 10 - p["distance_km"])
        if not p["operational"]: routing_score -= 45
        if p["npa_restriction"]: routing_score -= 18
        if not compatible: routing_score -= 35
        ranked.append({**p, "scheme_compatible": compatible, "currently_eligible": currently_eligible, "routing_score": round(routing_score, 1)})
    return sorted(ranked, key=lambda x: x["routing_score"], reverse=True)


def require_admin(authorization: str | None = Header(default=None)) -> None:
    # Prototype-only guard. Production design: OIDC/OAuth2 JWT verification + RBAC + short-lived tokens.
    expected = os.getenv("DEMO_ADMIN_TOKEN", "sih-admin-demo")
    provided = (authorization or "").removeprefix("Bearer ")
    if not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Admin role required")


@app.get("/health")
def health():
    return {"status":"ok", "data_mode":"live-ai+open-data-ready", "ai_web_search": bool(os.getenv("OPENAI_API_KEY"))}

@app.get("/schemes")
def list_schemes(loan_type: str | None = None, max_interest: float | None = Query(default=None, ge=0, le=40)):
    result = SCHEMES
    if loan_type: result = [s for s in result if s["type"].lower() == loan_type.lower()]
    if max_interest is not None: result = [s for s in result if s["interest_rate"] is not None and s["interest_rate"] <= max_interest]
    return {"data_mode":"simulated-prototype", "items":result}

@app.post("/eligibility")
def eligibility(user: Beneficiary):
    ranked = sorted((evaluate(user, s) for s in SCHEMES), key=lambda x: x["match_score"], reverse=True)
    return {"official_approval":False, "data_mode":"simulated-prototype", "recommendations":ranked}

@app.post("/calculator")
def calculator(inp: CalculatorIn):
    return calculate(inp)

@app.get("/partners/route")
def partners_route(scheme_id: str):
    if not any(s["id"] == scheme_id for s in SCHEMES):
        raise HTTPException(404, "scheme not found")
    return {"data_mode":"simulated-prototype", "ranking_basis":["scheme compatibility","operational eligibility","fund status","restriction flag","distance"], "items":route_partner(scheme_id)}

@app.post("/nlp/parse")
def nlp_parse(inp: NLPIn):
    text = inp.text.lower()
    amount = None
    lakh = re.search(r"([\d.]+)\s*(?:lakh|lac|लाख)", inp.text, flags=re.I)
    rupee = re.search(r"₹\s*([\d,]+)", inp.text)
    if lakh: amount = round(float(lakh.group(1)) * 100000)
    elif rupee: amount = int(rupee.group(1).replace(",", ""))
    category = "dairy" if re.search(r"dairy|milk|डेयरी|दूध", text) else "education" if re.search(r"education|college|study|शिक्षा|पढ़ाई", text) else "handicraft" if re.search(r"artisan|handicraft|कारीगर", text) else "retail" if re.search(r"shop|retail|दुकान", text) else "micro"
    return {"purpose":"education" if category == "education" else "business", "business_category":category, "required_loan_amount":amount, "confidence":"prototype-heuristic", "note":"Use an audited multilingual NLU model plus human-readable extraction confirmation in production."}


class AIChatIn(BaseModel):
    message: str = Field(min_length=2, max_length=4000)
    language: str = Field(default="en", min_length=2, max_length=8)
    profile: dict = Field(default_factory=dict)

@app.post("/ai/chat")
async def ai_chat(inp: AIChatIn):
    """Live, source-grounded AI assistant.

    The assistant can research current public information on the internet. It is
    instructed to prioritize official government/financial sources and to
    distinguish verified facts from estimates. It never grants credit or
    guarantees eligibility.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(503, "Advanced AI is not configured. Set OPENAI_API_KEY on the backend.")

    # Use a generally available Responses API model by default. Override with
    # OPENAI_MODEL when deploying a different supported model in your account.
    model = os.getenv("OPENAI_MODEL", "gpt-5")
    language_names = {
        "en":"English","hi":"Hindi","mr":"Marathi","bn":"Bengali",
        "te":"Telugu","ta":"Tamil","gu":"Gujarati","kn":"Kannada",
        "ml":"Malayalam","pa":"Punjabi","or":"Odia","as":"Assamese"
    }
    lang_name = language_names.get(inp.language, "the user's language")

    # Keep the local catalogue available to the model, but tell it that live
    # web research wins when current rules differ.
    compact_catalogue = [
        {k:s.get(k) for k in ("id","name","type","maximum_loan","interest_rate","income_limit","tenure","purposes","states","source_url")}
        for s in SCHEMES
    ]
    official_domains = [
        "myscheme.gov.in", "data.gov.in", "gov.in", "nic.in",
        "standupmitra.in", "kviconline.gov.in", "pmfme.mofpi.gov.in",
        "pmay-urban.gov.in", "sbi.co.in", "unionbankofindia.bank.in",
        "bankofmaharashtra.in", "pib.gov.in"
    ]
    system = f"""You are Pranav AI, the central intelligence layer of an Indian government-scheme and finance discovery website.

Your job is to research CURRENT public information and give evidence-based, personalized scheme guidance.
Respond in {lang_name} whenever possible.

LIVE RESEARCH RULES:
1. Use web search for every substantive scheme/loan question so your answer can reflect current information.
2. Prefer primary/official sources first: myScheme, data.gov.in, relevant Ministry/Department portals, PIB, official scheme portals, and official bank portals. Treat blogs, aggregators and social posts only as secondary context.
3. Do not invent a scheme, eligibility rule, loan limit, interest rate, subsidy, deadline, bank partnership, or application URL.
4. If two sources conflict, say so and prefer the latest official source. Mention the source name and link when practical.
5. Public open-government data from data.gov.in may be used for contextual analysis (beneficiary counts, geography, trends, etc.), but do not turn aggregate statistics into an individual's approval probability.

RECOMMENDATION RULES:
- Analyze the supplied profile: age, gender, marital status, category, disability, residence, state/district, occupation, income, existing loan, purpose, project type/cost and requested loan.
- Rank 3-5 schemes when possible.
- Give a clear "Best scheme for you" recommendation, followed by 2-3 alternatives.
- Explain positive matches AND blockers/missing information.
- Compare requested amount with the scheme's current published limit.
- Separate "scheme eligibility/suitability" from "bank credit approval". Never promise approval.
- If the user asks for EMI/affordability, calculate only from explicitly supplied or clearly sourced assumptions and label estimates.
- Never request or expose Aadhaar, PAN, OTP, passwords, card numbers, bank PINs, or other secrets.

CURRENT LOCAL CATALOGUE (use as a starting point, verify online):
{compact_catalogue}

PRIORITY OFFICIAL DOMAINS:
{official_domains}

Output style: concise, practical, human-readable. Include a short "Why this is recommended" section, "What to verify", and "Official source(s)" when researching schemes."""

    context = f"User language: {inp.language}\nUser profile: {inp.profile}\nUser request: {inp.message}"
    payload = {
        "model": model,
        "input": [
            {"role":"system","content":system},
            {"role":"user","content":context}
        ],
        "tools":[{"type":"web_search_preview"}],
        "temperature":0.2
    }
    headers={"Authorization":f"Bearer {api_key}","Content-Type":"application/json"}
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r=await client.post("https://api.openai.com/v1/responses",json=payload,headers=headers)
        if r.status_code >= 400:
            raise HTTPException(502, f"AI provider error: {r.text[:500]}")
        data=r.json()
        reply=data.get("output_text")
        if not reply:
            for item in data.get("output",[]):
                for c in item.get("content",[]):
                    if c.get("type")=="output_text":
                        reply=c.get("text"); break
                if reply: break
        # Preserve a lightweight audit trail of whether the model actually used
        # the web tool; do not expose raw provider internals to the browser.
        used_web = any(item.get("type","").startswith("web_search") for item in data.get("output",[]))
        return {
            "reply": reply or "I could not generate a response. Please try again.",
            "model": model,
            "live": True,
            "web_research": used_web,
            "research_policy": "official-first"
        }
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"AI connection failed: {exc}")


@app.get('/partners/nearby')
async def partners_nearby(lat:float=Query(...,ge=-90,le=90), lon:float=Query(...,ge=-180,le=180), radius:int=Query(7000,ge=500,le=15000)):
    # Public OpenStreetMap Overpass endpoint; only basic place metadata is returned.
    query=f"[out:json][timeout:20];(nwr[amenity=bank](around:{radius},{lat},{lon});nwr[amenity=atm](around:{radius},{lat},{lon});nwr[amenity=post_office](around:{radius},{lat},{lon}););out center tags;"
    try:
        async with httpx.AsyncClient(timeout=25,headers={'User-Agent':'Pranav-SIH-Prototype/1.0'}) as client:
            r=await client.post('https://overpass-api.de/api/interpreter',data=query)
        r.raise_for_status(); data=r.json(); items=[]
        for e in data.get('elements',[])[:80]:
            tags=e.get('tags',{}); la=e.get('lat',e.get('center',{}).get('lat')); lo=e.get('lon',e.get('center',{}).get('lon'))
            if la is None or lo is None: continue
            items.append({'id':f"osm-{e.get('type')}-{e.get('id')}",'name':tags.get('name','Nearby financial/service point'),'type':tags.get('amenity','service'),'latitude':la,'longitude':lo,'phone':tags.get('phone')})
        return {'live':True,'source':'OpenStreetMap/Overpass','items':items}
    except Exception as exc:
        return {'live':False,'source':'OpenStreetMap/Overpass','items':[],'note':'Nearby lookup temporarily unavailable.'}

@app.get("/admin/metrics", dependencies=[Depends(require_admin)])
def admin_metrics():
    return {"data_mode":"simulated-prototype", "total_users":12480, "total_applications":4286, "eligible_applications":2912, "pending_applications":824}
