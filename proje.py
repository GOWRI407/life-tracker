"""Personal Life Tracker - Streamlit edition.

Multi-user, per-user themes, task start/deadline alerts, proof photos.
Run with:  streamlit run app.py
"""
import base64
import hashlib
import html
import json
import os
import re
import secrets
import uuid
from datetime import date, datetime, time as dtime, timedelta

import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

DATA_DIR, IMG_DIR, AUDIO_DIR = "data", "images", "audio"
USERS_FILE = os.path.join(DATA_DIR, "users.json")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)

PRESETS = {
    "Ocean": {"bg": "#EAF4FB", "card": "#FFFFFF", "text": "#12324A", "primary": "#1E88E5"},
    "Forest": {"bg": "#EEF5EC", "card": "#FFFFFF", "text": "#1F3A28", "primary": "#2E7D32"},
    "Sunset": {"bg": "#FFF3E8", "card": "#FFFFFF", "text": "#4A2A14", "primary": "#EF6C00"},
    "Rose": {"bg": "#FDEEF3", "card": "#FFFFFF", "text": "#4A1F30", "primary": "#D81B60"},
    "Midnight": {"bg": "#14161F", "card": "#1E2130", "text": "#E8EAF2", "primary": "#7C8CFF"},
    "Charcoal": {"bg": "#1B1B1B", "card": "#272727", "text": "#EDEDED", "primary": "#26A69A"},
}
FONTS = {
    "Clean (Inter)": "Inter",
    "Friendly (Poppins)": "Poppins",
    "Elegant (Playfair Display)": "Playfair Display",
    "Code (JetBrains Mono)": "JetBrains Mono",
}
DEFAULT_SETTINGS = {**PRESETS["Ocean"], "preset": "Ocean", "font": "Inter",
                    "sound": True, "notify": True, "radius": 12}
APPS = ["Instagram", "YouTube", "WhatsApp", "Chrome", "Other"]


# ---------------------------------------------------------------- storage
def read_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def data_path(user):
    return os.path.join(DATA_DIR, user, "tracker.json")


def load_data(user):
    d = read_json(data_path(user), {})
    for key in ("habits", "health", "skincare", "screen_time"):
        d.setdefault(key, [])
    d["settings"] = {**DEFAULT_SETTINGS, **d.get("settings", {})}
    return d


def save():
    write_json(data_path(st.session_state.user), st.session_state.data)


def upsert(d, key, record):
    """One record per day: replace today's record if it already exists."""
    d[key] = sorted([r for r in d[key] if r["date"] != record["date"]] + [record],
                    key=lambda r: r["date"])
    save()


# ------------------------------------------------------------------- auth
def hash_pw(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 100_000).hex()


def register(user, password):
    users = read_json(USERS_FILE, {})
    if not re.fullmatch(r"[A-Za-z0-9_]{3,20}", user):
        return "Username must be 3-20 letters, numbers or underscore."
    if user.lower() in {u.lower() for u in users}:
        return "That username is already taken."
    if len(password) < 4:
        return "Password must be at least 4 characters."
    salt = secrets.token_hex(16)
    users[user] = {"salt": salt, "hash": hash_pw(password, salt)}
    write_json(USERS_FILE, users)
    return None


def check_login(user, password):
    rec = read_json(USERS_FILE, {}).get(user)
    return bool(rec) and secrets.compare_digest(rec["hash"], hash_pw(password, rec["salt"]))


def auth_screen():
    apply_theme(DEFAULT_SETTINGS)
    st.title("✅ Personal Life Tracker")
    st.caption("Each user gets their own data and their own theme.")
    tab_in, tab_up = st.tabs(["Login", "Create account"])
    with tab_in:
        with st.form("login"):
            user = st.text_input("Username")
            pw = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if check_login(user.strip(), pw):
                    st.session_state.user = user.strip()
                    st.session_state.data = load_data(user.strip())
                    st.rerun()
                else:
                    st.error("Wrong username or password.")
    with tab_up:
        with st.form("register"):
            user = st.text_input("Choose a username")
            pw = st.text_input("Choose a password", type="password")
            if st.form_submit_button("Create account"):
                err = register(user.strip(), pw)
                st.error(err) if err else st.success("Account created. Now log in from the Login tab.")


# ------------------------------------------------------------------ theme
def apply_theme(s):
    font = s["font"]
    st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family={font.replace(' ', '+')}:wght@400;600;700&display=swap');
