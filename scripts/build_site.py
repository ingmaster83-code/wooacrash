# -*- coding: utf-8 -*-
"""우아교통사고 정적 사이트 생성기.
입력: data/spots.json.gz (한국도로교통공단 사고다발지역: 보행어린이 2019~, 보행노인 2021~ — 노인은 2021년부터 선정 기준이 바뀌어 이전 연도는 쓰지 않음)
출력: _site/  (지점 상세, 시도·시군구 허브, 어린이/노인 개요, 순위, 안내, 검색 인덱스, sitemap)
"""
import collections, gzip, json, os, re, shutil, sys
from datetime import datetime, timedelta, timezone

from common import *  # noqa

sys.stdout.reconfigure(encoding="utf-8")
DATA = pathlib.Path(os.environ["DATA_DIR"]) if os.environ.get("DATA_DIR") else ROOT / "data"
TODAY = (datetime.now(timezone.utc) + timedelta(hours=9)).date()

SIDO = {"서울특별시": "서울", "서울": "서울", "부산광역시": "부산", "부산": "부산", "대구광역시": "대구", "대구": "대구", "인천광역시": "인천", "인천": "인천", "광주광역시": "광주", "광주": "광주",
        "대전광역시": "대전", "대전": "대전", "울산광역시": "울산", "울산": "울산", "세종특별자치시": "세종", "세종": "세종", "경기도": "경기", "경기": "경기", "강원도": "강원", "강원특별자치도": "강원",
        "강원": "강원", "충청북도": "충북", "충북": "충북", "충청남도": "충남", "충남": "충남", "전라북도": "전북", "전북특별자치도": "전북", "전북": "전북", "전라남도": "전남", "전남": "전남",
        "경상북도": "경북", "경북": "경북", "경상남도": "경남", "경남": "경남", "제주특별자치도": "제주", "제주": "제주"}
ORDER = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]
TYPE = {"c": dict(slug="child", name="보행어린이", short="어린이", who="12세 이하 보행 어린이", crit="1년간 12세 이하 보행 어린이가 다치거나 사망한 교통사고가 반경 200m 안에서 3건 이상(사망 포함 시 2건 이상) 발생한 지점"),
        "o": dict(slug="old", name="보행노인", short="노인", who="65세 이상 보행 노인", crit="최근 3년간 65세 이상 보행자가 사망·중상을 입은 교통사고가 반경 100m 안에서 5건 이상 발생한 지점")}
SLUG2T = {v["slug"]: k for k, v in TYPE.items()}
MIN_YEAR = {"c": 2019, "o": 2021}


def region_of(nm):
    base = nm.split("(")[0].split()
    if not base or base[0] not in SIDO:
        return "", "", ""
    sido = SIDO[base[0]]
    rest = base[1:]
    if sido == "세종":
        return sido, "세종시", " ".join(rest[:1])
    sgg = rest[0] if rest and re.search(r"(시|군|구)$", rest[0]) else ""
    k = 1 if sgg else 0
    if sgg.endswith("시") and len(rest) > 1 and rest[1].endswith("구"):
        k = 2
    dong = rest[k] if len(rest) > k else ""
    return sido, sgg, dong


def landmark(nm):
    m = re.search(r"\(([^)]*)\)", nm)
    return re.sub(r"\s*(부근|인근)$", "", m.group(1)).strip() if m else ""


def load():
    rows = json.loads(gzip.open(DATA / "spots.json.gz", "rt", encoding="utf-8").read())
    by = collections.defaultdict(list)
    for r in rows:
        if r["y"] >= MIN_YEAR[r["t"]]:
            by[(r["t"], r["id"])].append(r)
    spots = []
    for (t, sid), L in by.items():
        L.sort(key=lambda r: r["y"])
        last = L[-1]
        sido, sgg, dong = region_of(last["nm"])
        if not sido or not sgg:
            continue
        spots.append(dict(t=t, id=sid, key="%s-%s" % (t, sid), nm=last["nm"], sido=sido, sgg=sgg, dong=dong, lm=landmark(last["nm"]), x=last["x"], y=last["yy"],
                          rec=L, years=[r["y"] for r in L], last=last["y"], o=sum(r["o"] for r in L), c=sum(r["c"] for r in L), d=sum(r["d"] for r in L),
                          s=sum(r["s"] for r in L), l=sum(r["l"] for r in L), w=sum(r["w"] for r in L)))
    return spots, max(r["y"] for r in rows)


