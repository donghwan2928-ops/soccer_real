\# ⚽ Real Club Manager (동아리 관리 웹앱)



부산대 전기·전자·컴퓨터 동아리 \*\*레알 일렉트론\*\*을 위한  

부원 관리 + 경기 일정 + 참석 체크 + 팀 자동 배정 웹 서비스입니다.



\## ✨ 주요 기능



\- 부원 관리

&nbsp; - 이름 / 포지션 / 실력 / 연락처 등록

&nbsp; - 부원 목록 확인



\- 경기 일정 관리

&nbsp; - 경기 일정 추가 (제목, 날짜/시간, 장소, 메모)

&nbsp; - 일정 목록 / 상세 보기



\- 참석 체크

&nbsp; - 각 경기별로 부원 참석 / 불참 / 미정 기록



\- 팀 자동 배정

&nbsp; - 전체 부원 기준 팀 배정

&nbsp; - 특정 경기 “참석(yes)” 한 사람만 대상으로 팀 배정

&nbsp; - 실력 점수 기반으로 팀 별 총합이 비슷하도록 자동 분배



\- 팀 기록 저장

&nbsp; - 경기별로 팀 배정 결과를 세트로 저장

&nbsp; - 저장된 팀 세트 목록 / 상세 보기



\## 🛠 기술 스택



\- Python 3.13

\- FastAPI

\- Jinja2 템플릿

\- SQLite (club.db)

\- HTML / CSS



\## 📁 프로젝트 구조



```text

real-club/

&nbsp; app.py               # FastAPI 메인 서버

&nbsp; database.py          # DB 연동 및 함수

&nbsp; club.db              # SQLite 데이터베이스 파일

&nbsp; templates/           # HTML 템플릿

&nbsp;   base.html

&nbsp;   index.html

&nbsp;   members.html

&nbsp;   member\_new.html

&nbsp;   events.html

&nbsp;   event\_new.html

&nbsp;   event\_detail.html

&nbsp;   teams.html

&nbsp;   event\_teams.html

&nbsp;   event\_teams\_saved\_list.html

&nbsp;   event\_teams\_saved\_view.html

&nbsp;   team\_graph.html

&nbsp; static/              # (선택) CSS/이미지



