from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import random
import matplotlib.pyplot as plt
from io import BytesIO
import base64


from database import (
    init_db,
    get_all_members,
    add_member,
    get_all_events,
    add_event,
    get_event,
    get_attendance_for_event,
    set_attendance,
    save_team_set,
    get_team_sets_for_event,
    get_team_members_for_set,
)

app = FastAPI()

# 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 템플릿 / 정적 파일 설정
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# DB 테이블들 생성
init_db()


# =========================
# 팀 자동 배정 함수
# =========================
def assign_teams(members, team_count: int = 2):
    if team_count < 2:
        team_count = 2

    # skill이 None이면 0으로
    for m in members:
        if m.get("skill") is None:
            m["skill"] = 0

    # 실력 높은 순 정렬
    sorted_members = sorted(members, key=lambda m: m["skill"], reverse=True)

    teams_members = [[] for _ in range(team_count)]
    teams_skill_sum = [0 for _ in range(team_count)]

    # 실력 높은 사람부터, 현재 합이 가장 낮은 팀에 배치
    for m in sorted_members:
        idx = teams_skill_sum.index(min(teams_skill_sum))
        teams_members[idx].append(m)
        teams_skill_sum[idx] += m["skill"]

    teams = []
    for i in range(team_count):
        team = {
            "members": teams_members[i],
            "total_skill": teams_skill_sum[i],
        }
        teams.append(team)
    return teams


# =========================
# 기본 페이지
# =========================
@app.get("/", response_class=HTMLResponse)
async def read_main(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )


# =========================
# 부원 관리
# =========================
@app.get("/members", response_class=HTMLResponse)
async def list_members(request: Request):
    members = get_all_members()
    return templates.TemplateResponse(
        "members.html",
        {
            "request": request,
            "members": members,
        },
    )


@app.get("/members/new", response_class=HTMLResponse)
async def new_member_form(request: Request):
    return templates.TemplateResponse(
        "member_new.html",
        {"request": request},
    )


@app.post("/members/new")
async def create_member(
    name: str = Form(...),
    position: str = Form(""),
    skill: int = Form(3),
    phone: str = Form(""),
):
    add_member(name, position, skill, phone)
    return RedirectResponse(url="/members", status_code=303)


# =========================
# 팀 자동 배정
# =========================
@app.get("/teams", response_class=HTMLResponse)
async def show_team_page(request: Request):
    members = get_all_members()
    return templates.TemplateResponse(
        "teams.html",
        {
            "request": request,
            "members": members,
            "teams": None,
        },
    )


@app.post("/teams", response_class=HTMLResponse)
async def make_teams(request: Request, team_count: int = Form(2)):
    members = get_all_members()
    teams = assign_teams(members, team_count)
    return templates.TemplateResponse(
        "teams.html",
        {
            "request": request,
            "members": members,
            "teams": teams,
        },
    )


# =========================
# 경기 일정 관리
# =========================
@app.get("/events", response_class=HTMLResponse)
async def list_events(request: Request):
    events = get_all_events()
    return templates.TemplateResponse(
        "events.html",
        {
            "request": request,
            "events": events,
        },
    )


@app.get("/events/new", response_class=HTMLResponse)
async def new_event_form(request: Request):
    return templates.TemplateResponse(
        "event_new.html",
        {
            "request": request,
        },
    )


@app.post("/events/new")
async def create_event(
    title: str = Form(...),
    date: str = Form(""),
    place: str = Form(""),
    memo: str = Form(""),
):
    add_event(title, date, place, memo)
    return RedirectResponse(url="/events", status_code=303)


@app.get("/events/{event_id}", response_class=HTMLResponse)
async def event_detail(request: Request, event_id: int):
    event = get_event(event_id)
    if not event:
        return HTMLResponse("이 일정은 존재하지 않습니다.", status_code=404)

    members = get_all_members()
    attendance_rows = get_attendance_for_event(event_id)
    attendance_map = {row["member_id"]: row["status"] for row in attendance_rows}

    for m in members:
        m["status"] = attendance_map.get(m["id"], "none")

    return templates.TemplateResponse(
        "event_detail.html",
        {
            "request": request,
            "event": event,
            "members": members,
        },
    )


@app.post("/events/{event_id}/attendance")
async def update_attendance(
    event_id: int,
    member_id: int = Form(...),
    status: str = Form(...),
):
    set_attendance(event_id, member_id, status)
    return RedirectResponse(url=f"/events/{event_id}", status_code=303)