.stApp {{ background:{s['bg']}; --primary:{s['primary']}; }}
html, body, .stApp, .stApp p, .stApp label, .stApp li, h1, h2, h3, h4, h5,
[data-testid="stMetricValue"], [data-testid="stMetricLabel"], [data-testid="stCaptionContainer"] {{
    color:{s['text']}; font-family:'{font}', sans-serif; }}
[data-testid="stSidebar"] {{ background:{s['card']}; }}
[data-testid="stHeader"] {{ background:transparent; }}
.stButton>button, .stFormSubmitButton>button {{
    background:{s['primary']}; border:none; border-radius:{s['radius']}px; font-weight:600; }}
.stButton>button p, .stFormSubmitButton>button p {{ color:#fff !important; }}
[data-baseweb="input"] input, [data-baseweb="textarea"] textarea, [data-baseweb="select"]>div {{
    background:{s['card']}; color:{s['text']}; }}
.task-card {{ background:{s['card']}; border-left:6px solid {s['primary']};
    border-radius:{s['radius']}px; padding:12px 16px; margin-bottom:10px; }}
.stProgress>div>div>div>div {{ background:{s['primary']}; }}
.data-table {{ width:100%; border-collapse:collapse; font-size:.9rem; }}
.data-table th {{ background:{s['card']}; text-align:left; padding:6px 10px; }}
.data-table td {{ padding:6px 10px; border-bottom:1px solid {s['text']}22; }}
.legend {{ font-size:.85rem; margin-bottom:6px; }}
.legend .dot {{ display:inline-block; width:10px; height:10px; border-radius:50%; margin:0 4px 0 12px; }}
.bar-row {{ display:flex; align-items:center; gap:10px; margin:6px 0; }}
.bar-label {{ width:90px; font-size:.8rem; flex-shrink:0; }}
.bar-group {{ flex:1; }}
.bar-track {{ display:flex; align-items:center; gap:6px; height:14px; margin:2px 0; }}
.bar {{ height:12px; border-radius:6px; min-width:2px; }}
.bar-val {{ font-size:.75rem; }}
</style>""", unsafe_allow_html=True)


# ------------------------------------------------------------- task logic
def today_str():
    return date.today().isoformat()


def hhmm():
    return datetime.now().strftime("%H:%M")


def today_habits(d):
    return [h for h in d["habits"] if h["date"] == today_str()]


def habit_names(d):
    return sorted({h["name"] for h in d["habits"]})


def new_habit(d, name, start, end, repeat, alarm_audio=None):
    return {"id": max((h["id"] for h in d["habits"]), default=0) + 1, "name": name,
            "date": today_str(), "start": start, "end": end, "repeat": repeat,
            "alarm_audio": alarm_audio, "completed": False, "completed_time": None,
            "proof_image": None, "proof_size_kb": None}


def add_repeating_habits(d):
    """Copy 'repeat every day' tasks into today if they are missing."""
    have = {h["name"].lower() for h in today_habits(d)}
    latest = {h["name"].lower(): h for h in d["habits"] if h.get("repeat")}
    added = False
    for key, h in latest.items():
        if key not in have and h["date"] < today_str():
            d["habits"].append(new_habit(d, h["name"], h["start"], h["end"], True, h.get("alarm_audio")))
            added = True
    return added


def task_state(h, now):
    if h["completed"]:
        return "Completed ✅"
    if now < h["start"]:
        return "Upcoming 🕒"
    return "In progress ▶️" if now < h["end"] else "Overdue ⚠️"


def task_card(h, now):
    extra = f" · done at {h['completed_time']}" if h["completed"] else ""
    if h.get("alarm_audio"):
        extra += " · 🎙️ voice alarm"
    st.markdown(f"<div class='task-card'><b>{html.escape(h['name'])}</b><br>"
                f"{h['start']} → {h['end']} · {task_state(h, now)}{extra}</div>",
                unsafe_allow_html=True)


def save_file(user, upload, root, default_ext):
    """Save an uploaded file under <root>/<user>/ with a unique name; return the path (str)."""
    folder = os.path.join(root, user)
    os.makedirs(folder, exist_ok=True)
    ext = os.path.splitext(upload.name)[1].lower() or default_ext
    path = os.path.join(folder, f"{today_str()}_{uuid.uuid4().hex[:8]}{ext}")
    with open(path, "wb") as f:
        f.write(upload.getbuffer())
    return path


def streak(d, name):
    days = {h["date"] for h in d["habits"] if h["name"].lower() == name.lower() and h["completed"]}
    day = date.today()
    if day.isoformat() not in days:  # today not done yet -> streak still alive from yesterday
        day -= timedelta(days=1)
    count = 0
    while day.isoformat() in days:
        count += 1
        day -= timedelta(days=1)
    return count


# ------------------------------------------- tables and charts (no pandas)
def show_table(records):
    """Draw a list of dicts as an HTML table."""
    if not records:
        return
    cols = list(records[0].keys())
    head = "".join(f"<th>{html.escape(str(c))}</th>" for c in cols)
    body = "".join("<tr>" + "".join(f"<td>{html.escape(str(r.get(c, '')))}</td>" for c in cols) + "</tr>"
                   for r in records)
    st.markdown(f"<div style='overflow-x:auto'><table class='data-table'><tr>{head}</tr>{body}</table></div>",
                unsafe_allow_html=True)


def draw_chart(labels, series):
    """Horizontal bar chart. labels: list of str, series: dict name -> list of numbers."""
    peak = max((v for vals in series.values() for v in vals), default=0) or 1
    shades = ["var(--primary)", "#9AA5B1"]
    legend = "".join(f"<span class='dot' style='background:{shades[i % 2]}'></span>{html.escape(name)}"
                     for i, name in enumerate(series))
    rows = ""
    for i, label in enumerate(labels):
        bars = ""
        for j, vals in enumerate(series.values()):
            bars += (f"<div class='bar-track'><div class='bar' style='width:{vals[i] / peak * 100:.1f}%;"
                     f"background:{shades[j % 2]}'></div><span class='bar-val'>{vals[i]:g}</span></div>")
        rows += f"<div class='bar-row'><span class='bar-label'>{html.escape(label)}</span><div class='bar-group'>{bars}</div></div>"
    st.markdown(f"<div class='legend'>{legend}</div>{rows}", unsafe_allow_html=True)


def run_html(code, height):
    """Run a small HTML/JS snippet (used for alarm sound). Newer Streamlit uses st.iframe."""
    if hasattr(st, "iframe"):
        st.iframe(code, height=height)
    else:
        components.html(code, height=height)


# ----------------------------------------------------------------- alerts
AUDIO_MIME = {".wav": "audio/wav", ".mp3": "audio/mpeg", ".ogg": "audio/ogg",
              ".m4a": "audio/mp4", ".webm": "audio/webm"}


def audio_data_uri(path):
    """Read a voice-note file and return it as a data URI string the browser can play."""
    if not path or not os.path.isfile(path):
        return None
    mime = AUDIO_MIME.get(os.path.splitext(path)[1].lower(), "audio/wav")
    with open(path, "rb") as f:
        return f"data:{mime};base64,{base64.b64encode(f.read()).decode()}"


def alert_js(alerts, sound, notify):
    """alerts: list of (message, audio_data_uri_or_None) tuples."""
    items = [{"msg": m, "audio": a} for m, a in alerts]
    return f"""<script>
const items={json.dumps(items)}, sound={str(sound).lower()}, notify={str(notify).lower()};
function beep() {{
  try {{
    const c = new (window.AudioContext || window.webkitAudioContext)();
    [0, 0.25, 0.5].forEach(t => {{
      const o = c.createOscillator(), g = c.createGain();
      o.connect(g); g.connect(c.destination); o.frequency.value = 880; g.gain.value = 0.15;
      o.start(c.currentTime + t); o.stop(c.currentTime + t + 0.15); }});
  }} catch (e) {{}}
}}
items.forEach((it, i) => setTimeout(() => {{
  if (!sound) return;
  if (it.audio) {{ new Audio(it.audio).play().catch(beep); }} else {{ beep(); }}
}}, i * 4000));
try {{ if (notify) {{
  const N = window.parent.Notification || window.Notification;
  if (N.permission === 'granted') items.forEach(it => new N('Life Tracker', {{body: it.msg}}));
}} }} catch (e) {{}}
</script>"""


@st.fragment(run_every=15)
def alert_center():
    """Checks the clock every 15 seconds while the page is open."""
    d = st.session_state.data
    s = d["settings"]
    now = hhmm()
    fired = st.session_state.setdefault("fired", set())  # set: each alert fires only once
    new_alerts = []                                       # list of (message, audio) tuples
    for h in today_habits(d):
        if h["completed"]:
            continue
        if h["start"] <= now < h["end"]:
            st.info(f"▶️ Time to start: **{h['name']}** ({h['start']} - {h['end']})")
            phase, text = "start", f"Start now: {h['name']}"
        elif now >= h["end"]:
            st.warning(f"⏰ Deadline reached - mark as complete: **{h['name']}** (due {h['end']})")
            phase, text = "end", f"Complete your task: {h['name']}"
        else:
            continue
        if h.get("alarm_audio") and os.path.isfile(h["alarm_audio"]):
            st.audio(h["alarm_audio"])  # fallback player if the browser blocks autoplay
        key = f"{h['id']}|{h['date']}|{phase}"
        if key not in fired:
            fired.add(key)
            new_alerts.append((text, audio_data_uri(h.get("alarm_audio"))))
    for text, _ in new_alerts:
        st.toast(text, icon="🔔")
    if new_alerts and (s["sound"] or s["notify"]):
        run_html(alert_js(new_alerts, s["sound"], s["notify"]), 1)


# ------------------------------------------------------------------ pages
def page_dashboard():
    d = st.session_state.data
    habits, now = today_habits(d), hhmm()
    done = sum(h["completed"] for h in habits)
    pct = done / len(habits) if habits else 0
    st.title(f"👋 Hello, {st.session_state.user}")
    st.caption(datetime.now().strftime("%A, %d %B %Y"))
    c1, c2, c3 = st.columns(3)
    c1.metric("Tasks done", f"{done}/{len(habits)}")
    c2.metric("Progress", f"{pct * 100:.0f}%")
    c3.metric("Best current streak", f"{max((streak(d, n) for n in habit_names(d)), default=0)} day(s)")
    st.progress(pct)
    upcoming = sorted((h for h in habits if not h["completed"] and h["start"] > now),
                      key=lambda h: h["start"])
    if upcoming:
        st.info(f"Next task: **{upcoming[0]['name']}** at {upcoming[0]['start']}")
    st.subheader("Today's schedule")
    if not habits:
        st.write("No tasks yet. Add one on the Tasks page.")
    for h in sorted(habits, key=lambda h: h["start"]):
        task_card(h, now)


def page_tasks():
    d, user = st.session_state.data, st.session_state.user
    s = d["settings"]
    st.title("📝 Today's Tasks")
    with st.form("add_task", clear_on_submit=True):
        name = st.text_input("Task / habit name")
        c1, c2 = st.columns(2)
        start = c1.time_input("Start time", value=dtime(9, 0))
        end = c2.time_input("Deadline / finish time", value=dtime(10, 0))
        repeat = st.checkbox("Repeat every day")
        st.markdown("**Alarm voice note (optional)**: your own voice, played when the task "
                    "starts and at the deadline. Without one, a beep is used.")
        recorded = st.audio_input("Record a voice note")
        uploaded = st.file_uploader("...or upload an audio file", type=[e[1:] for e in AUDIO_MIME])
        if st.form_submit_button("Add task"):
            if not name.strip():
                st.error("Task name cannot be empty.")
            elif end <= start:
                st.error("Deadline must be after the start time.")
            else:
                voice = recorded if recorded is not None else uploaded
                audio_path = save_file(user, voice, AUDIO_DIR, ".wav") if voice is not None else None
                d["habits"].append(new_habit(d, name.strip(), start.strftime("%H:%M"),
                                             end.strftime("%H:%M"), repeat, audio_path))
                save()
                st.success("Task added. You will be alerted at the start time and at the deadline.")
    now = hhmm()
    for h in sorted(today_habits(d), key=lambda h: h["start"]):
        task_card(h, now)
        if not h["completed"]:
            with st.expander(f"Complete or delete: {h['name']}"):
                up = st.file_uploader("Proof photo (optional)", type=["png", "jpg", "jpeg", "webp"], key=f"up{h['id']}")
                a, b = st.columns(2)
                if a.button("✅ Mark as done", key=f"done{h['id']}"):
                    valid = True
                    if up is not None:
                        try:
                            Image.open(up).verify()  # confirms it is a real image
                            up.seek(0)
                        except Exception:
                            st.error("That file is not a valid image.")
                            valid = False
                    if valid:
                        if up is not None:
                            h["proof_image"] = save_file(user, up, IMG_DIR, ".png")
                            h["proof_size_kb"] = round(up.size / 1024, 1)
                        h["completed"] = True
                        h["completed_time"] = datetime.now().strftime("%H:%M:%S")
                        save()
                        st.rerun()
                if b.button("Delete (stops repeating)", key=f"del{h['id']}"):
                    for x in d["habits"]:
                        if x["name"].lower() == h["name"].lower():
                            x["repeat"] = False
                    d["habits"].remove(h)
                    save()
                    st.rerun()
        elif h["proof_image"] and os.path.isfile(h["proof_image"]):
            st.image(h["proof_image"], width=180, caption=f"Proof ({h['proof_size_kb']} KB)")


def show_history(records, columns):
    """records: list of dicts (one per day). Shows the last 14 days as a chart and all days as a table."""
    if not records:
        st.info("No records yet.")
        return
    recent = records[-14:]
    draw_chart([r["date"] for r in recent], {c: [r[c] for r in recent] for c in columns})
    show_table(records[::-1])  # newest first


def page_health():
    d = st.session_state.data
    st.title("💧 Health Tracker")
    with st.form("health"):
        c1, c2 = st.columns(2)
        water = c1.number_input("Water (glasses)", 0.0, 30.0, 8.0, 0.5)
        sleep = c2.number_input("Sleep (hours)", 0.0, 24.0, 7.0, 0.5)
        exercise = st.selectbox("Exercise done?", ["Yes", "No"])
        notes = st.text_area("Notes")
        if st.form_submit_button("Save today's record"):
            upsert(d, "health", {"date": today_str(), "water": water, "sleep": sleep,
                                 "exercise": exercise, "notes": notes})
            st.success("Health record saved.")
    show_history(d["health"], ["water", "sleep"])


def skincare_percent(records):
    return sum(r["morning"] + r["night"] for r in records) / (2 * len(records)) * 100


def page_skincare():
    d = st.session_state.data
    st.title("🧴 Skincare Tracker")
    with st.form("skin"):
        morning = st.checkbox("Morning routine done")
        night = st.checkbox("Night routine done")
        if st.form_submit_button("Save today's record"):
            upsert(d, "skincare", {"date": today_str(), "morning": morning, "night": night})
            st.success("Skincare record saved.")
    if d["skincare"]:
        st.metric("Routine completion", f"{skincare_percent(d['skincare']):.0f}%",
                  f"{len(d['skincare'])} day(s) tracked", delta_color="off")
        show_table(d["skincare"][::-1])
    else:
        st.info("No records yet.")


def page_screen():
    d = st.session_state.data
    st.title("📱 Screen Time")
    last_limit = d["screen_time"][-1]["limit"] if d["screen_time"] else 180.0
    with st.form("screen"):
        cols = st.columns(len(APPS))
        mins = {a.lower(): c.number_input(f"{a} (min)", 0.0, 1440.0, 0.0, 5.0)
                for a, c in zip(APPS, cols)}
        limit = st.number_input("Daily limit (minutes)", 0.0, 1440.0, float(last_limit), 10.0)
        if st.form_submit_button("Save today's record"):
            total = sum(mins.values())
            upsert(d, "screen_time", {"date": today_str(), **mins, "total": total, "limit": limit})
            if total <= limit:
                st.success(f"{total:.0f} min used - within your {limit:.0f} min limit.")
            else:
                st.error(f"Limit exceeded by {total - limit:.0f} minutes.")
    show_history(d["screen_time"], ["total", "limit"])


def page_report():
    d = st.session_state.data
    st.title("📊 Streaks & Report")
    st.subheader("Habit streaks")
    for n in habit_names(d) or []:
        st.write(f"**{n}**: {streak(d, n)} day(s)")
    if not d["habits"]:
        st.info("No habits yet.")
    st.subheader("Last 7 days")
    rows = []
    for i in range(6, -1, -1):
        day = (date.today() - timedelta(days=i)).isoformat()
        hs = [h for h in d["habits"] if h["date"] == day]
        rows.append({"date": day, "completed": sum(h["completed"] for h in hs), "planned": len(hs)})
    draw_chart([r["date"] for r in rows],
               {"completed": [r["completed"] for r in rows], "planned": [r["planned"] for r in rows]})
    st.subheader("Summary")
    c1, c2, c3 = st.columns(3)
    if d["health"]:
        recent = d["health"][-7:]
        c1.metric("Avg water (glasses)", f"{sum(r['water'] for r in recent) / len(recent):.1f}")
        c1.metric("Avg sleep (hours)", f"{sum(r['sleep'] for r in recent) / len(recent):.1f}")
    if d["skincare"]:
        c2.metric("Skincare completion", f"{skincare_percent(d['skincare']):.0f}%")
    if d["screen_time"]:
        last = d["screen_time"][-1]
        c3.metric("Latest screen time", f"{last['total']:.0f} min",
                  "within limit" if last["total"] <= last["limit"] else "limit exceeded",
                  delta_color="off")


def page_settings():
    d = st.session_state.data
    s = d["settings"]
    st.title("🎨 Settings")
    st.caption("These settings belong to your account only.")
    with st.form("settings"):
        st.subheader("Theme")
        options = list(PRESETS) + ["Custom"]
        preset = st.selectbox("Preset", options,
                              index=options.index(s["preset"]) if s["preset"] in options else len(options) - 1)
        c1, c2, c3, c4 = st.columns(4)
        bg = c1.color_picker("Background", s["bg"])
        card = c2.color_picker("Cards / sidebar", s["card"])
        text = c3.color_picker("Text", s["text"])
        primary = c4.color_picker("Accent / buttons", s["primary"])
        fonts = list(FONTS)
        font_label = st.selectbox("Font", fonts,
                                  index=list(FONTS.values()).index(s["font"]) if s["font"] in FONTS.values() else 0)
        radius = st.slider("Corner roundness (px)", 0, 24, int(s["radius"]))
        st.subheader("Alerts")
        sound = st.checkbox("Play alarm (your voice note, or a beep if none) when a task starts or is due", s["sound"])
        notify = st.checkbox("Show browser notifications", s["notify"])
        if st.form_submit_button("Save settings"):
            picked = {"bg": bg, "card": card, "text": text, "primary": primary}
            colors = dict(PRESETS[preset]) if preset in PRESETS and preset != s["preset"] else picked
            colors = {k: v.upper() for k, v in colors.items()}
            name = next((p for p, v in PRESETS.items() if v == colors), "Custom")
            s.update(colors, preset=name, font=FONTS[font_label], sound=sound, notify=notify, radius=radius)
            save()
            st.rerun()
    st.subheader("Browser notifications")
    st.caption("Click once and choose 'Allow' so alerts can appear even when the tab is in the background.")
    run_html("""<button style="padding:8px 14px;border-radius:8px;border:0;cursor:pointer"
        onclick="(window.parent.Notification||Notification).requestPermission().then(p=>this.innerText='Permission: '+p)">
        Enable browser notifications</button>""", 50)


def page_concepts():
    d = st.session_state.data
    st.title("🐍 Python Concepts Used")
    rows = [
        ("list", "d['habits'], d['health'], d['skincare'], d['screen_time']", "ordered collection of records"),
        ("dict", "every habit / health / skincare record, the settings", "key-value record"),
        ("tuple", "alerts as (message, audio) pairs; (start, end) windows", "fixed pair that is not changed"),
        ("set", "fired alerts, unique habit names, completed dates", "no duplicates, fast lookup"),
        ("str", "name, 'HH:MM' times, file paths", "text"),
        ("int / float", "id, radius / water, sleep, minutes", "whole and decimal numbers"),
        ("bool", "completed, repeat", "True / False"),
        ("None", "proof_image before a photo is uploaded", "'no value yet'"),
    ]
    show_table([{"Concept": c, "Where used": w, "Meaning": m} for c, w, m in rows])
    if d["habits"]:
        st.subheader("Live example: your latest task record")
        sample = d["habits"][-1]
        st.json(sample)
        show_table([{"Field": k, "Python type": type(v).__name__, "Value": repr(v)}
                    for k, v in sample.items()])


PAGES = {
    "🏠 Dashboard": page_dashboard,
    "📝 Tasks": page_tasks,
    "💧 Health": page_health,
    "🧴 Skincare": page_skincare,
    "📱 Screen Time": page_screen,
    "📊 Streaks & Report": page_report,
    "🐍 Python Concepts": page_concepts,
    "🎨 Settings": page_settings,
}


def main():
    st.set_page_config(page_title="Life Tracker", page_icon="✅", layout="wide")
    if "user" not in st.session_state:
        auth_screen()
        return
    d = st.session_state.data
    if add_repeating_habits(d):
        save()
    apply_theme(d["settings"])
    st.sidebar.title("Life Tracker")
    st.sidebar.write(f"Logged in as **{st.session_state.user}**")
    page = st.sidebar.radio("Go to", list(PAGES), label_visibility="collapsed")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()
    alert_center()
    PAGES[page]()


main()
