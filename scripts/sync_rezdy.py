"""Busca voos/bookings na Rezdy e gera assets/rezdy_dados.js para o hub.

Uso: REZDY_API_KEY=... python scripts/sync_rezdy.py
Somente biblioteca padrão. Não grava nome, e-mail ou telefone de clientes, nem valores financeiros
(o repositório é público).
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone

API = "https://api.rezdy.com/v1/"
TZ = timezone(timedelta(hours=-3))  # America/Sao_Paulo (sem horário de verão)
ATIVOS = {"CONFIRMED", "PENDING_SUPPLIER", "PENDING_CUSTOMER", "ON_HOLD", "PROCESSING"}
NAO_VOO = ("gift card", "no-show", "shuttle", "teste")
SAIDA = os.path.join(os.path.dirname(__file__), "..", "assets", "rezdy_dados.js")

KEY = os.environ.get("REZDY_API_KEY") or os.environ.get("REZDY_KEY")
if not KEY:
    sys.exit("REZDY_API_KEY não definido")


def get(endpoint, params):
    q = urllib.parse.urlencode(dict(params, apiKey=KEY), doseq=True)
    for tentativa in range(4):
        try:
            with urllib.request.urlopen(API + endpoint + "?" + q, timeout=40) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 429 or tentativa == 3:
                raise
            time.sleep(5 * (tentativa + 1))


def eh_voo(nome):
    return not any(x in (nome or "").lower() for x in NAO_VOO)


agora = datetime.now(TZ)
hoje = agora.date()
seg = hoje - timedelta(days=hoje.weekday())
dom = seg + timedelta(days=6)
ate = max(dom, hoje + timedelta(days=7))  # proximos 7 dias
inicio = min(hoje.replace(day=1), seg)

# produtos: duração por código
produtos = get("products", {"limit": 100}).get("products", [])
duracao = {p["productCode"]: p.get("durationMinutes") or 30 for p in produtos}
codigos_voo = [p["productCode"] for p in produtos if eh_voo(p.get("name"))]

# bookings do período (paginado)
bookings, off = [], 0
while True:
    pg = get("bookings", {
        "minTourStartTime": f"{inicio}T00:00:00-03:00",
        "maxTourStartTime": f"{ate}T23:59:59-03:00",
        "limit": 100, "offset": off,
    }).get("bookings") or []
    bookings += pg
    if len(pg) < 100:
        break
    off += 100

# agrupa por horário de saída (produtos no mesmo horário = mesmo voo)
slots = defaultdict(lambda: {"produtos": set(), "min": 0, "bookings": []})
for b in bookings:
    if b.get("status") not in ATIVOS:
        continue
    for it in b.get("items", []):
        if not eh_voo(it.get("productName")):
            continue
        ini = it.get("startTimeLocal")
        if not ini:
            continue
        s = slots[ini[:16]]
        s["produtos"].add(it.get("productName"))
        s["min"] = max(s["min"], duracao.get(it.get("productCode"), 30))
        s["bookings"].append({
            "order": b["orderNumber"],
            "pax": it.get("totalQuantity") or sum(q.get("value", 0) for q in it.get("quantities", [])),
            "status": b["status"],
            "canal": b.get("resellerName") or b.get("source") or "",
        })


def monta(chave, s):
    return {
        "data": chave[:10], "hora": chave[11:16], "produtos": sorted(s["produtos"]),
        "min": s["min"], "pax": sum(x["pax"] for x in s["bookings"]),
        "bookings": s["bookings"],
    }


todos = [monta(k, slots[k]) for k in sorted(slots)]

# capacidade dos horários de hoje
cap = {}
if codigos_voo:
    ses = get("availability", {
        "productCode": codigos_voo, "startTimeLocal": f"{hoje} 00:00:00",
        "endTimeLocal": f"{hoje} 23:59:59", "limit": 500,
    }).get("sessions") or []
    for x in ses:
        h = x["startTimeLocal"][11:16]
        c = cap.setdefault(h, {"capacidade": 0, "livres": None})
        c["capacidade"] = max(c["capacidade"], x.get("seats") or 0)
        lv = x.get("seatsAvailable")
        if lv is not None:
            c["livres"] = lv if c["livres"] is None else min(c["livres"], lv)

voos_hoje = []
for v in todos:
    if v["data"] == str(hoje):
        v.update(cap.get(v["hora"], {"capacidade": None, "livres": None}))
        voos_hoje.append(v)

agora_s = agora.strftime("%Y-%m-%d %H:%M")
mes = [v for v in todos if v["data"][:7] == str(hoje)[:7] and f"{v['data']} {v['hora']}" <= agora_s]
semana = [v for v in todos if str(seg) <= v["data"] <= str(dom)]
proximos = [v for v in todos if str(hoje) < v["data"] <= str(ate)]

dados = {
    "gerado_em": agora.isoformat(timespec="minutes"),
    "hoje": str(hoje),
    "voos_hoje": voos_hoje,
    "semana": semana,
    "proximos": proximos,
    "mes": {
        "voos": len(mes),
        "horas": round(sum(v["min"] for v in mes) / 60, 1),
        "pax": sum(v["pax"] for v in mes),
    },
}
with open(SAIDA, "w", encoding="utf-8") as f:
    f.write("// GERADO POR scripts/sync_rezdy.py: não editar à mão\n")
    f.write("const REZDY=" + json.dumps(dados, ensure_ascii=False, separators=(",", ":")) + ";\n")
print(f"{len(voos_hoje)} voos hoje, {len(semana)} na semana, mês: {dados['mes']}")
