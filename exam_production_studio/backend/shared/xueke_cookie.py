"""学科网 Cookie 自动获取（面向非技术用户）。

两种方式：
1. read_from_browser()：用 browser_cookie3 直接读取本机已登录浏览器中的 zxxk.com Cookie（最省事，
   但受浏览器加密策略影响，较新 Chrome/Edge 可能读不到）。
2. LoginSession：用 Playwright 打开真实浏览器窗口，用户正常登录后抓取 Cookie（最稳，需已装 playwright）。

所有 Cookie 仅限 zxxk.com 域，不读取其它站点；保存后清除运行时配置错误标记。
"""
from __future__ import annotations

import threading
import time
from typing import Any

import db
from shared import config_errors

_ZXXK = "zxxk.com"
_LOGIN_URL = "https://www.zxxk.com/"
# 登录成功的启发式判断：出现名字含以下关键字的 Cookie 即认为已登录
_AUTH_COOKIE_HINTS = ("token", "uid", "userid", "ucid", "auth", "passport", "sessionid", "usercode")
_LOGIN_TIMEOUT_S = 300  # 用户手动登录最长等待 5 分钟


def _cookie_str_from_pairs(pairs: list[tuple[str, str]]) -> str:
    seen: set[str] = set()
    out: list[str] = []
    for name, value in pairs:
        if not name or name in seen:
            continue
        seen.add(name)
        out.append(f"{name}={value}")
    return "; ".join(out)


def _save_cookie(cookie_str: str) -> None:
    db.execute(
        "INSERT INTO settings (key, value) VALUES (?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        ("xueke.cookie", cookie_str),
    )
    config_errors.clear()


# ---------------- 方式一：读取本机浏览器 ----------------
def read_from_browser() -> dict[str, Any]:
    """尝试从 Chrome/Edge/Firefox 读取 zxxk.com 的 Cookie。返回 {ok, count, source, message}。"""
    try:
        import browser_cookie3 as bc  # 延迟导入，未安装时给出提示
    except Exception:  # noqa: BLE001
        return {"ok": False, "count": 0, "source": "",
                "message": "未安装 browser_cookie3，无法读取浏览器 Cookie；请改用「登录学科网」。"}

    loaders = [("Chrome", getattr(bc, "chrome", None)), ("Edge", getattr(bc, "edge", None)),
               ("Firefox", getattr(bc, "firefox", None))]
    tried_errors: list[str] = []
    for source, loader in loaders:
        if loader is None:
            continue
        try:
            jar = loader(domain_name=_ZXXK)
        except Exception as e:  # noqa: BLE001
            tried_errors.append(f"{source}: {e}")
            continue
        pairs = [(c.name, c.value) for c in jar if _ZXXK in (c.domain or "")]
        if pairs:
            cookie_str = _cookie_str_from_pairs(pairs)
            _save_cookie(cookie_str)
            return {"ok": True, "count": len(pairs), "source": source,
                    "message": f"已从 {source} 读取到学科网 Cookie（{len(pairs)} 项）。"}
    detail = ("；".join(tried_errors)) if tried_errors else "未在浏览器中找到学科网登录信息（可能未登录或浏览器加密限制）"
    return {"ok": False, "count": 0, "source": "", "message": f"未能自动读取：{detail}。请改用「登录学科网」。"}


# ---------------- 方式二：Playwright 登录窗口 ----------------
class LoginSession:
    """单例式登录会话：所有 Playwright 调用都在同一后台线程内完成（避免线程亲和问题）。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._harvest = threading.Event()
        self._cancel = threading.Event()
        self.state: str = "idle"  # idle|running|success|failed|timeout|cancelled
        self.message: str = ""
        self.count: int = 0

    def start(self) -> dict[str, Any]:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return {"state": self.state, "message": "登录窗口已打开，请在浏览器中完成登录。"}
            try:
                import playwright  # noqa: F401
            except Exception:  # noqa: BLE001
                self.state = "failed"
                self.message = "未安装 Playwright，无法打开登录窗口；请先安装或改用「一键读取」。"
                return {"state": self.state, "message": self.message}
            self._harvest.clear()
            self._cancel.clear()
            self.state = "running"
            self.message = "已打开学科网登录窗口，请在其中登录；登录后点击「我已登录完成」。"
            self.count = 0
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            return {"state": self.state, "message": self.message}

    def confirm(self) -> dict[str, Any]:
        """用户点击「我已登录完成」→ 触发抓取。"""
        if not (self._thread and self._thread.is_alive()):
            return {"state": self.state, "message": "没有正在进行的登录会话，请先点击「登录学科网」。"}
        self._harvest.set()
        return {"state": "running", "message": "正在读取登录信息……"}

    def cancel(self) -> dict[str, Any]:
        self._cancel.set()
        self._harvest.set()
        return {"state": self.state, "message": "已请求关闭登录窗口。"}

    def status(self) -> dict[str, Any]:
        return {"state": self.state, "message": self.message, "count": self.count}

    def _run(self) -> None:
        from playwright.sync_api import sync_playwright
        try:
            with sync_playwright() as p:
                try:
                    browser = p.chromium.launch(headless=False)
                except Exception as e:  # noqa: BLE001
                    self.state = "failed"
                    self.message = (f"无法启动浏览器内核：{e}。"
                                    "请在项目目录运行 `python -m playwright install chromium` 后重试。")
                    return
                context = browser.new_context()
                page = context.new_page()
                page.goto(_LOGIN_URL, wait_until="domcontentloaded")

                deadline = time.time() + _LOGIN_TIMEOUT_S
                harvested = False
                while time.time() < deadline:
                    if self._cancel.is_set():
                        self.state = "cancelled"
                        self.message = "已取消登录。"
                        break
                    cookies = self._zxxk_cookies(context)
                    manual = self._harvest.wait(2)
                    # 手动确认，或自动检测到登录 Cookie
                    if manual or self._looks_logged_in(cookies):
                        cookies = self._zxxk_cookies(context)  # 重新取最新
                        if cookies:
                            _save_cookie(_cookie_str_from_pairs(cookies))
                            self.count = len(cookies)
                            self.state = "success"
                            self.message = f"登录成功，已保存学科网 Cookie（{len(cookies)} 项）。"
                            harvested = True
                            break
                        elif manual:
                            self.message = "尚未检测到登录信息，请确认已在窗口中登录后再点「我已登录完成」。"
                            self._harvest.clear()
                if not harvested and self.state == "running":
                    self.state = "timeout"
                    self.message = "登录超时，请重试。"
                try:
                    browser.close()
                except Exception:  # noqa: BLE001
                    pass
        except Exception as e:  # noqa: BLE001
            self.state = "failed"
            self.message = f"登录过程出错：{e}"

    @staticmethod
    def _zxxk_cookies(context) -> list[tuple[str, str]]:
        try:
            cks = context.cookies()
        except Exception:  # noqa: BLE001
            return []
        return [(c.get("name", ""), c.get("value", "")) for c in cks if _ZXXK in (c.get("domain") or "")]

    @staticmethod
    def _looks_logged_in(cookies: list[tuple[str, str]]) -> bool:
        names = {n.lower() for n, _ in cookies}
        return any(any(h in n for h in _AUTH_COOKIE_HINTS) for n in names)


login_session = LoginSession()
