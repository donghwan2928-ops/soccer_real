import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "club.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # 부원 테이블
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            position TEXT,
            skill INTEGER,
            phone TEXT
        )
        """
    )

    # 경기 일정 테이블
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            date TEXT,
            place TEXT,
            memo TEXT
        )
        """
    )

    # 참석 정보 테이블
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            member_id INTEGER NOT NULL,
            status TEXT,
            UNIQUE(event_id, member_id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS event_team_sets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS event_team_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            set_id INTEGER NOT NULL,
            team_index INTEGER NOT NULL,
            member_id INTEGER NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


def get_all_members():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, position, skill, phone FROM members ORDER BY id"
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def add_member(name: str, position: str, skill: int, phone: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO members (name, position, skill, phone) VALUES (?, ?, ?, ?)",
        (name, position, skill, phone),
    )
    conn.commit()
    conn.close()


def get_all_events():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, title, date, place, memo FROM events ORDER BY id DESC"
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def add_event(title: str, date: str, place: str, memo: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO events (title, date, place, memo) VALUES (?, ?, ?, ?)",
        (title, date, place, memo),
    )
    conn.commit()
    conn.close()


def get_event(event_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, title, date, place, memo FROM events WHERE id = ?",
        (event_id,),
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_attendance_for_event(event_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT member_id, status FROM attendance WHERE event_id = ?",
        (event_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def set_attendance(event_id: int, member_id: int, status: str):
    conn = get_connection()
    cur = conn.cursor()
    # 이미 있으면 수정, 없으면 새로 넣기
    cur.execute(
        "SELECT id FROM attendance WHERE event_id = ? AND member_id = ?",
        (event_id, member_id),
    )
    row = cur.fetchone()
    if row:
        cur.execute(
            "UPDATE attendance SET status = ? WHERE id = ?",
            (status, row["id"]),
        )
    else:
        cur.execute(
            "INSERT INTO attendance (event_id, member_id, status) VALUES (?, ?, ?)",
            (event_id, member_id, status),
        )
    conn.commit()
    conn.close()

from datetime import datetime

def save_team_set(event_id: int, teams: list):
    """
    teams: [
      {"members": [{id,name,...}, ...], "total_skill": X},
      ...
    ]
    저장 과정:
      1) event_team_sets 행 생성 (created_at)
      2) 각 팀의 멤버들을 event_team_members에 저장
    """
    conn = get_connection()
    cur = conn.cursor()
    created_at = datetime.now().isoformat(timespec="seconds")
    cur.execute(
        "INSERT INTO event_team_sets (event_id, created_at) VALUES (?, ?)",
        (event_id, created_at),
    )
    set_id = cur.lastrowid

    for team_idx, team in enumerate(teams):
        for m in team.get("members", []):
            cur.execute(
                "INSERT INTO event_team_members (set_id, team_index, member_id) VALUES (?, ?, ?)",
                (set_id, team_idx, m["id"]),
            )

    conn.commit()
    conn.close()
    return set_id


def get_team_sets_for_event(event_id: int):
    """해당 이벤트에 저장된 팀 세트 목록(요약)을 반환"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, event_id, created_at FROM event_team_sets WHERE event_id = ? ORDER BY id DESC",
        (event_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_team_members_for_set(set_id: int):
    """
    set_id에 대해 팀별로 멤버 정보를 반환.
    반환 형식: [{team_index:0, members:[member_dict,...]}, ...]
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT team_index, member_id FROM event_team_members WHERE set_id = ? ORDER BY team_index, id",
        (set_id,),
    )
    rows = cur.fetchall()

    # member_id들을 모아서 멤버 정보(이름/실력/포지션)로 치환
    members_map = {}
    # 미리 모든 멤버 가져오기 (작고 효율적)
    cur2 = conn.cursor()
    cur2.execute("SELECT id, name, position, skill, phone FROM members")
    all_members = {r["id"]: dict(r) for r in cur2.fetchall()}

    teams = {}
    for r in rows:
        ti = r["team_index"]
        mid = r["member_id"]
        teams.setdefault(ti, []).append(all_members.get(mid, {"id": mid, "name": "알 수 없음"}))

    # 정렬된 리스트로 반환
    result = []
    for ti in sorted(teams.keys()):
        result.append({"team_index": ti, "members": teams[ti]})
    conn.close()
    return result

