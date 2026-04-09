from flask import Flask
import requests
import os
import time
import google.generativeai as genai
from datetime import datetime

app = Flask(__name__)

# Configurație din variabile de mediu
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configurare Gemini AI
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload)
    except:
        pass

def analyze_token(token):
    prompt = f"""
    Ești un expert în memecoins pe Solana. Analizează acest token și răspunde DOAR cu JSON valid:

    {{
      "name": "{token.get('name', 'Unknown')}",
      "symbol": "{token.get('symbol', 'N/A')}",
      "mcap": {token.get('mcap', 0)},
      "volume5m": {token.get('volume5m', 0)},
      "volume1h": {token.get('volume1h', 0)},
      "potential_score": scor_de_la_1_la_10,
      "potential_2x": "DA" or "NU",
      "reason": "motiv scurt în română",
      "scam_risk": "DA" or "NU"
    }}

    Date: MCAP ~{token.get('mcap', 0)}k, Volum 5m ~{token.get('volume5m', 0)}k, Volum 1h ~{token.get('volume1h', 0)}k
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except:
        return '{{"potential_2x": "NU", "reason": "Eroare la analiză AI", "scam_risk": "DA"}}'

@app.route("/")
def home():
    return "Botul Solana Memecoin AI rulează!"

@app.route("/scan")
def scan():
    try:
        resp = requests.get("https://api.dexscreener.com/latest/dex/search?q=solana")
        data = resp.json()

        pairs = data.get("pairs", [])[:15]

        for pair in pairs:
            if not pair or not pair.get("baseToken"):
                continue

            fdv = pair.get("fdv") or pair.get("marketCap") or 0
            vol5m = pair.get("volume", {}).get("m5", 0)
            vol1h = pair.get("volume", {}).get("h1", 0)

            if fdv >= 8000 and fdv <= 300000 and (vol5m > 2000 or vol1h > 10000):
                token = {
                    "name": pair["baseToken"].get("name", "Unknown"),
                    "symbol": pair["baseToken"].get("symbol", "N/A"),
                    "mcap": round(fdv / 1000),
                    "volume5m": round(vol5m / 1000),
                    "volume1h": round(vol1h / 1000)
                }

                ai_result = analyze_token(token)

                message = f"""🚨 <b>AI Semnal Memecoin</b>

{token['name']} ({token['symbol']})
MCAP: ~{token['mcap']}k
Volum 5m: ~{token['volume5m']}k
Volum 1h: ~{token['volume1h']}k

AI Analiză:
{ai_result}

🔗 https://dexscreener.com/solana/{pair.get('pairAddress', '')}

DYOR!"""
                send_telegram(message)
                time.sleep(3)

        return "Scan completat cu AI."
    except Exception as e:
        return f"Eroare: {str(e)}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
