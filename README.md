# 우아교통사고 (wooacrash)

한국도로교통공단 사고다발지역 API(공공데이터포털 15058925 보행어린이 / 15057666 보행노인, `apis.data.go.kr/B552061/frequentzone*`)로 만든 교통사고 다발지역 정적 사이트(Python). https://wooacrash.wooahouse.com

- `scripts/fetch_data.py` — 연도×시도(guGun 공백=시도 전체)로 전체 수집 → `data/spots.json.gz`. 호출 약 300회. 어린이 2019~, 노인은 2021~(2021년에 선정 기준이 바뀌어 이전 연도는 빌더에서 제외).
- `scripts/build_site.py` — 지점 `/spot/{c|o}-{spot_cd}/`, 시도·시군구 허브, 어린이/노인 개요, 순위, 검색 인덱스. 지역은 spot_nm 파싱(연도마다 표기가 달라 최신 연도 이름 사용).
- Actions: push 시 빌드, 매월 2일 KST 06:10 수집→커밋→빌드. 시크릿 `API_KEY`. 네이버 토큰은 `scripts/common.py` `NAVER_TOKEN`.
- 활용신청이 필요한 같은 기관 API(보행자·자전거·음주 등)를 추가 승인받으면 fetch_data.py의 EP에 추가.
