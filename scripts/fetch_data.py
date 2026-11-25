# -*- coding: utf-8 -*-
"""
우아교통사고 수집기 — 한국도로교통공단 사고다발지역 API (공공데이터포털 15058925 보행어린이 / 15057666 보행노인)
엔드포인트: apis.data.go.kr/B552061/frequentzoneChild/getRestFrequentzoneChild, frequentzoneOldman/getRestFrequentzoneOldman
연도(searchYearCd) × 시도(siDo, guGun 공백 = 시도 전체)로 전체를 받아 data/spots.json.gz 에 저장한다(호출 약 300회, 매달 1회면 충분).
키: 환경변수 API_KEY → DATA_GO_KR_API_KEY → 로컬 ../hosppass/.env (코드에 넣지 않는다).
사용: python scripts/fetch_data.py
"""
import gzip, json, os, re, sys, time
from datetime import date
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
BASE = "https://apis.data.go.kr/B552061/"
EP = {"c": "frequentzoneChild/getRestFrequentzoneChild", "o": "frequentzoneOldman/getRestFrequentzoneOldman"}
SIDO = ["11", "26", "27", "28", "29", "30", "31", "36", "41", "42", "43", "44", "45", "46", "47", "48", "50", "51", "52"]
FIRST_YEAR = 2019


def api_key():
    for name in ("API_KEY", "DATA_GO_KR_API_KEY"):
        if os.environ.get(name):
            return os.environ[name].strip()
    for p in (ROOT / ".env", ROOT.parent / "hosppass" / ".env"):
        if p.exists():
            m = re.search(r"^API_KEY\s*=\s*(\S+)", p.read_text(encoding="utf-8"), re.M)
            if m:
                return m.group(1).strip("\"'")
    sys.exit("환경변수 API_KEY 가 필요합니다.")


KEY = api_key()
S = requests.Session()


def call(ep, year, sido):
    last = ""
    for attempt in range(6):
        try:
            r = S.get(BASE + ep, params=dict(serviceKey=KEY, type="json", numOfRows=1000, pageNo=1, searchYearCd=year, siDo=sido, guGun=""), timeout=90)
            j = r.json()
            code = str(j.get("resultCode"))
            if code == "03":
                return []
            if code != "00":
                raise RuntimeError("%s %s" % (code, j.get("resultMsg")))
            it = (j.get("items") or {}).get("item", []) if j.get("items") else []
            return it if isinstance(it, list) else [it]
        except (requests.RequestException, ValueError, RuntimeError) as e:
            last = str(e)
            time.sleep(3 + 4 * attempt)
    raise RuntimeError("API 실패 %s %s %s: %s" % (ep, year, sido, last))


def main():
    rows, year_tot = [], {}
    for t, ep in EP.items():
        for y in range(FIRST_YEAR, date.today().year + 1):
            n = 0
            for sd in SIDO:
                for x in call(ep, y, sd):
                    rows.append({"t": t, "y": y, "id": x["spot_cd"], "nm": (x.get("spot_nm") or "").strip(), "b": str(x.get("bjd_cd") or ""),
                                 "o": int(x.get("occrrnc_cnt") or 0), "c": int(x.get("caslt_cnt") or 0), "d": int(x.get("dth_dnv_cnt") or 0),
                                 "s": int(x.get("se_dnv_cnt") or 0), "l": int(x.get("sl_dnv_cnt") or 0), "w": int(x.get("wnd_dnv_cnt") or 0),
                                 "x": x.get("lo_crd") or "", "yy": x.get("la_crd") or ""})
                    n += 1
                time.sleep(0.1)
            year_tot[(t, y)] = n
            print(t, y, n, flush=True)
    # 직전 수집보다 크게 줄었으면 중단(API 일시 오류 방어)
    p = DATA / "spots.json.gz"
    if p.exists():
        prev = len(json.loads(gzip.open(p, "rt", encoding="utf-8").read()))
        if prev > 500 and len(rows) < prev * 0.7:
            sys.exit("행 수가 직전(%d)보다 크게 줄어(%d) 중단" % (prev, len(rows)))
    rows.sort(key=lambda r: (r["t"], r["id"], r["y"]))
    with gzip.GzipFile(p, "wb", compresslevel=9, mtime=0) as f:
        f.write(json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    print("완료: 행", len(rows))


if __name__ == "__main__":
    main()
