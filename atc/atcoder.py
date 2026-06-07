from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import List, Optional
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from .models import AtCoderProblem


# --- Constants ---
ATCODER_BASE_URL = "https://atcoder.jp"


# --- URL helpers ---
def build_fallback_task_url(contest_id: str, problem_index: str) -> str:
    return f"{ATCODER_BASE_URL}/contests/{contest_id}/tasks/{contest_id}_{problem_index.lower()}"


# --- Internal HTML parse models ---
@dataclass
class _ParsedLink:
    href: str
    text_parts: List[str] = field(default_factory=list)


@dataclass
class _ParsedCell:
    tag: str
    text_parts: List[str] = field(default_factory=list)
    links: List[_ParsedLink] = field(default_factory=list)


@dataclass
class _ParsedRow:
    section: str
    cells: List[_ParsedCell] = field(default_factory=list)


@dataclass
class _ParsedTable:
    section: str = ""
    thead_rows: List[_ParsedRow] = field(default_factory=list)
    tbody_rows: List[_ParsedRow] = field(default_factory=list)
    other_rows: List[_ParsedRow] = field(default_factory=list)
    current_row: Optional[_ParsedRow] = None
    current_cell: Optional[_ParsedCell] = None


# --- Text helpers ---
def _clean_text(text: str) -> str:
    return " ".join(text.replace("\xa0", " ").split())


def _cell_text(cell: _ParsedCell) -> str:
    return _clean_text("".join(cell.text_parts))


def _link_text(link: _ParsedLink) -> str:
    return _clean_text("".join(link.text_parts))


# --- HTML parser ---
class _AtCoderTasksHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables: List[_ParsedTable] = []
        self._table_stack: List[_ParsedTable] = []
        self._link_stack: List[Optional[_ParsedLink]] = []

    @property
    def _current_table(self) -> Optional[_ParsedTable]:
        if not self._table_stack:
            return None
        return self._table_stack[-1]

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attrs_map = dict(attrs)

        if tag == "table":
            self._table_stack.append(_ParsedTable())
            return

        table = self._current_table
        if table is None:
            return

        if tag in {"thead", "tbody"}:
            table.section = tag
            return

        if tag == "tr":
            table.current_row = _ParsedRow(section=table.section)
            return

        if tag in {"th", "td"} and table.current_row is not None:
            table.current_cell = _ParsedCell(tag=tag)
            return

        if tag == "a" and table.current_cell is not None:
            href = attrs_map.get("href")
            link = _ParsedLink(href=href) if href else None
            if link is not None:
                table.current_cell.links.append(link)
            self._link_stack.append(link)

    def handle_endtag(self, tag):
        tag = tag.lower()
        table = self._current_table

        if tag == "a":
            if self._link_stack:
                self._link_stack.pop()
            return

        if table is None:
            return

        if tag in {"th", "td"}:
            if table.current_row is not None and table.current_cell is not None:
                table.current_row.cells.append(table.current_cell)
            table.current_cell = None
            return

        if tag == "tr":
            row = table.current_row
            if row is not None:
                if row.section == "thead":
                    table.thead_rows.append(row)
                elif row.section == "tbody":
                    table.tbody_rows.append(row)
                else:
                    table.other_rows.append(row)
            table.current_row = None
            return

        if tag in {"thead", "tbody"}:
            if table.section == tag:
                table.section = ""
            return

        if tag == "table":
            finished = self._table_stack.pop()
            self.tables.append(finished)

    def handle_data(self, data):
        table = self._current_table
        if table is None or table.current_cell is None:
            return

        table.current_cell.text_parts.append(data)
        if self._link_stack and self._link_stack[-1] is not None:
            self._link_stack[-1].text_parts.append(data)


# --- Parser helpers ---
def _has_problem_name_header(table: _ParsedTable) -> bool:
    for row in table.thead_rows:
        for cell in row.cells:
            header = _cell_text(cell)
            if "問題名" in header or "Task Name" in header:
                return True
    return False


def _first_link(cell: _ParsedCell) -> Optional[_ParsedLink]:
    for link in cell.links:
        if link.href:
            return link
    return None


def _task_id_from_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    return path.split("/")[-1] if path else ""


# --- Public parse API ---
def parse_atcoder_tasks_html(html: str, base_url: str = ATCODER_BASE_URL) -> List[AtCoderProblem]:
    parser = _AtCoderTasksHTMLParser()
    parser.feed(html)
    parser.close()

    problems: List[AtCoderProblem] = []
    for table in parser.tables:
        if not _has_problem_name_header(table):
            continue

        for row in table.tbody_rows:
            if len(row.cells) < 2:
                continue

            index_link = _first_link(row.cells[0])
            title_link = _first_link(row.cells[1])
            if index_link is None:
                continue

            href = index_link.href
            if not href:
                continue

            title = _link_text(title_link) if title_link is not None else ""
            url = urljoin(base_url, href)
            time_limit = _cell_text(row.cells[2]) if len(row.cells) >= 3 else None
            memory_limit = _cell_text(row.cells[3]) if len(row.cells) >= 4 else None
            problems.append(
                AtCoderProblem(
                    index=_link_text(index_link) or _cell_text(row.cells[0]),
                    title=title or _cell_text(row.cells[1]),
                    url=url,
                    task_id=_task_id_from_url(url),
                    time_limit=time_limit or None,
                    memory_limit=memory_limit or None,
                )
            )

    return problems


# --- Fetch API ---
def fetch_atcoder_tasks_html(
    contest_id: str,
    base_url: str = ATCODER_BASE_URL,
    timeout: float = 15.0,
) -> str:
    url = urljoin(base_url, f"/contests/{contest_id}/tasks")
    request = Request(
        url,
        headers={
            "User-Agent": "atc/0.1",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        body = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
    return body.decode(charset, errors="replace")


def fetch_atcoder_tasks(
    contest_id: str,
    base_url: str = ATCODER_BASE_URL,
    timeout: float = 15.0,
) -> List[AtCoderProblem]:
    html = fetch_atcoder_tasks_html(contest_id, base_url=base_url, timeout=timeout)
    return parse_atcoder_tasks_html(html, base_url=base_url)