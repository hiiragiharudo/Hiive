"""靶场初始化与连通性检查。

本机的三个靶场（sqli-labs / DVWA / Pikachu）跑在 XAMPP 上
（Apache 2.4.58 + PHP 8.2.12 + MariaDB 10.4.32）。
**本机 3306 被独立安装的 MySQL 8.0 占用**，所以 XAMPP 的 MariaDB 走 **3307**，
并通过 `php.ini` 的 `mysqli.default_port=3307` 让所有靶场自动连上。

用法::

    .venv/Scripts/python eval/ranges/setup_ranges.py            # 初始化 + 检查
    .venv/Scripts/python eval/ranges/setup_ranges.py --check    # 只检查

## 各靶场的初始化方式（都不一样）

| 靶场 | 数据库 | 初始化方式 |
|---|---|---|
| sqli-labs | `security` | 导入仓库自带 `sql-lab.sql` |
| Pikachu | `pikachu` | POST `install.php`（自建库建表 + 默认数据） |
| DVWA | `dvwa` | POST `setup.php`，**必须先带 CSRF token**（否则静默失败） |

> DVWA 的 `setup.php` 会调 `checkToken()`。不带 token 直接 POST 会**静默返回 200
> 但什么都不做**——这是本脚本存在的主要理由。
"""

from __future__ import annotations

import argparse
import html
import re
import subprocess
import sys
from pathlib import Path

import httpx

XAMPP = Path("H:/XAMPP")
MYSQL = XAMPP / "mysql" / "bin" / "mysql.exe"
DB_PORT = "3307"
BASE = "http://localhost"

#: 需要存在的数据库 → 说明
EXPECTED_DBS = {
    "security": "sqli-labs（Less-1..Less-65）",
    "pikachu": "Pikachu（SQL 注入 / XSS / 文件包含等）",
    "dvwa": "DVWA（15 个模块）",
}

#: 靶场入口 → (路径, 期望状态码)
RANGES = {
    "sqli-labs": "/sqli-labs/",
    "DVWA": "/DVWA/",
    "pikachu": "/pikachu/",
}

_TAG = re.compile(r"<[^>]+>")
_TOKEN_RE = re.compile(r"""name=["']user_token["']\s+value=["']([^"']+)["']""")