# 경기별 참석자 팀 배정 페이지 (GET)
@app.get("/events/{event_id}/teams", response_class=HTMLResponse)
async def event_teams_page(request: Request, event_id: int):
    event = get_event(event_id)
    if not event:
        return HTMLResponse("이 일정은 존재하지 않습니다.", status_code=404)

    members = get_all_members()
    attendance_rows = get_attendance_for_event(event_id)
    attendance_map = {row["member_id"]: row["status"] for row in attendance_rows}

    # 참석(yes)인 사람만 필터링
    attendees = []
    for m in members:
        if attendance_map.get(m["id"]) == "yes":
            attendees.append(m)

    return templates.TemplateResponse(
        "event_teams.html",
        {
            "request": request,
            "event": event,
            "attendees": attendees,
            "teams": None,  # 아직 배정 안 함
        },
    )


# 경기별 참석자 팀 배정 처리 (POST)
@app.post("/events/{event_id}/teams", response_class=HTMLResponse)
async def make_event_teams(
    request: Request,
    event_id: int,
    team_count: int = Form(2),
):
    event = get_event(event_id)
    if not event:
        return HTMLResponse("이 일정은 존재하지 않습니다.", status_code=404)

    members = get_all_members()
    attendance_rows = get_attendance_for_event(event_id)
    attendance_map = {row["member_id"]: row["status"] for row in attendance_rows}

    attendees = []
    for m in members:
        if attendance_map.get(m["id"]) == "yes":
            attendees.append(m)

    teams = []
    if attendees:
        teams = assign_teams(attendees, team_count)

    return templates.TemplateResponse(
        "event_teams.html",
        {
            "request": request,
            "event": event,
            "attendees": attendees,
            "teams": teams,
        },
    )

# 이벤트별로 생성한 팀을 DB에 저장 (POST)
@app.post("/events/{event_id}/teams/save")
async def save_event_teams(event_id: int, team_count: int = Form(2)):
    # 이벤트 존재 확인
    event = get_event(event_id)
    if not event:
        return HTMLResponse("이 일정은 존재하지 않습니다.", status_code=404)

    # 참가(yes) 유저들만 모으기
    members = get_all_members()
    attendance_rows = get_attendance_for_event(event_id)
    attendance_map = {row["member_id"]: row["status"] for row in attendance_rows}
    attendees = [m for m in members if attendance_map.get(m["id"]) == "yes"]

    if not attendees:
        # 참석자가 없으면 팀 페이지로 돌아가기
        return RedirectResponse(url=f"/events/{event_id}/teams", status_code=303)

    # 서버에서 동일 알고리즘으로 팀 생성 -> DB에 저장
    teams = assign_teams(attendees, team_count)
    set_id = save_team_set(event_id, teams)
    # 저장 후 저장된 세트 상세 페이지로 이동
    return RedirectResponse(url=f"/events/{event_id}/teams/saved/{set_id}", status_code=303)


# 해당 이벤트의 저장된 팀 세트 목록 보기
@app.get("/events/{event_id}/teams/saved", response_class=HTMLResponse)
async def list_saved_team_sets(request: Request, event_id: int):
    event = get_event(event_id)
    if not event:
        return HTMLResponse("이 일정은 존재하지 않습니다.", status_code=404)
    sets = get_team_sets_for_event(event_id)
    return templates.TemplateResponse(
        "event_teams_saved_list.html",
        {"request": request, "event": event, "sets": sets},
    )


# 특정 저장 세트 상세 보기 (팀별 구성)
@app.get("/events/{event_id}/teams/saved/{set_id}", response_class=HTMLResponse)
async def view_saved_team_set(request: Request, event_id: int, set_id: int):
    event = get_event(event_id)
    if not event:
        return HTMLResponse("이 일정은 존재하지 않습니다.", status_code=404)

    teams = get_team_members_for_set(set_id)
    # teams는 [{'team_index':0,'members':[...]} ...]
    # 템플릿에 맞게 total_skill 계산
    composed = []
    for t in teams:
        total_skill = sum((m.get("skill") or 0) for m in t["members"])
        composed.append({"members": t["members"], "total_skill": total_skill})

    return templates.TemplateResponse(
        "event_teams_saved_view.html",
        {"request": request, "event": event, "teams": composed, "set_id": set_id},
    )

@app.get("/events/{event_id}/teams/graph", response_class=HTMLResponse)
async def show_team_balance_graph(request: Request, event_id: int):
    sets = get_team_sets_for_event(event_id)
    if not sets:
        return HTMLResponse("저장된 팀이 없습니다.")

    # 가장 최근 세트 선택
    latest_set = sets[-1]
    teams = get_team_members_for_set(latest_set["id"])

    scores = []
    labels = []

    for idx, team in enumerate(teams):
        total = sum(m.get("skill", 0) for m in team["members"])
        scores.append(total)
        labels.append(f"Team {idx+1}")

    # 그래프 생성
    plt.figure()
    plt.bar(labels, scores)
    plt.title("팀 밸런스 점수")
    plt.xlabel("팀")
    plt.ylabel("총 실력 점수")

    # 이미지 저장
    buffer = BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode("utf-8")

    return templates.TemplateResponse(
        "team_graph.html",
        {
            "request": request,
            "image": image_base64
        }
    )

