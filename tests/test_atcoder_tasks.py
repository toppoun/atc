from atc.atcoder import build_fallback_task_url, parse_atcoder_tasks_html


ADT_TASKS_HTML = """
<html>
  <body>
    <ul class="dropdown-menu">
      <li><a href="/contests/adt_easy_20260525_1/tasks/abc230_a">A - duplicate nav link</a></li>
      <li><a href="/contests/adt_easy_20260525_1/tasks/abc262_a">B - duplicate nav link</a></li>
    </ul>
    <div class="panel panel-default table-responsive">
      <table class="table table-bordered table-striped">
        <thead>
          <tr>
            <th></th>
            <th>問題名</th>
            <th>実行時間制限</th>
            <th>メモリ制限</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td class="text-center no-break"><a href="/contests/adt_easy_20260525_1/tasks/abc230_a">A</a></td>
            <td><a href="/contests/adt_easy_20260525_1/tasks/abc230_a">AtCoder Quiz 3</a></td>
            <td class="text-right">2 sec</td>
            <td class="text-right">1024 MiB</td>
          </tr>
          <tr>
            <td class="text-center no-break"><a href="/contests/adt_easy_20260525_1/tasks/abc262_a">B</a></td>
            <td><a href="/contests/adt_easy_20260525_1/tasks/abc262_a">World Cup</a></td>
            <td class="text-right">2 sec</td>
            <td class="text-right">1024 MiB</td>
          </tr>
          <tr>
            <td class="text-center no-break"><a href="/contests/adt_easy_20260525_1/tasks/abc362_b">C</a></td>
            <td><a href="/contests/adt_easy_20260525_1/tasks/abc362_b">Right Triangle</a></td>
            <td class="text-right">2 sec</td>
            <td class="text-right">1024 MiB</td>
          </tr>
          <tr>
            <td class="text-center no-break"><a href="/contests/adt_easy_20260525_1/tasks/abc274_b">D</a></td>
            <td><a href="/contests/adt_easy_20260525_1/tasks/abc274_b">Line Sensor</a></td>
            <td class="text-right">2 sec</td>
            <td class="text-right">1024 MiB</td>
          </tr>
          <tr>
            <td class="text-center no-break"><a href="/contests/adt_easy_20260525_1/tasks/abc372_c">E</a></td>
            <td><a href="/contests/adt_easy_20260525_1/tasks/abc372_c">Count ABC Again</a></td>
            <td class="text-right">2 sec</td>
            <td class="text-right">1024 MiB</td>
          </tr>
        </tbody>
      </table>
    </div>
  </body>
</html>
"""


ABC_TASKS_HTML = """
<html>
  <body>
    <div class="navbar">
      <a href="/contests/abc460/tasks/abc460_a">A - duplicate nav link</a>
      <a href="/contests/abc460/tasks/abc460_b">B - duplicate nav link</a>
      <a href="/contests/abc460/tasks/abc460_c">C - duplicate nav link</a>
    </div>
    <div class="panel panel-default table-responsive">
      <table class="table table-bordered table-striped">
        <thead>
          <tr>
            <th></th>
            <th>問題名</th>
            <th>実行時間制限</th>
            <th>メモリ制限</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><a href="/contests/abc460/tasks/abc460_a">A</a></td>
            <td><span class="difficulty-label"></span><a href="/contests/abc460/tasks/abc460_a" class="difficulty-grey">Mod While Positive</a></td>
            <td>2 sec</td>
            <td>1024 MiB</td>
          </tr>
          <tr>
            <td><a href="/contests/abc460/tasks/abc460_b">B</a></td>
            <td><span class="difficulty-label"></span><a href="/contests/abc460/tasks/abc460_b" class="difficulty-grey">Two Rings</a></td>
            <td>2 sec</td>
            <td>1024 MiB</td>
          </tr>
          <tr>
            <td><a href="/contests/abc460/tasks/abc460_c">C</a></td>
            <td><a href="/contests/abc460/tasks/abc460_c">Sushi</a></td>
            <td>2 sec</td>
            <td>1024 MiB</td>
          </tr>
          <tr>
            <td><a href="/contests/abc460/tasks/abc460_d">D</a></td>
            <td><a href="/contests/abc460/tasks/abc460_d">Repeatedly Repainting</a></td>
            <td>2 sec</td>
            <td>1024 MiB</td>
          </tr>
          <tr>
            <td><a href="/contests/abc460/tasks/abc460_e">E</a></td>
            <td><a href="/contests/abc460/tasks/abc460_e">x + y ≡ x + y</a></td>
            <td>2 sec</td>
            <td>1024 MiB</td>
          </tr>
          <tr>
            <td><a href="/contests/abc460/tasks/abc460_f">F</a></td>
            <td><a href="/contests/abc460/tasks/abc460_f">Farthest Pair Query</a></td>
            <td>2 sec</td>
            <td>1024 MiB</td>
          </tr>
          <tr>
            <td><a href="/contests/abc460/tasks/abc460_g">G</a></td>
            <td><a href="/contests/abc460/tasks/abc460_g">Vertex Flip Query</a></td>
            <td>2 sec</td>
            <td>1024 MiB</td>
          </tr>
        </tbody>
      </table>
    </div>
  </body>
</html>
"""