def title_of(p):
    place = " ".join(x for x in (p["sido"], p["sgg"], p["dong"]) if x)
    return place + ((" " + p["lm"]) if p["lm"] else "")


def link(p):
    return '<a href="/spot/%s/">%s</a>' % (p["key"], esc(title_of(p)))


def ptable(L, cap=100, region=True, show_type=True):
    L = L[:cap]
    head = "<tr><th>지점</th>%s<th>선정 연도</th><th>누적 사상자</th><th>사망</th></tr>" % ("<th>구분</th>" if show_type else "")
    rows = []
    for p in L:
        rows.append("<tr><td>%s</td>%s<td>%s</td><td>%d명</td><td>%d명</td></tr>" % (
            link(p) if region else '<a href="/spot/%s/">%s</a>' % (p["key"], esc((p["dong"] + " " + p["lm"]).strip() or p["nm"])),
            ("<td>%s</td>" % TYPE[p["t"]]["short"]) if show_type else "", esc(yrs(p["years"])), p["c"], p["d"]))
    return '<div class="tbl-wrap"><table class="tbl">%s%s</table></div>' % (head, "".join(rows))


def yrs(ys):
    ys = sorted(ys)
    if not ys:
        return "-"
    out, s, e = [], ys[0], ys[0]
    for y in ys[1:]:
        if y == e + 1:
            e = y
        else:
            out.append((s, e))
            s = e = y
    out.append((s, e))
    return ", ".join(str(a) if a == b else "%d~%d" % (a, b) for a, b in out) + "년"


def stat(L, ly):
    n = collections.Counter(p["t"] for p in L)
    now = sum(1 for p in L if p["last"] == ly)
    s = "사고다발지역으로 선정된 적 있는 지점 <b>%d곳</b>(어린이 %d곳, 노인 %d곳)이고, 이 중 <b>%d곳</b>이 %d년에도 선정됐습니다." % (len(L), n["c"], n["o"], now, ly)
    return '<p class="lead">%s</p>' % s


def hub(path, h1, sub, L, ly, extra="", cap=100, title=None, desc=None, crumbs=None, prio="0.7", region=True, faq=None, show_type=True):
    body = ['<div class="page-head"><h1>%s</h1><p>%s</p></div>' % (esc(h1), esc(sub)), stat(L, ly), ad(), extra, '<h2 class="group-title">지점 목록</h2>', ptable(L, cap, region, show_type)]
    if len(L) > cap:
        body.append('<p class="note">지점이 많아 %d곳만 표시했습니다. 시도·시군구별 페이지에서 좁혀 보세요.</p>' % cap)
    write(path, layout(path, title or h1, desc or sub, "\n".join(b for b in body if b), faq, crumbs or [("홈", "/")], coupang=True), prio)