def _text(s: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", _TAG.sub(" ", s)))


def mysql(sql: str) -> tuple[int, str]:
    """执行 SQL，返回 (退出码, 输出)。"""
    p = subprocess.run(
        [str(MYSQL), "-u", "root", "-P", DB_PORT, "-h", "127.0.0.1", "-e", sql],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def db_tables() -> dict[str, int]:
    rc, out = mysql(
        "SELECT table_schema, COUNT(*) FROM information_schema.tables "
        "WHERE table_schema NOT IN ('information_schema','performance_schema',"
        "'mysql','phpmyadmin') GROUP BY table_schema;"
    )
    counts: dict[str, int] = {}
    if rc != 0:
        return counts
    for line in out.splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) == 2 and parts[1].strip().isdigit():
            counts[parts[0].strip()] = int(parts[1])
    return counts


# --------------------------------------------------------------------- 初始化


def init_sqli_labs() -> str:
    sql_file = XAMPP / "htdocs" / "sqli-labs" / "sql-lab.sql"
    if not sql_file.exists():
        return f"✗ 找不到 {sql_file}"
    rc, out = mysql(f"SOURCE {sql_file.as_posix()};")
    if rc != 0:
        return f"✗ 导入失败: {out[:200]}"
    return "✓ 已导入 sql-lab.sql"


def init_pikachu(client: httpx.Client) -> str:
    r = client.post(f"{BASE}/pikachu/install.php",
                    data={"submit": "安装/初始化"})
    t = _text(r.text)
    if "创建数据库数据成功" in t:
        return "✓ 初始化成功"
    if "失败" in t:
        i = t.find("失败")
        return f"✗ {t[max(0, i - 60):i + 80]}"
    return f"✗ 未见成功标志（HTTP {r.status_code}）"


def init_dvwa(client: httpx.Client) -> str:
    """DVWA 必须先取 CSRF token —— 不带 token 的 POST 会静默失败。

    **成功判定必须查数据库，不能看页面文本**：DVWA 的 setup 页
    无论成功与否都会渲染"Click on the 'Create / Reset Database' button"
    那句引导语（它是静态 HTML），早先按文本判断会误报失败。
    """
    r = client.get(f"{BASE}/DVWA/setup.php")
    m = _TOKEN_RE.search(r.text)
    if not m:
        return "✗ 未能从 setup.php 取到 user_token（页面结构可能已变）"
    token = m.group(1)

    client.post(f"{BASE}/DVWA/setup.php",
                data={"create_db": "Create / Reset Database", "user_token": token})

    n = db_tables().get("dvwa", 0)
    if n > 0:
        return f"✓ 初始化成功（dvwa 库 {n} 张表）"
    return "✗ 库仍未创建 —— 检查 config/config.inc.php 的凭据与 db_port"


# --------------------------------------------------------------------- 检查


def check(client: httpx.Client, verbose: bool = True) -> bool:
    ok = True
    counts = db_tables()

    print("\n" + "=" * 74)
    print("数据库")
    print("=" * 74)
    for db, desc in EXPECTED_DBS.items():
        n = counts.get(db, 0)
        mark = "✓" if n > 0 else "✗"
        if n == 0:
            ok = False
        print(f"  {mark} {db:<12} {n:>3} 张表   {desc}")

    print("\n" + "=" * 74)
    print("靶场可达性")
    print("=" * 74)
    for name, path in RANGES.items():
        try:
            r = client.get(f"{BASE}{path}")
            body = _text(r.text)
            # DVWA 未初始化时会显示 setup 引导
            hint = ""
            if name == "DVWA" and "DVWA Setup" in body:
                hint = "  ⚠ 尚未初始化（显示 Setup 页）"
                ok = False
            print(f"  ✓ {name:<11} HTTP {r.status_code}  {len(r.content):>6} bytes{hint}")
        except httpx.HTTPError as e:
            ok = False
            print(f"  ✗ {name:<11} {type(e).__name__}: {e}")

    if verbose:
        print("\n" + "=" * 74)
        print("关键端点抽检（这些是技能要打的入口）")
        print("=" * 74)
        probes = [
            ("sqli-labs Less-1 (GET 注入)", "/sqli-labs/Less-1/?id=1"),
            ("sqli-labs Less-11 (POST 注入)", "/sqli-labs/Less-11/"),
            ("DVWA 登录页", "/DVWA/login.php"),
            ("Pikachu SQL 注入", "/pikachu/vul/sqli/sqli_str.php?name=vince&submit=查询"),
            ("Pikachu 反射型 XSS", "/pikachu/vul/xss/xss_reflected_get.php?message=hiive&submit=submit"),
        ]
        for label, path in probes:
            try:
                r = client.get(f"{BASE}{path}")
                print(f"  {r.status_code}  {label:<34} {path}")
            except httpx.HTTPError as e:
                print(f"  ERR  {label:<34} {type(e).__name__}")

    print("\n" + "=" * 74)
    print("结论：" + ("全部就绪 ✓" if ok else "存在未就绪项 ✗，见上方标记"))
    print("=" * 74)
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只检查，不初始化")
    args = ap.parse_args()

    if not MYSQL.exists():
        print(f"找不到 {MYSQL}，请确认 XAMPP 安装在 H:/XAMPP", file=sys.stderr)
        return 2

    with httpx.Client(timeout=120, follow_redirects=True) as c:
        if not args.check:
            print("=" * 74)
            print("初始化靶场")
            print("=" * 74)
            print(f"  sqli-labs  {init_sqli_labs()}")
            print(f"  Pikachu    {init_pikachu(c)}")
            print(f"  DVWA       {init_dvwa(c)}")
        ok = check(c)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