def test_parse_atcoder_tasks_html_adt_uses_problem_table_only():
    problems = parse_atcoder_tasks_html(ADT_TASKS_HTML)

    assert len(problems) == 5
    assert problems[0].index == "A"
    assert problems[0].task_id == "abc230_a"
    assert problems[0].title == "AtCoder Quiz 3"
    assert [(problem.index, problem.task_id, problem.title) for problem in problems] == [
        ("A", "abc230_a", "AtCoder Quiz 3"),
        ("B", "abc262_a", "World Cup"),
        ("C", "abc362_b", "Right Triangle"),
        ("D", "abc274_b", "Line Sensor"),
        ("E", "abc372_c", "Count ABC Again"),
    ]
    assert "/contests/adt_easy_20260525_1/tasks/abc230_a" in problems[0].url


def test_parse_atcoder_tasks_html_abc_uses_problem_table_only():
    problems = parse_atcoder_tasks_html(ABC_TASKS_HTML)

    assert len(problems) == 7
    assert problems[0].index == "A"
    assert problems[0].task_id == "abc460_a"
    assert problems[0].title == "Mod While Positive"
    assert [(problem.index, problem.task_id, problem.title) for problem in problems] == [
        ("A", "abc460_a", "Mod While Positive"),
        ("B", "abc460_b", "Two Rings"),
        ("C", "abc460_c", "Sushi"),
        ("D", "abc460_d", "Repeatedly Repainting"),
        ("E", "abc460_e", "x + y ≡ x + y"),
        ("F", "abc460_f", "Farthest Pair Query"),
        ("G", "abc460_g", "Vertex Flip Query"),
    ]


def test_parse_atcoder_tasks_html_accepts_english_task_name_header():
    problems = parse_atcoder_tasks_html(ABC_TASKS_HTML.replace("問題名", "Task Name"))

    assert len(problems) == 7
    assert problems[0].index == "A"
    assert problems[0].task_id == "abc460_a"
    assert problems[0].title == "Mod While Positive"


def test_build_fallback_task_url_uses_contest_problem_pattern():
    assert build_fallback_task_url("abc460", "A") == "https://atcoder.jp/contests/abc460/tasks/abc460_a"
    assert build_fallback_task_url("abc460", "B") == "https://atcoder.jp/contests/abc460/tasks/abc460_b"


def test_build_fallback_task_url_keeps_existing_adt_fallback_shape():
    assert (
        build_fallback_task_url("adt_easy_20260525_1", "A")
        == "https://atcoder.jp/contests/adt_easy_20260525_1/tasks/adt_easy_20260525_1_a"
    )