def page_spot(p, by_sgg, hubs_ok, ly):
    T = TYPE[p["t"]]
    place = title_of(p)
    lead = ["<b>%s</b>은(는) %s 사고다발지역으로 %s에 선정된 지점입니다." % (esc(place), T["name"], esc(yrs(p["years"])))]
    lead.append("선정된 해의 사고는 합계 %d건, 사상자 %d명(사망 %d명, 중상 %d명)입니다." % (p["o"], p["c"], p["d"], p["s"]))
    rows = []
    for r in reversed(p["rec"]):
        rows.append("<tr><th>%d년</th><td>%d건</td><td>%d명</td><td>%d명</td><td>%d명</td><td>%d명</td><td>%d명</td></tr>" % (r["y"], r["o"], r["c"], r["d"], r["s"], r["l"], r["w"]))
    tbl = ('<h2 class="group-title">연도별 사고 현황</h2><div class="tbl-wrap"><table class="tbl"><tr><th>연도</th><th>사고</th><th>사상자</th><th>사망</th><th>중상</th><th>경상</th><th>부상신고</th></tr>%s</table></div>' % "".join(rows))
    info = [("구분", "%s 교통사고 다발지역" % T["name"]), ("지역", " ".join(x for x in (p["sido"], p["sgg"], p["dong"]) if x)), ("위치 설명", p["lm"]), ("선정 연도", yrs(p["years"])), ("선정 기준", T["crit"])]
    itbl = '<div class="tbl-wrap"><table class="tbl">%s</table></div>' % "".join("<tr><th>%s</th><td>%s</td></tr>" % (a, esc(b)) for a, b in info if b)
    body = ['<div class="page-head"><h1>%s</h1><p>%s 사고다발지역 · %s</p></div>' % (esc(place), T["name"], esc(yrs(p["years"]))), '<p class="lead">%s</p>' % " ".join(lead), ad(), itbl, tbl]
    if p["x"] and p["y"]:
        body.append('<p><a class="btn" href="https://map.kakao.com/link/map/%s,%s,%s">🗺️ 지도에서 위치 보기</a></p>' % (urllib.parse.quote((p["lm"] or p["dong"] or "사고다발지역")[:30]), p["y"], p["x"]))
    body.append('<div class="note-box">이 지점은 한국도로교통공단 통계 기준에 해당한 사고다발지역이며, 현재 도로 상태나 위험도를 단정하는 정보가 아닙니다. %s 선정 기준: %s.</div>' % (T["name"], T["crit"]))
    sib = [o for o in by_sgg.get((p["sido"], p["sgg"]), []) if o is not p and o["t"] == p["t"]][:6]
    other = [o for o in by_sgg.get((p["sido"], p["sgg"]), []) if o["t"] != p["t"]][:4]
    if sib or other:
        body.append('<h2 class="group-title">같은 지역 다른 지점 <small>%s %s</small></h2>' % (esc(p["sido"]), esc(p["sgg"])))
        body.append(ptable(sib + other, 10, False))
    chips = []
    if ("sgg", p["sido"], p["sgg"]) in hubs_ok:
        chips.append('<a class="chip" href="/region/%s/%s/">%s %s 사고다발지역</a>' % (q(p["sido"]), q(p["sgg"]), esc(p["sido"]), esc(p["sgg"])))
    chips.append('<a class="chip" href="/region/%s/">%s 사고다발지역</a>' % (q(p["sido"]), esc(p["sido"])))
    if (p["t"], p["sido"]) in hubs_ok:
        chips.append('<a class="chip" href="/%s/%s/">%s %s 사고다발지역</a>' % (T["slug"], q(p["sido"]), esc(p["sido"]), T["short"]))
    body.append('<div class="chips">%s</div>' % "".join(chips))
    n = len(p["years"])
    faq = [("%s은(는) 사고다발지역에 몇 번 선정됐나요?" % place, "%s 기준 %s에 선정돼 총 %d회입니다. %s" % (T["name"], yrs(p["years"]), n, ("%d년에도 선정됐습니다." % ly) if p["last"] == ly else "%d년 목록에는 포함되지 않았습니다." % ly)),
           ("%s 사고다발지역은 어떤 기준으로 선정하나요?" % T["name"], "%s이며, 한국도로교통공단 교통사고분석시스템 자료를 기준으로 합니다." % T["crit"] + (" 노인 사고다발지역은 2021년부터 기준이 바뀌어 이전 연도와 직접 비교하기 어렵습니다." if p["t"] == "o" else "")),
           ("%s에서 사고가 많이 난다는 뜻인가요?" % place, "사고다발지역은 기준 이상의 사고가 반경 안에서 발생했다는 통계상 지점입니다. 선정 이후 개선 사업으로 상황이 달라졌을 수 있으니 현장 표지와 신호를 우선 따르세요.")]
    crumbs = [("홈", "/"), (p["sido"], "/region/%s/" % p["sido"]), ((place[:30] + "…") if len(place) > 30 else place, "/spot/%s/" % p["key"])]
    ld = [{"@context": "https://schema.org", "@type": "Place", "name": place, "address": " ".join(x for x in (p["sido"], p["sgg"], p["dong"]) if x)}]
    if p["x"] and p["y"]:
        ld[0]["geo"] = {"@type": "GeoCoordinates", "latitude": p["y"], "longitude": p["x"]}
    title = "%s %s 교통사고 다발지역 - %s" % (place, T["name"], yrs(p["years"]))
    desc = "%s %s 사고다발지역. %s 선정, 사고 %d건·사상자 %d명(사망 %d명) 연도별 현황과 선정 기준을 정리했습니다." % (place, T["name"], yrs(p["years"]), p["o"], p["c"], p["d"])
    write("/spot/%s/" % p["key"], layout("/spot/%s/" % p["key"], title, desc, "\n".join(body), faq, crumbs, "article", ld, coupang=True), "0.6")


