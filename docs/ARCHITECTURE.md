# ディレクトリ構造

atc/
├─ __init__.py
├─ __main__.py
├─ cli.py
├─ commands/
│  ├─ __init__.py
│  ├─ contest.py
│  ├─ run.py
│  ├─ watch.py
│  ├─ refresh.py
│  ├─ template.py
│  ├─ stress.py
│  ├─ manual.py
│  ├─ doctor.py
│  └─ visual.py
│
├─ core/
│  ├─ __init__.py
│  ├─ runner.py
│  ├─ config.py
│  ├─ contest.py
│  ├─ atcoder.py
│  ├─ samples.py
│  ├─ metadata.py
│  ├─ paths.py
│  ├─ problems.py
│  └─ templates.py
│
├─ ui/
│  ├─ __init__.py
│  ├─ console.py
│  ├─ run_view.py
│  ├─ watch_view.py
│  ├─ doctor_view.py
│  ├─ refresh_view.py
│  └─ stress_view.py
│
└─ models.py