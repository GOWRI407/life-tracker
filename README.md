# Personal Life Tracker (Streamlit)

## Run
```
pip install -r requirements.txt
streamlit run app.py
```

## How it works
```
Python  ->  Streamlit  ->  JSON files  ->  Lists + Dictionaries
(logic)     (web pages)    (storage)       (data in memory)
```
- Every record (habit, health, skincare, screen time) is a **dict**; each category is a **list** of dicts.
- `data/<user>/tracker.json` is read with `json.load` into those lists/dicts and written back with `json.dump`.
- No pandas: tables and bar charts are drawn from plain lists / dicts with small helper functions (`show_table`, `draw_chart`).

## Features
- Multi-user accounts; every user has their own data, photos, voice notes and **theme**.
- **Theme customization**: 6 presets, 4 colour pickers, 4 fonts, corner roundness.
- Tasks with **start time** and **deadline**. At both moments the app shows a banner and popup and plays the alarm.
- **Voice-note alarm**: record your own voice (or upload an audio file) per task. It plays at the start time and at the deadline. No voice note = beep.
- **Proof image to complete a task**: the image is checked to be a real image, saved in `images/<user>/`, and shown on the task. Can be switched to optional in Settings.
- Daily repeat tasks, streaks, health / skincare / screen-time trackers with charts.

## Python concepts (also shown live on the "Python Concepts" page)
| Concept | Where used |
|---|---|
| list | `habits`, `health`, `skincare`, `screen_time` records |
| dict | each record, user settings, `PRESETS`, `FONTS`, `PAGES` |
| tuple | alerts `(message, audio)`, sorting keys |
| set | `fired` alerts, unique habit names, completed dates |
| str / int / float / bool / None | names and times / id / water, sleep / completed / proof_image |
| functions, f-strings, loops, try/except, file I/O, JSON | throughout `app.py` |

No AI, machine learning or deep learning is used.

## Notes
- Alerts are checked every 15 s **while the app page is open**.
- Browsers may block autoplay audio until you click on the page once; a small audio player is also shown in the banner.