def build():
    ps, ly = load()
    print("지점", len(ps), "최근연도", ly)
    ps.sort(key=lambda p: (-p["last"], -p["c"], -p["d"], p["key"]))
    by_sido, by_sgg, by_ts = (collections.defaultdict(list) for _ in range(3))
    by_t = collections.defaultdict(list)
    for p in ps:
        by_sido[p["sido"]].append(p)
        by_sgg[(p["sido"], p["sgg"])].append(p)
        by_t[p["t"]].append(p)
        by_ts[(p["t"], p["sido"])].append(p)
    hubs_ok = {("sgg", s, g) for (s, g), L in by_sgg.items() if len(L) >= 2} | {(t, s) for (t, s), L in by_ts.items() if len(L) >= 3}
    OUT.mkdir(parents=True, exist_ok=True)
    for ch in OUT.iterdir():
        shutil.rmtree(ch) if ch.is_dir() else ch.unlink()
    for p in ps:
        page_spot(p, by_sgg, hubs_ok, ly)
    sidos = [s for s in ORDER if s in by_sido]
    # 시도
    for s in sidos:
        L = by_sido[s]
        gc = collections.Counter(p["sgg"] for p in L)
        extra = '<h2 class="group-title">시군구별</h2><div class="chips">%s</div>' % "".join(
            ('<a class="chip" href="/region/%s/%s/">%s <small>%d</small></a>' % (q(s), q(g), esc(g), n)) if ("sgg", s, g) in hubs_ok else '<span class="chip">%s <small>%d</small></span>' % (esc(g), n) for g, n in gc.most_common())
        for t in ("c", "o"):
            if (t, s) in hubs_ok:
                extra += '<p><a class="chip" href="/%s/%s/">%s 보행%s 사고다발지역 %d곳</a></p>' % (TYPE[t]["slug"], q(s), esc(s), TYPE[t]["short"], len(by_ts[(t, s)]))
        hub("/region/%s/" % s, "%s 교통사고 다발지역 %d곳 - 어린이·노인 보행" % (s, len(L)), "스쿨존·보행 사고다발지역 정리", L, ly, extra, 100,
            "%s 교통사고 다발지역 %d곳 - 보행어린이·보행노인" % (s, len(L)), "%s의 보행어린이·보행노인 교통사고 다발지역 %d곳을 시군구별로 정리했습니다. 연도별 사고와 사상자, 선정 기준을 확인하세요." % (s, len(L)),
            [("홈", "/"), ("지역별", "/region/"), (s, "/region/%s/" % s)], "0.8",
            faq=[("%s에는 사고다발지역이 몇 곳 있나요?" % s, "한국도로교통공단 보행어린이(2019년~)·보행노인(2021년~) 사고다발지역에 한 번이라도 선정된 지점은 %d곳입니다." % len(L))])
    for (s, g), L in by_sgg.items():
        if ("sgg", s, g) in hubs_ok:
            hub("/region/%s/%s/" % (s, g), "%s %s 교통사고 다발지역 %d곳" % (s, g, len(L)), "보행어린이·보행노인 사고다발지역", L, ly, "", 100, "%s %s 교통사고 다발지역 %d곳 - 어린이·노인 보행" % (s, g, len(L)),
                "%s %s의 보행어린이·보행노인 교통사고 다발지역 %d곳의 선정 연도와 사상자 현황을 정리했습니다." % (s, g, len(L)), [("홈", "/"), (s, "/region/%s/" % s), (g, "/region/%s/%s/" % (s, g))], "0.6", region=False)
    cards = "".join('<a class="card" href="/region/%s/"><b>%s</b><span>%d곳</span></a>' % (q(s), esc(s), len(by_sido[s])) for s in sidos)
    write("/region/", layout("/region/", "지역별 교통사고 다발지역", "시도별 보행어린이·보행노인 교통사고 다발지역을 확인하세요.", '<div class="page-head"><h1>지역별 교통사고 다발지역</h1></div>' + ad() + '<div class="card-grid">%s</div>' % cards, None, [("홈", "/"), ("지역별", "/region/")]), "0.8")
    # 유형
    for t in ("c", "o"):
        T, L = TYPE[t], by_t[t]
        sc = collections.Counter(p["sido"] for p in L)
        extra = '<h2 class="group-title">시도별</h2><div class="chips">%s</div>' % "".join(
            ('<a class="chip" href="/%s/%s/">%s <small>%d</small></a>' % (T["slug"], q(s), esc(s), sc[s])) if (t, s) in hubs_ok else '<span class="chip">%s <small>%d</small></span>' % (esc(s), sc[s]) for s in sidos if sc[s])
        extra += '<div class="note-box"><b>선정 기준</b> — %s. 한국도로교통공단 교통사고분석시스템 자료를 기준으로 합니다.%s</div>' % (T["crit"], " 2021년부터 기준이 바뀌어 이 사이트는 2021년 이후 자료만 사용합니다." if t == "o" else "")
        hub("/%s/" % T["slug"], "%s 교통사고 다발지역 %d곳" % (T["name"], len(L)), "%s 사고다발지역 전국 목록" % T["who"], L, ly, extra, 100, "%s 교통사고 다발지역 전국 %d곳 - 시도별" % (T["name"], len(L)),
            "%s 사고다발지역 %d곳을 시도·시군구별로 정리했습니다. 선정 기준과 연도별 사고·사상자를 확인하세요." % (T["who"], len(L)), [("홈", "/"), (T["short"], "/%s/" % T["slug"])], "0.8", show_type=False)
        for s in sidos:
            if (t, s) in hubs_ok:
                L2 = by_ts[(t, s)]
                hub("/%s/%s/" % (T["slug"], s), "%s 보행%s 교통사고 다발지역 %d곳" % (s, T["short"], len(L2)), "%s 사고다발지역" % T["who"], L2, ly, "", 100, "%s %s 교통사고 다발지역 %d곳" % (s, T["name"], len(L2)),
                    "%s의 %s 교통사고 다발지역 %d곳의 선정 연도와 사상자를 정리했습니다." % (s, T["who"], len(L2)), [("홈", "/"), (T["short"], "/%s/" % T["slug"]), (s, "/%s/%s/" % (T["slug"], s))], "0.6", show_type=False)
    # 순위
    def rank_page(path, h1, key, sub, cond=None):
        L = [p for p in ps if (cond is None or cond(p))]
        L = sorted(L, key=key)[:50]
        body = ['<div class="page-head"><h1>%s</h1><p>%s</p></div>' % (esc(h1), esc(sub)), ad(), ptable(L, 50, True)]
        write(path, layout(path, h1, sub, "\n".join(body), None, [("홈", "/"), ("순위", "/ranking/"), (h1, path)], coupang=True), "0.7")
    rank_page("/ranking/casualty/", "누적 사상자가 많은 사고다발지역 TOP50", lambda p: (-p["c"], -p["d"], p["key"]), "선정 연도의 사상자를 합산한 순위(2019~%d년, 노인은 2021년~)" % ly)
    rank_page("/ranking/death/", "누적 사망자가 많은 사고다발지역 TOP50", lambda p: (-p["d"], -p["c"], p["key"]), "선정 연도의 사망자를 합산한 순위", lambda p: p["d"] > 0)
    rank_page("/ranking/repeat/", "사고다발지역에 가장 자주 선정된 지점 TOP50", lambda p: (-len(p["years"]), -p["c"], p["key"]), "여러 해 연속 또는 반복해 선정된 지점", lambda p: len(p["years"]) >= 2)
    rank_page("/ranking/latest/", "%d년 사고다발지역 사상자 순위" % ly, lambda p: (-[r for r in p["rec"] if r["y"] == ly][0]["c"], p["key"]), "%d년에 선정된 지점을 사상자 순으로 정렬" % ly, lambda p: p["last"] == ly)
    sg = sorted(by_sgg.items(), key=lambda kv: (-sum(1 for p in kv[1] if p["last"] == ly), -len(kv[1])))[:50]
    rows = "".join('<tr><td><a href="%s">%s %s</a></td><td>%d곳</td><td>%d곳</td></tr>' % (("/region/%s/%s/" % (q(s), q(g))) if ("sgg", s, g) in hubs_ok else ("/region/%s/" % q(s)), esc(s), esc(g), len(L), sum(1 for p in L if p["last"] == ly)) for (s, g), L in sg)
    write("/ranking/region/", layout("/ranking/region/", "교통사고 다발지역이 많은 시군구 TOP50", "%d년 사고다발지역이 많은 시군구 순위" % ly, '<div class="page-head"><h1>사고다발지역이 많은 시군구 TOP50</h1><p>%d년 선정 지점 수 기준</p></div>' % ly + ad() +
          '<div class="tbl-wrap"><table class="tbl"><tr><th>시군구</th><th>누적 지점</th><th>%d년 선정</th></tr>%s</table></div>' % (ly, rows), None, [("홈", "/"), ("순위", "/ranking/"), ("시군구", "/ranking/region/")], coupang=True), "0.7")
    cards = "".join('<a class="card" href="%s"><b>%s</b><span>%s</span></a>' % (u, esc(n), esc(d)) for u, n, d in [
        ("/ranking/casualty/", "누적 사상자 TOP50", "사상자가 가장 많았던 지점"), ("/ranking/death/", "누적 사망자 TOP50", "사망 사고가 있었던 지점"), ("/ranking/repeat/", "반복 선정 TOP50", "여러 해 선정된 지점"),
        ("/ranking/latest/", "%d년 사상자 순위" % ly, "최근 연도 선정 지점"), ("/ranking/region/", "시군구 순위", "사고다발지역이 많은 지역")])
    write("/ranking/", layout("/ranking/", "교통사고 다발지역 순위", "보행어린이·보행노인 교통사고 다발지역 순위 모음", '<div class="page-head"><h1>교통사고 다발지역 순위</h1></div>' + ad() + '<div class="card-grid">%s</div>' % cards, None, [("홈", "/"), ("순위", "/ranking/")]), "0.8")
    # 홈
    nl = {t: sum(1 for p in by_t[t] if p["last"] == ly) for t in ("c", "o")}
    body = ['<div class="hero"><h1>우리 동네 교통사고 다발지역</h1><p>한국도로교통공단 공공데이터로 보행어린이·보행노인 사고다발지역을 시군구별로 확인하세요</p>'
            '<div class="today-box"><div><small>%d년 어린이 사고다발지역</small><b>%d곳</b></div><div><small>%d년 노인 사고다발지역</small><b>%d곳</b></div><div><small>수록 지점(누적)</small><b>%d곳</b></div></div></div>' % (ly, nl["c"], ly, nl["o"], len(ps)),
            '<div class="search-box"><input id="q" type="search" placeholder="동네·지점 검색 (예: 강남구 대치동, 수원 스쿨존)" autocomplete="off"><div id="sr" class="sr-list"></div></div>', ad(),
            '<h2 class="group-title">유형별</h2><div class="card-grid"><a class="card" href="/child/"><b>보행어린이 사고다발지역</b><span>%d곳</span></a><a class="card" href="/old/"><b>보행노인 사고다발지역</b><span>%d곳</span></a></div>' % (len(by_t["c"]), len(by_t["o"])),
            '<h2 class="group-title">지역별</h2><div class="card-grid">%s</div>' % "".join('<a class="card" href="/region/%s/"><b>%s</b><span>%d곳</span></a>' % (q(s), esc(s), len(by_sido[s])) for s in sidos),
            '<h2 class="group-title">%d년 사고다발지역 주요 지점</h2>' % ly, ptable([p for p in ps if p["last"] == ly][:10], 10), '<script src="/assets/js/search.js"></script>']
    faq = [("사고다발지역은 어떻게 정해지나요?", "보행어린이는 1년간 12세 이하 보행 어린이 교통사고가 반경 200m 안에 3건 이상(사망 포함 시 2건 이상), 보행노인은 2021년부터 최근 3년간 65세 이상 보행자 사망·중상 사고가 반경 100m 안에 5건 이상 발생한 지점입니다."),
           ("데이터는 어디서 가져왔나요?", "한국도로교통공단 교통사고분석시스템 자료를 공공데이터포털(보행어린이 15058925, 보행노인 15057666)에서 받아 정리했습니다. 매달 갱신합니다."),
           ("여기 나온 곳이 지금도 위험한가요?", "통계상 기준에 해당한 지점이며 이후 시설 개선으로 달라졌을 수 있습니다. 현장의 표지와 신호를 우선 따르세요.")]
    ld = [{"@context": "https://schema.org", "@type": "WebSite", "name": "우아교통사고", "url": BASE + "/", "potentialAction": {"@type": "SearchAction", "target": BASE + "/?q={q}", "query-input": "required name=q"}}]
    write("/", layout("/", "우리 동네 교통사고 다발지역 %d곳 - 어린이·노인 보행 | 우아교통사고" % len(ps), "한국도로교통공단 공공데이터로 보행어린이·보행노인 교통사고 다발지역 %d곳을 시군구별로 확인하세요." % len(ps), "\n".join(body), faq, None, "website", ld), "1.0")
    idx = [[title_of(p), "/spot/%s/" % p["key"], TYPE[p["t"]]["short"], " ".join(x for x in (p["sido"], p["sgg"]) if x), ""] for p in ps]
    (OUT / "search_index.json").write_text(json.dumps(idx, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    pages_static(ly)
    finish()


def pages_static(ly):
    body = ['<div class="page-head"><h1>교통사고 다발지역 보는 방법과 안전 수칙</h1></div>', ad(),
            '<h2 class="group-title">1. 사고다발지역이란</h2><p class="lead">같은 장소에서 비슷한 사고가 반복되는 지점을 통계 기준으로 뽑은 것입니다. 이 사이트는 <a href="/child/">보행어린이</a>와 <a href="/old/">보행노인</a> 사고다발지역을 다룹니다. 목록에 있다고 해서 지금 그 장소가 특별히 위험하다는 뜻은 아닙니다.</p>',
            '<h2 class="group-title">2. 운전자가 알아둘 점</h2><ul class="lead"><li>어린이보호구역(스쿨존)에서는 표지판의 제한속도(대부분 시속 30km 이내)를 지켜야 하고, 어린이 사고는 가중처벌 대상이 될 수 있습니다.</li><li>횡단보도 앞 일시정지, 골목 진출입로 서행은 보행 어린이·노인 사고를 줄이는 기본 수칙입니다.</li><li>야간·우천 시에는 어린이와 노인 보행자가 잘 보이지 않으니 속도를 더 낮추세요.</li></ul>',
            '<h2 class="group-title">3. 보행자와 보호자가 알아둘 점</h2><ul class="lead"><li>어린이는 횡단보도 앞에서 멈추고 차가 선 것을 확인한 뒤 건너도록 지도하세요.</li><li>노인 보행자는 무단횡단을 피하고, 밝은 옷이나 반사 용품을 착용하면 도움이 됩니다.</li><li>사고다발지역 근처를 자주 지나면 해당 구청·경찰서의 교통안전 시설 개선 민원을 활용할 수 있습니다.</li></ul>',
            '<div class="note-box">이 사이트는 공개 통계를 정리한 참고용이며 법률·보험 자문이 아닙니다. 사고 처리나 합의는 경찰·보험사·전문가와 상담하세요.</div>']
    write("/guide/", layout("/guide/", "교통사고 다발지역 보는 방법과 안전 수칙", "사고다발지역의 의미와 운전자·보행자 안전 수칙을 정리했습니다.", "\n".join(body), None, [("홈", "/"), ("이용 안내", "/guide/")]), "0.4")
    body = ['<div class="page-head"><h1>데이터 설명</h1></div>', '<p class="lead">우아교통사고는 한국도로교통공단의 <b>보행어린이 교통사고 다발지역</b>(공공데이터포털 15058925)과 <b>보행노인 교통사고 다발지역</b>(15057666) API를 정리합니다. 어린이는 2019~%d년, 노인은 2021~%d년 자료를 사용합니다(노인 사고다발지역은 2021년부터 선정 기준이 바뀌어 이전 연도와 비교할 수 없어 제외). 사상자·사망·중상·경상·부상신고 건수는 원자료 그대로이며, 지점 이름은 가장 최근 연도 표기를 따릅니다. 매달 1일 새로 받아 갱신합니다.</p>' % (ly, ly)]
    write("/about/", layout("/about/", "데이터 설명", "우아교통사고가 사용하는 한국도로교통공단 사고다발지역 데이터를 설명합니다.", "\n".join(body), None, [("홈", "/"), ("데이터 설명", "/about/")]), "0.3")
    body = ['<div class="page-head"><h1>개인정보처리방침</h1></div>', '<p class="lead">우아교통사고는 회원가입·로그인 없이 이용하며 개인정보를 수집하지 않습니다. 사이트 개선을 위해 Google Analytics를 사용하고, 광고 게재를 위해 Google AdSense와 쿠팡 파트너스를 사용하며 이 과정에서 쿠키가 사용될 수 있습니다.</p>']
    write("/privacy/", layout("/privacy/", "개인정보처리방침", "우아교통사고 개인정보처리방침", "\n".join(body), None, [("홈", "/"), ("개인정보처리방침", "/privacy/")]), sitemap=False)


def finish():
    shutil.copytree(ROOT / "assets", OUT / "assets")
    for nf in ROOT.glob("naver*.html"):
        shutil.copy(nf, OUT / nf.name)
    today = TODAY.isoformat()
    urls = "".join("<url><loc>%s%s</loc><lastmod>%s</lastmod><priority>%s</priority></url>" % (BASE, q(p), today, pr) for p, pr in WRITTEN)
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>\n' % urls, encoding="utf-8")
    (OUT / "robots.txt").write_text("User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % BASE, encoding="utf-8")
    (OUT / "CNAME").write_text("wooacrash.wooahouse.com\n", encoding="utf-8")
    nf = layout("/404.html", "페이지를 찾을 수 없습니다", "요청한 페이지를 찾을 수 없습니다.", '<div class="page-head"><h1>페이지를 찾을 수 없습니다</h1></div><div class="chips"><a class="chip" href="/">홈으로</a><a class="chip" href="/region/">지역별</a><a class="chip" href="/ranking/">순위</a></div>', None, None, noindex=True)
    (OUT / "404.html").write_text(nf, encoding="utf-8")
    print("페이지", len(WRITTEN), "(sitemap)")


if __name__ == "__main__":
    build()
