#!/usr/bin/env python3
"""포트폴리오 문서(index.html)를 A4 PDF로 만들어 레포 맨 위에 <이름>-포트폴리오.pdf(예: 홍길동-포트폴리오.pdf)로 저장합니다.
이름은 data/portfolio.json의 profile.name(= profile.md의 이름)에서 읽습니다. Claude Code에서는 /portfolio-make-pdf 스킬이 이 도구를 씁니다.

    python3 tools/make-pdf.py                                   # 만들기 (Windows: py -3 tools/make-pdf.py)
    python3 tools/make-pdf.py --out 미리.pdf --report 점검.json  # 미리 만들어 점검만(덮어쓰지 않음)
    python3 tools/make-pdf.py --css 후보.css --against 점검.json  # theme/pdf.css 대신 후보 CSS로 시험, 지금과 줄바꿈 비교
    python3 tools/make-pdf.py --pages 쪽그림폴더 --from 미리.pdf  # PDF를 쪽마다 PNG + 모음(sheet.png)으로
    python3 tools/make-pdf.py --finalize 미리.pdf                # 점검한 파일을 <이름>-포트폴리오.pdf로 확정(복사)
    python3 tools/make-pdf.py --print-name                      # 확정 파일 이름만 출력
    python3 tools/make-pdf.py --env                             # 이 컴퓨터에서 고른 방식만 출력

하는 일
- 페이지를 넓은 화면 폭(--layout-px, 기본 1040 — theme/pdf.css의 /* layout-px: N */)으로 배치한 뒤 A4에 맞게 줄여 인쇄 → 화면 배치를 따름.
- theme/pdf.css(PDF 전용 배치 손질)를 인쇄에만 덧씌움(페이지가 이 파일을 불러오지 않아도 도구가 넣음).
- 글씨 규칙(이미 잘 보이는 글은 키우지 않기 · 가장 큰 글 대비 비율 한도 · 캡션 같은 종류는 같은 크기), 흐린 배경 굳히기, 링크를 배포 주소로.
- 그림은 만드는 동안만 줄여 넘김(긴 변 1400px · JPEG 80, 투명한 그림은 PNG 유지). 원본 파일은 안 건드림.

환경에 따라 방식을 고름(mac 품질은 그대로, Windows는 Windows에서 되는 방식)
- Chrome 연결: mac·리눅스 = 파이프 / Windows = 로컬 포트(WebSocket). 결과 PDF는 같음.
- 그림 압축: Pillow가 있으면 Pillow → mac이면 sips → 둘 다 없으면 Chrome 안에서(canvas).
- 쪽 그림(--pages): mac이면 PDFKit(미리보기와 같은 엔진, raster.swift) → 아니면 Chrome 안의 pdf.js(인터넷 필요).
필요한 것: Google Chrome(또는 Chromium·Edge), 파이썬 3.8 이상(표준 라이브러리만).
"""
import argparse
import base64
import functools
import http.server
import io
import json
import os
import platform
import re
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata
import urllib.parse
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_CSS = os.path.join(ROOT, "theme", "pdf.css")
SKILL_DIR = os.path.join(ROOT, ".claude", "skills", "portfolio-make-pdf")
IS_WIN, IS_MAC = os.name == "nt", sys.platform == "darwin"
A4_W_MM, A4_H_MM = 210, 297
REF_LAYOUT_PX = 1040                 # 화면 배치(넓은 화면) — '원본 페이지'의 기준 폭
KEEP_READABLE_PT = 10.0              # 이미 잘 보이는 글씨의 기준(종이 위 pt)
RATIO_LIMIT = 1.25                   # 원본에서 가장 큰 글 대비 비율이 달라져도 되는 한도(× · ÷)
BACKDROP_CONTRAST = 3.0              # 흐린 배경 위 밝은 글씨의 최소 대비
IMG_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff"}
PDFJS = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174"


# ── 이름 · Chrome · 배포 주소 ──
def pdf_name():
    """확정 PDF 이름 = '<이름>-포트폴리오.pdf'(페이지의 [PDF로 저장]도 같은 규칙). NFC로(맥에서도 웹 주소와 같은 글자 조합)."""
    name = ""
    try:
        with open(os.path.join(ROOT, "data", "portfolio.json"), encoding="utf-8") as f:
            name = str((json.load(f).get("profile") or {}).get("name") or "").strip()
    except Exception:
        pass
    name = re.sub(r'[\\/:*?"<>|]', "", name)
    return unicodedata.normalize("NFC", f"{name}-포트폴리오.pdf" if name else "포트폴리오.pdf")


def find_chrome(given):
    if given:
        return given
    cands = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
    ]
    for c in cands:
        if os.path.isfile(c):
            return c
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge"):
        p = shutil.which(name)
        if p:
            return p
    return None


def guess_base():
    """git remote origin이 github.com/<계정>/<레포>이면 GitHub Pages 주소로 짐작."""
    try:
        url = subprocess.run(["git", "-C", ROOT, "remote", "get-url", "origin"], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return ""
    m = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$", url)
    if not m:
        return ""
    owner, repo = m.group(1), m.group(2)
    if repo.lower() == f"{owner.lower()}.github.io":
        return f"https://{owner.lower()}.github.io/"
    return f"https://{owner.lower()}.github.io/{repo}/"


def pick_env(args):
    """이 컴퓨터에 맞는 방식. mac 품질은 그대로 두고, Windows는 Windows에서 되는 방식으로."""
    try:
        import PIL.Image  # noqa: F401
        has_pil = True
    except Exception:
        has_pil = False
    transport = args.transport if args.transport != "auto" else ("ws" if IS_WIN else "pipe")
    if args.no_compress:
        compress = "none"
    elif args.compress != "auto":
        compress = args.compress
    else:
        compress = "pillow" if has_pil else ("sips" if IS_MAC and shutil.which("sips") else "canvas")
    raster = args.raster if args.raster != "auto" else ("pdfkit" if IS_MAC and shutil.which("swift") and os.path.isfile(os.path.join(SKILL_DIR, "raster.swift")) else "pdfjs")
    return {"os": f"{platform.system()} {platform.release()}", "transport": transport, "compress": compress, "raster": raster, "pillow": has_pil}


# ── PDF 배치 CSS(theme/pdf.css)의 설정 줄: /* 키: 값 */ ──
def read_text(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def directive(css, key, default=None):
    m = re.search(r"/\*\s*" + re.escape(key) + r":\s*([^*]+?)\s*\*/", css or "")
    return m.group(1).strip() if m else default


def num_directive(css, key, default, allow_off=False):
    v = directive(css, key)
    if v is None:
        return default
    if allow_off and v.lower() == "off":
        return 0.0
    m = re.match(r"[\d.]+", v)
    return float(m.group(0)) if m else default


def page_margins(css_text, page="index.html"):
    """종이 여백(mm): 페이지(html)와 그 페이지가 불러오는 레포 안 CSS의 @page { margin }, 그다음 PDF 배치 CSS의 이름 없는 @page. 못 읽으면 12 14 12."""
    t, x, b = 12.0, 14.0, 12.0
    def apply(body, t, x, b):
        m = re.search(r"margin:\s*([\d.]+)mm(?:\s+([\d.]+)mm)?(?:\s+([\d.]+)mm)?", body)
        if m:
            t = float(m.group(1)); x = float(m.group(2) or t); b = float(m.group(3) or t)
        for side, val in re.findall(r"margin-(top|bottom|left|right):\s*([\d.]+)mm", body):
            if side == "top": t = float(val)
            elif side == "bottom": b = float(val)
            else: x = float(val)
        return t, x, b
    html = read_text(os.path.join(ROOT, page))
    sources = []
    for m in re.finditer(r"<link[^>]+href=[\"']([^\"']+\.css)[\"'][^>]*>|<style[^>]*>(.*?)</style>", html, re.S | re.I):
        if m.group(1):
            href = m.group(1)
            if not re.match(r"^[a-z]+:|^//", href, re.I) and "pdf.css" not in href:
                sources.append(read_text(os.path.join(ROOT, os.path.dirname(page), href.split("?")[0])))
        else:
            sources.append(m.group(2))
    sources.append(css_text or "")
    for src in sources:
        for body in re.findall(r"@page\s*\{([^}]*)\}", src):            # 이름 없는 @page만(이름 붙은 쪽은 제외)
            t, x, b = apply(body, t, x, b)
    return t, x, b


# ── 그림 압축(서버에서): Pillow 또는 macOS sips ──
def png_has_transparency(data):
    """작게 줄인 PNG에 투명한 픽셀이 있는지. 8비트 RGBA·회색+알파만 읽고, 모르는 형식은 '있음'(안전하게 PNG 유지)."""
    try:
        if data[:8] != b"\x89PNG\r\n\x1a\n":
            return True
        pos, idat, w = 8, b"", 0
        while pos < len(data):
            n, kind = struct.unpack(">I4s", data[pos:pos + 8])
            body = data[pos + 8:pos + 8 + n]
            if kind == b"IHDR":
                w, h, depth, ctype, _, _, interlace = struct.unpack(">IIBBBBB", body)
                if depth != 8 or interlace or ctype not in (4, 6):
                    return ctype in (3, 4, 6) or depth != 8
                bpp = 4 if ctype == 6 else 2
            elif kind == b"IDAT":
                idat += body
            elif kind == b"IEND":
                break
            pos += 12 + n
        raw, stride = zlib.decompress(idat), w * bpp
        prev, i = bytearray(stride), 0
        while i < len(raw):
            f, row = raw[i], bytearray(raw[i + 1:i + 1 + stride])
            i += 1 + stride
            for x in range(stride):
                a = row[x - bpp] if x >= bpp else 0
                b = prev[x]
                c = prev[x - bpp] if x >= bpp else 0
                if f == 1: row[x] = (row[x] + a) & 255
                elif f == 2: row[x] = (row[x] + b) & 255
                elif f == 3: row[x] = (row[x] + ((a + b) >> 1)) & 255
                elif f == 4:
                    p = a + b - c; pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                    row[x] = (row[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
            if min(row[bpp - 1::bpp]) < 250:
                return True
            prev = row
        return False
    except Exception:
        return True


class Compressor:
    def __init__(self, tool, max_px, quality):
        self.tool, self.max_px, self.quality = tool, max_px, quality
        self.cache, self.lock = {}, threading.Lock()
        self.stats = {"images": 0, "before": 0, "after": 0, "kept_png": [], "failed": []}
        self.tmp = tempfile.mkdtemp(prefix="pf-pdf-img-")

    def close(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def get(self, path):
        with self.lock:
            if path in self.cache:
                return self.cache[path]
            res = self._make(path)
            self.cache[path] = res
            orig = os.path.getsize(path)
            self.stats["images"] += 1
            self.stats["before"] += orig
            self.stats["after"] += len(res[0]) if res[0] is not None else orig
            return res

    def _make(self, path):
        rel = os.path.relpath(path, ROOT)
        try:
            data, ctype, kept = (self._pillow if self.tool == "pillow" else self._sips)(path)
        except Exception as e:
            self.stats["failed"].append(f"{rel}: {e}")
            return None, None
        if kept:
            self.stats["kept_png"].append(rel)
        if len(data) >= os.path.getsize(path):
            return None, None
        return data, ctype

    def _pillow(self, path):
        from PIL import Image
        im = Image.open(path)
        im.seek(0)
        im = im.convert("RGBA") if im.mode in ("RGBA", "LA", "P", "PA") else im.convert("RGB")
        im.thumbnail((self.max_px, self.max_px), Image.LANCZOS)
        out = io.BytesIO()
        if im.mode == "RGBA" and im.getchannel("A").getextrema()[0] < 250:
            im.save(out, "PNG", optimize=True)
            return out.getvalue(), "image/png", True
        im.convert("RGB").save(out, "JPEG", quality=self.quality, optimize=True, progressive=True)
        return out.getvalue(), "image/jpeg", False

    def _sips(self, path):
        def run(*a):
            return subprocess.run(["sips", *a], capture_output=True, text=True, check=True).stdout
        info = run("-g", "pixelWidth", "-g", "pixelHeight", "-g", "hasAlpha", path)
        w = int(re.search(r"pixelWidth:\s*(\d+)", info).group(1))
        h = int(re.search(r"pixelHeight:\s*(\d+)", info).group(1))
        alpha = re.search(r"hasAlpha:\s*yes", info) is not None
        size = ["-Z", str(self.max_px)] if max(w, h) > self.max_px else []
        base = os.path.join(self.tmp, f"{len(self.cache)}")
        if alpha:
            probe = base + "-probe.png"
            run("-s", "format", "png", "-Z", "96", path, "--out", probe)
            with open(probe, "rb") as f:
                alpha = png_has_transparency(f.read())
        out = base + (".png" if alpha else ".jpg")
        if alpha:
            run("-s", "format", "png", *size, path, "--out", out)
        else:
            run("-s", "format", "jpeg", "-s", "formatOptions", str(self.quality), *size, path, "--out", out)
        with open(out, "rb") as f:
            return f.read(), ("image/png" if alpha else "image/jpeg"), alpha


def make_handler(compressor, directory):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=directory, **k)

        def log_message(self, *a):
            pass

        def send_head(self):
            path = self.translate_path(self.path)
            if (compressor and os.path.isfile(path) and os.path.splitext(path)[1].lower() in IMG_EXT
                    and os.path.commonpath([os.path.abspath(path), ROOT]) == ROOT):
                data, ctype = compressor.get(path)
                if data is not None:
                    self.send_response(200)
                    self.send_header("Content-Type", ctype)
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    return io.BytesIO(data)
            return super().send_head()
    return Handler


def serve(directory, compressor=None):
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), make_handler(compressor, directory))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


# ── Chrome 원격 제어: mac·리눅스 = 파이프(--remote-debugging-pipe) / Windows = 로컬 포트(WebSocket) ──
CHROME_FLAGS = ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", "--hide-scrollbars",
                "--disable-extensions", "--disable-background-networking"]


class CDPBase:
    n = 0

    def _send_raw(self, data):
        raise NotImplementedError

    def _recv_raw(self):
        raise NotImplementedError

    def send(self, method, params=None, session=None):
        self.n += 1
        msg = {"id": self.n, "method": method, "params": params or {}}
        if session:
            msg["sessionId"] = session
        self._send_raw(json.dumps(msg).encode())
        while True:
            res = json.loads(self._recv_raw())
            if res.get("id") == self.n:
                if "error" in res:
                    raise RuntimeError(f"{method}: {res['error'].get('message')}")
                return res.get("result", {})

    def eval(self, session, expr):
        r = self.send("Runtime.evaluate", {"expression": expr, "awaitPromise": True, "returnByValue": True}, session)
        if "exceptionDetails" in r:
            d = r["exceptionDetails"]
            raise RuntimeError((d.get("exception") or {}).get("description") or d.get("text", "스크립트 오류"))
        return r.get("result", {}).get("value")

    def close(self):
        try:
            self.send("Browser.close")
        except Exception:
            pass
        try:
            self.proc.wait(10)
        except Exception:
            self.proc.kill()


class CDPPipe(CDPBase):
    """mac·리눅스: Chrome이 fd 3으로 읽고 fd 4로 씀(메시지는 \\0으로 구분)."""
    def __init__(self, chrome, profile, width):
        r_in, w_in = os.pipe()
        r_out, w_out = os.pipe()

        def fds():
            os.dup2(r_in, 3)
            os.dup2(w_out, 4)
        self.proc = subprocess.Popen([chrome, *CHROME_FLAGS, "--remote-debugging-pipe", f"--window-size={width},1400",
                                      f"--user-data-dir={profile}", "about:blank"],
                                     preexec_fn=fds, pass_fds=(3, 4), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.close(r_in); os.close(w_out)
        self.w, self.r = os.fdopen(w_in, "wb"), os.fdopen(r_out, "rb")
        self.buf = b""

    def _send_raw(self, data):
        self.w.write(data + b"\0"); self.w.flush()

    def _recv_raw(self):
        while b"\0" not in self.buf:
            chunk = self.r.read1(1 << 20)
            if not chunk:
                raise RuntimeError("Chrome 연결이 끊김")
            self.buf += chunk
        raw, self.buf = self.buf.split(b"\0", 1)
        return raw


class CDPSocket(CDPBase):
    """Windows(및 --transport ws): Chrome을 로컬 포트로 열고 표준 라이브러리만으로 WebSocket 연결."""
    def __init__(self, chrome, profile, width):
        self.proc = subprocess.Popen([chrome, *CHROME_FLAGS, "--remote-debugging-port=0", "--remote-allow-origins=*",
                                      f"--window-size={width},1400", f"--user-data-dir={profile}", "about:blank"],
                                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        port_file = os.path.join(profile, "DevToolsActivePort")
        for _ in range(300):                                            # Chrome이 포트를 알려 줄 때까지(최대 30초)
            if os.path.isfile(port_file):
                lines = read_text(port_file).split()
                if len(lines) >= 2:
                    port, path = int(lines[0]), lines[1]
                    break
            time.sleep(0.1)
        else:
            self.proc.kill()
            raise RuntimeError("Chrome 원격 제어 포트를 열지 못했습니다(DevToolsActivePort 없음).")
        self.sock = socket.create_connection(("127.0.0.1", port), timeout=300)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((f"GET {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                           f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise RuntimeError("Chrome WebSocket 연결 실패")
            head += chunk
        if b" 101 " not in head.split(b"\r\n", 1)[0]:
            raise RuntimeError("Chrome WebSocket 연결 거부: " + head.split(b"\r\n", 1)[0].decode("latin-1"))
        self.buf = head.split(b"\r\n\r\n", 1)[1]

    def _read(self, n):
        while len(self.buf) < n:
            chunk = self.sock.recv(1 << 20)
            if not chunk:
                raise RuntimeError("Chrome 연결이 끊김")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def _frame(self, opcode, payload):
        head = bytes([0x80 | opcode])
        n = len(payload)
        if n < 126:
            head += bytes([0x80 | n])
        elif n < 65536:
            head += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            head += bytes([0x80 | 127]) + struct.pack(">Q", n)
        mask = os.urandom(4)
        body = bytes(b ^ mask[i % 4] for i, b in enumerate(payload)) if n < 4096 else _xor_mask(payload, mask)
        self.sock.sendall(head + mask + body)

    def _send_raw(self, data):
        self._frame(0x1, data)

    def _recv_raw(self):
        parts = []
        while True:
            b1, b2 = self._read(2)
            fin, op, n = b1 & 0x80, b1 & 0x0F, b2 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._read(8))[0]
            mask = self._read(4) if b2 & 0x80 else None
            data = self._read(n)
            if mask:
                data = _xor_mask(data, mask)
            if op == 0x9:                                               # ping → pong
                self._frame(0xA, data); continue
            if op == 0x8:
                raise RuntimeError("Chrome이 연결을 닫음")
            if op in (0x1, 0x2, 0x0):
                parts.append(data)
                if fin:
                    return b"".join(parts)

    def close(self):
        super().close()
        try:
            self.sock.close()
        except Exception:
            pass


def _xor_mask(data, mask):
    m = (mask * (len(data) // 4 + 1))[:len(data)]
    return (int.from_bytes(data, "big") ^ int.from_bytes(m, "big")).to_bytes(len(data), "big") if data else b""


def open_cdp(transport, chrome, profile, width):
    return CDPSocket(chrome, profile, width) if transport == "ws" else CDPPipe(chrome, profile, width)


def new_tab(cdp, width):
    tid = cdp.send("Target.createTarget", {"url": "about:blank"})["targetId"]
    sid = cdp.send("Target.attachToTarget", {"targetId": tid, "flatten": True})["sessionId"]
    cdp.send("Page.enable", session=sid)
    cdp.send("Emulation.setDeviceMetricsOverride", {"width": width, "height": 1400, "deviceScaleFactor": 1, "mobile": False}, sid)
    return sid


# ── 페이지 안에서 도는 스크립트 ──
# 준비 기다리기: 템플릿 페이지면 PFPage.whenReady(), 아니면 load + 그림 + 글꼴
WAIT_JS = r"""(async () => {
  const t = (ms) => new Promise((r) => setTimeout(r, ms));
  for (let i = 0; i < 200 && !window.PFPage; i++) await t(100);
  const generic = !window.PFPage;
  if (generic) { if (document.readyState !== 'complete') await new Promise((r) => addEventListener('load', r, { once: true })); }
  else await Promise.race([PFPage.whenReady(), t(40000)]);
  await Promise.race([Promise.all([...document.images].map((i) => i.complete ? 0 : new Promise((r) => { i.addEventListener('load', r, { once: true }); i.addEventListener('error', r, { once: true }); }))), t(20000)]);
  if (document.fonts) await Promise.race([document.fonts.ready, t(5000)]);
  await t(generic ? 1200 : 300);
  return generic ? 'generic' : (document.documentElement.dataset.pfReady || 'no');
})()"""

# 템플릿의 PFPage가 없는 페이지용 간단 점검
GENERIC_AUDIT_JS = r"""JSON.stringify({ ready: 'yes', generic: true, errors: [],
  images: { total: document.images.length, broken: [...document.images].filter((i) => i.complete && !i.naturalWidth && i.src).map((i) => i.getAttribute('src')), pending: [] },
  overflowX: Math.max(0, document.documentElement.scrollWidth - innerWidth) })"""

# 원본 페이지(화면 배치 폭)의 글씨 크기를 요소마다 기억
ORIG_JS = r"""((rootSel) => {
  const root = document.querySelector(rootSel) || document.body;
  const own = (el) => [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
  window.__pfOrig = new Map([...root.querySelectorAll('*')].filter(own).map((el) => [el, parseFloat(getComputedStyle(el).fontSize)]));
  return window.__pfOrig.size;
})"""

# 인쇄 규칙이 글씨 크기를 따로 정하는지: 같은 요소의 화면(원본) 크기와 인쇄 크기를 글자 수로 가중해 비교(1 = 화면 크기 그대로 인쇄)
PRINT_VS_SCREEN_JS = r"""((rootSel) => {
  const root = document.querySelector(rootSel) || document.body; let w = 0, sum = 0; const rs = [];
  for (const [el, px] of (window.__pfOrig || new Map())) {
    if (!el.isConnected || !el.getClientRects().length || !px) continue;
    const n = el.textContent.trim().length, r = parseFloat(getComputedStyle(el).fontSize) / px; rs.push([r, n]); w += n; sum += r * n; }
  rs.sort((a, b) => a[0] - b[0]); let acc = 0, med = 1; for (const [r, n] of rs) { acc += n; if (acc >= w / 2) { med = r; break; } }
  return { median: Math.round(med * 100) / 100, mean: w ? Math.round(sum / w * 100) / 100 : 1 };
})"""

# 배치 CSS 넣기(theme/pdf.css 또는 --css 후보) · 링크를 배포 주소로 · 축소 비율을 CSS에 알림
PREP_JS = r"""(async (css, base, scale) => {
  document.querySelectorAll('link[href$="theme/pdf.css"]').forEach((l) => l.remove());
  if (css) { const s = document.createElement('style'); s.id = 'pf-pdf-css'; s.textContent = css; document.head.appendChild(s); }
  if (base) document.querySelectorAll('a[href]').forEach((a) => { const h = a.getAttribute('href');
    if (h && !h.startsWith('#') && !/^[a-z][a-z0-9+.-]*:/i.test(h)) a.setAttribute('href', new URL(h, base).href); });
  document.documentElement.style.setProperty('--pdf-scale', String(scale));
  dispatchEvent(new Event('resize'));
  await new Promise((r) => setTimeout(r, 800));
  return true;
})"""

# 흐린 배경 굳히기: 인쇄에서 보이는 흐린 그림(CSS filter: blur)을 같은 자리·같은 흐림으로 캔버스에 그려 작은 JPEG로 깖
#   (CSS 흐림을 PDF에 맡기면 사각형 얼룩·큰 파일). 꽉 찬 쪽(이름 붙은 쪽)이면 절이 아니라 그 쪽 자체의 배경(@page)으로
#   (절 배경은 Chrome이 바로 앞 쪽 맨 아래 경계에도 그려 가는 선이 생김). 배경이 밝으면 흰 글씨와 정한 대비가 될 때까지 검게 덮음.
#   sel: 흐린 배경 묶음 선택자(/* backdrop: … */). 비우면 흐림 필터가 걸린 그림을 스스로 찾음
BACKDROP_JS = r"""(async (ratio, scale, sel) => {
  const out = [];
  const lin = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
  const shown = (el) => el.getClientRects().length > 0 && (!el.checkVisibility || el.checkVisibility({ checkVisibilityCSS: true }));
  const named = (sec) => { const pg = getComputedStyle(sec).page; return pg && pg !== 'auto'; };
  let items = [];
  if (sel) items = [...document.querySelectorAll(sel)].filter(shown).map((bd) => ({ bd, img: bd.matches('img') ? bd : bd.querySelector('img') }));
  else items = [...document.querySelectorAll('img')].filter((i) => shown(i) && /blur\(/.test(getComputedStyle(i).filter)).map((img) => ({ img, bd: img.parentElement && img.parentElement.children.length === 1 ? img.parentElement : img }));
  items = items.filter((x) => x.img).map((x) => ({ ...x, sec: x.bd.closest('section') || x.bd.parentElement }));
  items.filter((x) => named(x.sec)).forEach(({ sec }) => { sec.style.setProperty('padding-left', '0px', 'important'); sec.style.setProperty('padding-right', '0px', 'important'); });
  dispatchEvent(new Event('resize')); await new Promise((r) => setTimeout(r, 500));
  const mmpx = 96 / 25.4 / scale;
  for (const { sec, bd, img } of items) {
    if (!img.complete || !img.naturalWidth) await new Promise((r) => { img.addEventListener('load', r, { once: true }); img.addEventListener('error', r, { once: true }); setTimeout(r, 5000); });
    if (!img.naturalWidth) continue;
    const sr = sec.getBoundingClientRect(), ir = img.getBoundingClientRect(), full = named(sec);
    const area = full ? { left: sr.left - (210 * mmpx - sr.width) / 2, top: sr.top, width: 210 * mmpx, height: 297 * mmpx } : { left: sr.left, top: sr.top, width: sr.width, height: sr.height };
    const f = getComputedStyle(img).filter; const bm = /blur\(([\d.]+)px\)/.exec(f); const blurPx = bm ? parseFloat(bm[1]) : 80;
    const rest = f.replace(/blur\([^)]*\)/, '').trim();
    const W = 720, k = W / area.width, H = Math.max(1, Math.round(area.height * k)), blur = blurPx * k, pad = Math.ceil(blur * 3);
    const big = document.createElement('canvas'); big.width = W + pad * 2; big.height = H + pad * 2;
    const b = big.getContext('2d'); b.fillStyle = '#000'; b.fillRect(0, 0, big.width, big.height);
    b.filter = `blur(${blur}px) ${rest === 'none' ? '' : rest}`;
    try { b.drawImage(img, pad + (ir.left - area.left) * k, pad + (ir.top - area.top) * k, ir.width * k, ir.height * k); } catch (e) { continue; }
    const c = document.createElement('canvas'); c.width = W; c.height = H; const x = c.getContext('2d');
    x.drawImage(big, pad, pad, W, H, 0, 0, W, H);
    let d; try { d = x.getImageData(0, 0, W, H).data; } catch (e) { continue; }       // 다른 출처 그림은 건너뜀
    const L = []; for (let i = 0; i < d.length; i += 16) L.push(0.2126 * lin(d[i]) + 0.7152 * lin(d[i + 1]) + 0.0722 * lin(d[i + 2]));
    L.sort((p, q) => p - q); const p80 = L[Math.floor(L.length * 0.8)] || 0;
    const target = (0.91 + 0.05) / ratio - 0.05;
    const a = p80 > target ? Math.min(0.85, 1 - target / p80) : 0;
    if (a > 0) { x.fillStyle = `rgba(0,0,0,${a.toFixed(3)})`; x.fillRect(0, 0, W, H); }
    const url = c.toDataURL('image/jpeg', 0.82);
    if (full) {
      const name = `pf-bg-${out.length + 1}`, st = document.createElement('style');
      st.textContent = `@page ${name} { margin: 0; background: #000 url(${url}) 0 0 / ${210 / scale}mm ${297 / scale}mm no-repeat; }`;
      document.head.appendChild(st);
      sec.style.setProperty('page', name, 'important'); sec.style.setProperty('background', 'none', 'important');
    } else sec.style.setProperty('background', `#000 url(${url}) center / 100% 100% no-repeat`, 'important');
    bd.style.setProperty('display', 'none', 'important');
    out.push({ id: sec.id || sec.className.split(' ')[0], darken: Math.round(a * 100) / 100, kb: Math.round(url.length * 0.75 / 1024), page: full });
  }
  items.filter((x) => named(x.sec)).forEach(({ sec }) => { sec.style.removeProperty('padding-left'); sec.style.removeProperty('padding-right'); });
  return out;
})"""

# 글씨 규칙(인쇄 미디어로 배치한 뒤, 글이 있는 요소마다 크기·줄 높이를 직접 지정)
#   ① 이미 잘 보이는 글은 키우지 않기: 화면 비율로 줄인 종이 위 크기(ref)가 R 이상이면 그대로, 작으면 min(ref×g, R − (R − ref)/4)
#   ② 비율 한도: 원본에서 가장 큰 글 대비 비율이 PDF에서 ÷T ~ ×T 안
#   ③ 같은 종류(캡션 등 groupSel)는 모두 같은 크기, 키워서 줄이 늘면 줄이 늘지 않는 데까지만
KEEP_JS = r"""((scale, refScale, R, T, rootSel, groupSel) => {
  const root = document.querySelector(rootSel) || document.body;
  const g = scale / refScale;
  const own = (el) => [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
  const els = [...root.querySelectorAll('*')].filter(own);
  const cs = els.map((el) => { const c = getComputedStyle(el); return { px: parseFloat(c.fontSize), lh: parseFloat(c.lineHeight) }; });
  const orig = els.map((el, i) => (window.__pfOrig && window.__pfOrig.get(el)) || cs[i].px * scale / refScale);
  const shown = els.map((el) => el.getClientRects().length > 0 && (!el.checkVisibility || el.checkVisibility({ checkVisibilityCSS: true })) && !el.closest('.sr-only'));
  const size = (i, np) => { const { px, lh } = cs[i];
    els[i].style.setProperty('font-size', np.toFixed(2) + 'px', 'important');
    if (lh) els[i].style.setProperty('line-height', (lh * np / px).toFixed(2) + 'px', 'important'); };
  const keepOn = R > 0 && g > 1.001;
  const grown = (i) => { if (!keepOn) return cs[i].px; const ref = cs[i].px * refScale * 0.75; return (ref >= R ? ref : Math.min(ref * g, R - (R - ref) / 4)) / (scale * 0.75); };
  const kept = (i) => keepOn ? cs[i].px * refScale / scale : cs[i].px;
  let k = -1; els.forEach((x, i) => { if (shown[i] && (k < 0 || orig[i] > orig[k])) k = i; });
  const P = k >= 0 ? grown(k) : 0, M = k >= 0 ? orig[k] : 0;
  const lowB = (i) => (T > 1 && M) ? orig[i] / M * P / T : 0;
  const highB = (i) => (T > 1 && M) ? orig[i] / M * P * T : Infinity;
  const clamp = (i, v) => Math.min(Math.max(v, lowB(i)), highB(i));
  const GROUPS = groupSel ? [['캡션', groupSel]] : [];
  const inGroup = new Set();
  const lines = (node) => { const r = document.createRange(); r.selectNodeContents(node); const g2 = [];
    for (const b of r.getClientRects()) { if (b.width < 1 || b.height < 1) continue; const c = b.top + b.height / 2;
      if (!g2.some((q) => c >= q.t && c <= q.b)) g2.push({ t: b.top, b: b.bottom }); } return g2.length; };
  let changed = 0, clamped = 0;
  els.forEach((x, i) => { if (GROUPS.some(([, sel]) => x.closest(sel))) { inGroup.add(i); return; }
    const v = grown(i), np = clamp(i, v); if (Math.abs(np - v) > 0.05) clamped++;
    if (Math.abs(np - cs[i].px) > 0.05) { size(i, np); changed++; } });
  const groups = [];
  for (const [name, sel] of GROUPS) {
    const idx = [...inGroup].filter((i) => els[i].closest(sel)); if (!idx.length) continue;
    const roots = [...new Set(idx.map((i) => els[i].closest(sel)))].filter((x) => x.getClientRects().length);
    const j = idx.reduce((a, i) => (cs[i].px < cs[a].px ? i : a), idx[0]);
    const ratio = (i) => cs[i].px / cs[j].px;
    const at = (v) => { idx.forEach((i) => size(i, v * ratio(i))); return roots.map(lines); };
    const lo = Math.max(kept(j), lowB(j)), hi = Math.max(lo, Math.min(grown(j), highB(j)));
    const low = at(lo); let pick = lo;
    for (let v = hi; v > lo + 0.01; v -= 0.25) { const n = at(v); if (!n.some((c, q) => c > low[q])) { pick = v; break; } }
    at(pick); changed += idx.length;
    groups.push({ name, count: roots.length, enlarged: pick > kept(j) + 0.01, full: pick >= hi - 0.01, pt: Math.round(pick * scale * 0.75 * 10) / 10 });
  }
  let dev = 1, devAt = '';
  const Pf = k >= 0 ? parseFloat(getComputedStyle(els[k]).fontSize) : 0;
  els.forEach((x, i) => { if (!shown[i] || !M || !Pf) return; const f = parseFloat(getComputedStyle(x).fontSize);
    const d = (f / Pf) / (orig[i] / M), dd = Math.max(d, 1 / d); if (dd > dev) { dev = dd; devAt = ((x.closest('[id]') || {}).id || '') + ' ' + x.textContent.trim().slice(0, 16); } });
  return new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(() => r({ changed, clamped, groups,
    largest: k >= 0 ? { text: els[k].textContent.trim().slice(0, 20), orig_px: orig[k], pt: Math.round(P * scale * 0.75 * 10) / 10 } : null,
    ratio_limit: T, ratio_dev_max: Math.round(dev * 100) / 100, ratio_dev_at: devAt }))));
})"""

# Chrome 안에서 그림 줄이기(Windows에서 Pillow가 없을 때): 인쇄에 보이는 같은 출처 그림을 긴 변 maxPx로, 투명하면 PNG·아니면 JPEG
CANVAS_IMG_JS = r"""(async (maxPx, q) => {
  const st = { images: 0, before: 0, after: 0, kept_png: [], failed: [] }, done = new Map();
  for (const img of [...document.images]) {
    if (!img.getClientRects().length || !img.naturalWidth || img.src.startsWith('data:')) continue;
    try {
      if (new URL(img.src).origin !== location.origin) continue;
      if (!done.has(img.src)) {
        const e = performance.getEntriesByName(img.src)[0]; const before = e ? (e.encodedBodySize || e.transferSize || 0) : 0;
        const s = Math.min(1, maxPx / Math.max(img.naturalWidth, img.naturalHeight));
        const c = document.createElement('canvas'); c.width = Math.round(img.naturalWidth * s); c.height = Math.round(img.naturalHeight * s);
        const x = c.getContext('2d'); x.imageSmoothingQuality = 'high'; x.drawImage(img, 0, 0, c.width, c.height);
        const d = x.getImageData(0, 0, c.width, c.height).data; let alpha = false;
        for (let i = 3; i < d.length; i += 64) if (d[i] < 250) { alpha = true; break; }
        const url = alpha ? c.toDataURL('image/png') : c.toDataURL('image/jpeg', q);
        const after = Math.round(url.length * 0.75);
        done.set(img.src, before && after >= before ? null : url);
        st.images++; st.before += before; st.after += (before && after >= before) ? before : after; if (alpha) st.kept_png.push(img.getAttribute('src'));
      }
      const url = done.get(img.src);
      if (url) { img.removeAttribute('srcset'); img.src = url; await img.decode().catch(() => 0); }
    } catch (e) { st.failed.push(String(img.getAttribute('src')) + ': ' + e.message); }
  }
  return st;
})"""

# 인쇄 배치 재기(인쇄 미디어로): 글씨 크기(종이 위 pt) · 쪽 채움 · 줄바꿈 · 종이 위 그림·표 크기
#   chk: { root, single, cell, cover, feature, box } — 이 페이지에 맞춘 선택자(/* check-…: … */). 없으면 그 항목은 null
MEASURE_JS = r"""((scale, pageH, fullH, chk) => {
  const root = document.querySelector(chk.root) || document.body;
  root.querySelectorAll('*').forEach((el) => { const c = getComputedStyle(el); if (c.page && c.page !== 'auto') { el.style.setProperty('padding-left', '0px', 'important'); el.style.setProperty('padding-right', '0px', 'important'); } });
  const vis = (el) => { const r = el.getBoundingClientRect(); return r.width > 2 && r.height > 2 && (el.checkVisibility ? el.checkVisibility({ checkVisibilityCSS: true }) : true); };
  const where = (el) => { const sec = el.closest('[id]'); const cls = (el.className && typeof el.className === 'string' ? el.className.split(/\s+/)[0] : '') || el.tagName.toLowerCase(); return (sec ? '#' + sec.id + ' ' : '') + cls; };
  const sizes = new Map(); let total = 0;
  const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  for (let n; (n = w.nextNode());) {
    const t = n.textContent.replace(/\s+/g, ''); const el = n.parentElement;
    if (!t || !el || el.closest('script,style,noscript,.sr-only') || !vis(el)) continue;
    const px = Math.round(parseFloat(getComputedStyle(el).fontSize) * 10) / 10;
    const e = sizes.get(px) || { px, chars: 0, where: new Map(), sample: '' };
    e.chars += t.length; total += t.length; const k = where(el); e.where.set(k, (e.where.get(k) || 0) + t.length);
    if (!e.sample) e.sample = n.textContent.trim().slice(0, 30); sizes.set(px, e);
  }
  const list = [...sizes.values()].sort((a, b) => a.px - b.px);
  const pick = (q) => { let acc = 0; for (const e of list) { acc += e.chars; if (acc >= total * q) return e.px; } return list.length ? list[list.length - 1].px : 0; };
  const pt = (px) => Math.round(px * scale * 0.75 * 10) / 10;
  const fonts = { body_pt: pt(pick(0.5)), small_pt: pt(pick(0.1)), min_pt: list.length ? pt(list[0].px) : 0, screen_ratio: scale,
    sizes: list.map((e) => ({ pt: pt(e.px), px: e.px, share: Math.round(e.chars / total * 1000) / 10, sample: e.sample,
      where: [...e.where.entries()].sort((a, b) => b[1] - a[1]).slice(0, 3).map((x) => x[0]) })) };
  const y = (el) => el.getBoundingClientRect().top + scrollY;
  const starts = [...root.querySelectorAll('*')].filter((el) => getComputedStyle(el).breakBefore === 'page' && vis(el));
  const kids = [...root.querySelectorAll('section, footer, header, main > *, article')].filter(vis);
  const end = Math.max(...kids.map((el) => el.getBoundingClientRect().bottom + scrollY), y(root) + root.getBoundingClientRect().height * 0, y(root) + 1);
  const first = root.querySelector('section, footer, article') || root;
  const marks = [{ top: y(root), el: first }, ...starts.map((el) => ({ top: y(el), el }))].sort((a, b) => a.top - b.top);
  const label = (el) => (el.id ? '#' + el.id : (el.className && typeof el.className === 'string' ? '.' + el.className.split(/\s+/)[0] : el.tagName.toLowerCase())) + (el.querySelector('h1,h2') ? ' ' + el.querySelector('h1,h2').textContent.trim().slice(0, 24) : '');
  const chunks = marks.map((m, i) => {
    const h = (i + 1 < marks.length ? marks[i + 1].top : end) - m.top;
    const ph = getComputedStyle(m.el).page && getComputedStyle(m.el).page !== 'auto' ? fullH : pageH;
    const pages = Math.max(1, Math.ceil(h / ph - 0.02));
    return { at: label(m.el), height_px: Math.round(h), pages, last_fill: Math.round((h - (pages - 1) * ph) / ph * 100), full_bleed: ph === fullH };
  });
  const lines = (el) => { const r = document.createRange(); r.selectNodeContents(el); const g = [];
    for (const b of r.getClientRects()) { if (b.width < 1 || b.height < 1) continue; const c = b.top + b.height / 2;
      const x = g.find((q) => c >= q.t && c <= q.b); if (x) { x.l = Math.min(x.l, b.left); x.r = Math.max(x.r, b.right); x.t = Math.min(x.t, b.top); x.b = Math.max(x.b, b.bottom); }
      else g.push({ t: b.top, b: b.bottom, l: b.left, r: b.right }); }
    return g.sort((a, b) => a.t - b.t); };
  const txt = (el) => el.textContent.trim().replace(/ +/g, ' ');
  const isUrl = (t) => t.length > 12 && !t.includes(' ') && t.includes('/');
  const q = (sel) => { try { return sel ? [...root.querySelectorAll(sel)] : []; } catch (e) { return []; } };
  const single = q('h1, h2, h3, dt, .chip' + (chk.single ? ', ' + chk.single : ''))
    .filter((el) => vis(el) && !el.closest('.sr-only') && txt(el)).map((el) => ({ where: where(el), text: txt(el).slice(0, 40), lines: lines(el).length })).filter((x) => x.lines > 1);
  const urls = q('a, span, dd').filter((el) => vis(el) && !el.querySelector('a, span') && isUrl(txt(el)))
    .map((el) => ({ where: where(el), text: txt(el).slice(0, 60), lines: lines(el).length })).filter((x) => x.lines > 1);
  let paraLines = 0; const orphans = [], paras = [];
  for (const el of q('p, dd, li')) {
    if (!vis(el) || el.querySelector('p, li, dd') || txt(el).length < 20 || isUrl(txt(el))) continue;
    if ([...el.children].some((c) => !['inline', 'contents'].includes(getComputedStyle(c).display) && txt(c))) continue;
    const g = lines(el); paraLines += g.length;
    const wd = el.getBoundingClientRect().width;
    const short = g.length >= 2 ? g.filter((s) => (s.r - s.l) < wd * 0.12).length : 0;
    if (short) orphans.push({ where: where(el), text: txt(el).slice(-12), lines: g.length });
    paras.push({ key: where(el) + '|' + txt(el).slice(0, 18), px: parseFloat(getComputedStyle(el).fontSize), lines: g.length, short });
  }
  const cells = q(chk.cell).filter(vis).map((el) => ({ at: (el.previousElementSibling ? txt(el.previousElementSibling) : '') + ' @' + ((el.closest('[id]') || {}).id || ''), lines: lines(el).length }));
  const tmax = cells.reduce((a, c) => (c.lines > a.lines ? c : a), { lines: 0, at: '' });
  const wrap = { single_multi: single.length, single_list: single.slice(0, 15), url_broken: urls.length, url_list: urls.slice(0, 10),
    orphans: orphans.length, orphan_list: orphans.slice(0, 10), para_lines: paraLines, paras,
    table: chk.cell ? { max: tmax.lines, max_at: tmax.at, total: cells.reduce((a, c) => a + c.lines, 0) } : null };
  const mm = (px) => Math.round(px * scale * 25.4 / 96);
  const minW = (sel) => { const ws = q(sel).filter(vis).map((el) => el.getBoundingClientRect().width); return ws.length ? mm(Math.min(...ws)) : null; };
  const images_mm = { cover_min: minW(chk.cover), feature_min: minW(chk.feature), table_mm: minW(chk.box) };
  return JSON.stringify({ fonts, wrap, images_mm, page_height_px: Math.round(pageH), chunks, est_pages: chunks.reduce((a, c) => a + c.pages, 0) });
})"""


# ── PDF 만들기 ──
def print_pdf(env, chrome, url, profile, layout_px, want_audit, css_text, cfg, base, comp_opts, page="index.html"):
    mt, mx, mb = page_margins(css_text, page)
    scale = round((A4_W_MM - 2 * mx) / 25.4 * 96 / layout_px, 4)
    ref_scale = (A4_W_MM - 2 * mx) / 25.4 * 96 / REF_LAYOUT_PX
    if not 0.1 <= scale <= 2:
        sys.exit(f"배치 폭 {layout_px}px는 너무 크거나 작습니다(축소 비율 {scale}).")
    cdp = open_cdp(env["transport"], chrome, profile, layout_px)
    try:
        sid = new_tab(cdp, REF_LAYOUT_PX)
        cdp.send("Page.navigate", {"url": url}, sid)
        ready = cdp.eval(sid, WAIT_JS)
        cdp.eval(sid, f"{ORIG_JS}({json.dumps(cfg['root'])})")             # 원본(화면 배치)의 글씨 크기 기억
        if layout_px != REF_LAYOUT_PX:
            cdp.send("Emulation.setDeviceMetricsOverride", {"width": layout_px, "height": 1400, "deviceScaleFactor": 1, "mobile": False}, sid)
            cdp.eval(sid, "new Promise((r) => setTimeout(r, 1500))")
        audit = None
        if want_audit:
            audit = json.loads(cdp.eval(sid, "JSON.stringify(PFPage.report())" if ready != "generic" else GENERIC_AUDIT_JS))
        cdp.send("Emulation.setEmulatedMedia", {"media": "print"}, sid)
        cdp.eval(sid, f"{PREP_JS}({json.dumps(css_text)}, {json.dumps(base)}, {scale})")
        pvs = cdp.eval(sid, f"{PRINT_VS_SCREEN_JS}({json.dumps(cfg['root'])})")
        canvas_stats = None
        if comp_opts and env["compress"] == "canvas":
            canvas_stats = cdp.eval(sid, f"{CANVAS_IMG_JS}({comp_opts[0]}, {comp_opts[1] / 100})")
        backdrops = cdp.eval(sid, f"{BACKDROP_JS}({cfg['contrast']}, {scale}, {json.dumps(cfg['backdrop'])})")
        keep = cdp.eval(sid, f"{KEEP_JS}({scale}, {ref_scale}, {cfg['keep']}, {cfg['ratio']}, {json.dumps(cfg['root'])}, {json.dumps(cfg['caption'])})")
        pdf = cdp.send("Page.printToPDF", {"printBackground": True, "preferCSSPageSize": True, "scale": scale,
                                           "displayHeaderFooter": False, "generateTaggedPDF": True}, sid)
        layout = None
        if want_audit:
            page_h = (A4_H_MM - mt - mb) / 25.4 * 96 / scale
            chk = {k: cfg[k] for k in ("root", "single", "cell", "cover", "feature", "box")}
            layout = json.loads(cdp.eval(sid, f"{MEASURE_JS}({scale}, {page_h}, {A4_H_MM / 25.4 * 96 / scale}, {json.dumps(chk)})"))
            layout["keep_readable"] = {"pt": cfg["keep"], **(keep or {})}
            layout["backdrops"] = backdrops or []
            layout["print_vs_screen"] = pvs
        return base64.b64decode(pdf["data"]), audit, ready, scale, layout, canvas_stats
    finally:
        cdp.close()


# ── 쪽 그림(--pages): mac = PDFKit(raster.swift) / 그 밖 = Chrome 안의 pdf.js ──
RENDER_HTML = """<!doctype html><meta charset="utf-8"><script src="%s/pdf.min.js"></script><script src="%s/pdf.worker.min.js"></script>
<script>
window.renderAll = async (file, scale, thumbW, cols) => {
  const doc = await pdfjsLib.getDocument({ url: file, disableWorker: true }).promise, pages = [], cv = [];
  for (let i = 1; i <= doc.numPages; i++) {
    const p = await doc.getPage(i), vp = p.getViewport({ scale });
    const c = document.createElement('canvas'); c.width = Math.round(vp.width); c.height = Math.round(vp.height);
    const x = c.getContext('2d'); x.fillStyle = '#fff'; x.fillRect(0, 0, c.width, c.height);
    await p.render({ canvasContext: x, viewport: vp }).promise; cv.push(c); pages.push(c.toDataURL('image/png'));
  }
  const n = cv.length, cl = Math.min(cols, Math.max(1, n)), rows = Math.ceil(n / cl), th = Math.round(thumbW * cv[0].height / cv[0].width), gap = 12;
  const s = document.createElement('canvas'); s.width = cl * thumbW + (cl + 1) * gap; s.height = rows * th + (rows + 1) * gap;
  const x = s.getContext('2d'); x.fillStyle = '#8c8c8c'; x.fillRect(0, 0, s.width, s.height);
  cv.forEach((c, i) => x.drawImage(c, gap + (i %% cl) * (thumbW + gap), gap + Math.floor(i / cl) * (th + gap), thumbW, th));
  return { pages, sheet: s.toDataURL('image/png') };
};
</script>""" % (PDFJS, PDFJS)


def rasterize(env, chrome, pdf_path, out_dir, scale):
    os.makedirs(out_dir, exist_ok=True)
    if env["raster"] == "pdfkit":
        r = subprocess.run(["swift", os.path.join(SKILL_DIR, "raster.swift"), pdf_path, out_dir, str(scale)], capture_output=True, text=True)
        if r.returncode == 0:
            return r.stdout.strip()
        print("PDFKit으로 못 그려 pdf.js로 그립니다:", (r.stderr or "")[-300:], file=sys.stderr)
    tmp = tempfile.mkdtemp(prefix="pf-pdf-raster-")
    profile = tempfile.mkdtemp(prefix="pf-pdf-")
    try:
        shutil.copy(pdf_path, os.path.join(tmp, "doc.pdf"))
        with open(os.path.join(tmp, "render.html"), "w", encoding="utf-8") as f:
            f.write(RENDER_HTML)
        server = serve(tmp)
        cdp = open_cdp(env["transport"], chrome, profile, 1200)
        try:
            sid = new_tab(cdp, 1200)
            cdp.send("Page.navigate", {"url": f"http://127.0.0.1:{server.server_address[1]}/render.html"}, sid)
            for _ in range(150):
                if cdp.eval(sid, "!!(window.pdfjsLib && window.renderAll)"):
                    break
                time.sleep(0.2)
            else:
                raise RuntimeError("pdf.js를 불러오지 못했습니다(인터넷 연결 확인).")
            res = cdp.eval(sid, f"renderAll('doc.pdf', {scale}, 300, 7)")
        finally:
            cdp.close(); server.shutdown()
        for i, u in enumerate(res["pages"], 1):
            with open(os.path.join(out_dir, f"p{i:02d}.png"), "wb") as f:
                f.write(base64.b64decode(u.split(",", 1)[1]))
        with open(os.path.join(out_dir, "sheet.png"), "wb") as f:
            f.write(base64.b64decode(res["sheet"].split(",", 1)[1]))
        return f"pages {len(res['pages'])} → {out_dir}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(profile, ignore_errors=True)


# ── 점검 도우미 ──
def compare_wraps(base_json, layout):
    """지금 배치(base_json)와 견줘 과하게 늘어난 줄바꿈: 큰 글(20px 이상)은 한 줄만 늘어도, 본문은 1.5배 이상이면서 두 줄 넘게 늘면, 새 외톨이 줄."""
    try:
        with open(base_json, encoding="utf-8") as f:
            b = {p["key"]: p for p in (json.load(f).get("layout") or {}).get("wrap", {}).get("paras", [])}
    except Exception:
        return None
    big, body, short = [], [], []
    for p in layout["wrap"].get("paras", []):
        o = b.get(p["key"])
        if not o:
            continue
        row = {"key": p["key"], "from": o["lines"], "to": p["lines"]}
        if p["lines"] > o["lines"] and p["px"] >= 20:
            big.append(row)
        elif p["lines"] >= max(o["lines"] * 1.5, o["lines"] + 2) and p["px"] < 20:
            body.append(row)
        if p["short"] > o["short"]:
            short.append(row)
    return {"big": big, "body": body, "short": short}


def pdf_facts(path):
    with open(path, "rb") as f:
        data = f.read()
    uris = sorted(set(u.decode("latin-1") for u in re.findall(rb"/URI\s*\(([^)]*)\)", data)))
    return {"pages": len(re.findall(rb"/Type\s*/Page[^s]", data)), "mb": round(len(data) / 1e6, 2),
            "links": len(uris), "local_links": [u for u in uris if re.search(r"localhost|127\.0\.0\.1", u)]}


def config_from(css):
    return {
        "keep": num_directive(css, "keep-readable", KEEP_READABLE_PT, allow_off=True),
        "ratio": num_directive(css, "ratio-limit", RATIO_LIMIT, allow_off=True),
        "contrast": max(1.0, num_directive(css, "backdrop-contrast", BACKDROP_CONTRAST)),
        "root": directive(css, "page-root", "#root"),
        "caption": directive(css, "caption", "figcaption"),
        "backdrop": directive(css, "backdrop", ""),
        "single": directive(css, "check-single-line", ""),
        "cell": directive(css, "check-table-cell", ""),
        "cover": directive(css, "check-cover-image", ""),
        "feature": directive(css, "check-feature-image", ""),
        "box": directive(css, "check-table-box", ""),
    }


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")                        # Windows(CP949)에서도 한글 이름이 깨지지 않게
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="index.html → <이름>-포트폴리오.pdf (A4)")
    ap.add_argument("--base", help="PDF에 적을 배포 주소 (기본: git remote에서 짐작)")
    ap.add_argument("--chrome", help="Chrome 실행 파일 경로")
    ap.add_argument("--page", default="index.html", help="인쇄할 페이지(레포 안 경로, 기본 index.html)")
    ap.add_argument("--out", help="저장할 파일 (기본: 레포 맨 위 <이름>-포트폴리오.pdf)")
    ap.add_argument("--report", help="점검 결과(JSON)를 쓸 파일")
    ap.add_argument("--css", help="theme/pdf.css 대신 이 CSS로 시험 인쇄(후보 비교용 — 파일은 안 바꿈)")
    ap.add_argument("--against", help="비교할 점검 결과(JSON) — 줄 수가 늘어난 글을 알려 줌")
    ap.add_argument("--layout-px", type=int, help="배치 폭(기본: PDF 배치 CSS의 /* layout-px: N */, 없으면 1040)")
    ap.add_argument("--max-px", type=int, default=1400, help="그림의 긴 변 최대 픽셀 (기본 1400)")
    ap.add_argument("--quality", type=int, default=80, help="JPEG 품질 (기본 80)")
    ap.add_argument("--no-compress", action="store_true", help="그림을 원본 그대로")
    ap.add_argument("--transport", choices=["auto", "pipe", "ws"], default="auto", help="Chrome 연결 방식(기본: mac·리눅스 pipe, Windows ws)")
    ap.add_argument("--compress", choices=["auto", "pillow", "sips", "canvas", "none"], default="auto", help="그림 압축 방식")
    ap.add_argument("--raster", choices=["auto", "pdfkit", "pdfjs"], default="auto", help="쪽 그림 방식(--pages)")
    ap.add_argument("--pages", help="쪽 그림을 이 폴더에(p01.png… + sheet.png). --from 이 없으면 --out 파일을 그림")
    ap.add_argument("--from", dest="src", help="--pages로 그릴 PDF")
    ap.add_argument("--pages-scale", type=float, default=1.5, help="쪽 그림 배율(1 = 72dpi, 기본 1.5)")
    ap.add_argument("--finalize", help="이 PDF(점검한 미리 만든 파일)를 <이름>-포트폴리오.pdf로 확정(복사)")
    ap.add_argument("--print-name", action="store_true", help="확정 파일 이름만 출력")
    ap.add_argument("--env", action="store_true", help="이 컴퓨터에서 고른 방식만 출력")
    args = ap.parse_args()
    env = pick_env(args)

    if args.print_name:
        print(pdf_name()); return
    if args.env:
        print(json.dumps({**env, "chrome": find_chrome(args.chrome), "python": sys.version.split()[0]}, ensure_ascii=False)); return
    if args.finalize:
        dst = os.path.join(ROOT, pdf_name())
        shutil.copyfile(args.finalize, dst)
        print(f"확정했습니다: {os.path.relpath(dst, ROOT)} ({os.path.getsize(dst) / 1e6:.2f} MB)"); return

    chrome = find_chrome(args.chrome)
    if not chrome:
        sys.exit("Chrome을 찾지 못했습니다. --chrome 으로 실행 파일 경로를 알려 주세요.")

    if args.pages and args.src:                                         # 그림만 그리기
        print(rasterize(env, chrome, os.path.abspath(args.src), os.path.abspath(args.pages), args.pages_scale)); return

    css_text = read_text(args.css) if args.css else read_text(PDF_CSS)
    cfg = config_from(css_text)
    layout_px = args.layout_px or int(num_directive(css_text, "layout-px", REF_LAYOUT_PX))
    base = args.base or guess_base()
    if base and not base.endswith("/"):
        base += "/"

    comp = Compressor(env["compress"], args.max_px, args.quality) if env["compress"] in ("pillow", "sips") else None
    server = serve(ROOT, comp)
    q = ("?pdf-base=" + urllib.parse.quote(base, safe="")) if base else ""
    url = f"http://127.0.0.1:{server.server_address[1]}/{urllib.parse.quote(args.page)}{q}"

    out = os.path.abspath(args.out or os.path.join(ROOT, pdf_name()))
    tmp_out = out + ".tmp"
    profile = tempfile.mkdtemp(prefix="pf-pdf-")
    try:
        data, audit, ready, scale, layout, canvas_stats = print_pdf(
            env, chrome, url, profile, layout_px, bool(args.report), css_text, cfg, base,
            (args.max_px, args.quality) if env["compress"] == "canvas" else None, args.page)
        if ready not in ("yes", "generic"):
            print(f"경고: 페이지가 다 준비되기 전에 인쇄했을 수 있습니다(ready={ready}).", file=sys.stderr)
        with open(tmp_out, "wb") as f:
            f.write(data)
        if os.path.getsize(tmp_out) < 1000:
            sys.exit("PDF를 만들지 못했습니다.")
        os.replace(tmp_out, out)
    finally:
        server.shutdown()
        shutil.rmtree(profile, ignore_errors=True)
        if comp:
            comp.close()
        if os.path.exists(tmp_out):
            os.remove(tmp_out)

    facts = pdf_facts(out)
    st = comp.stats if comp else canvas_stats
    print(f"환경: {env['os']} · Chrome 연결 {env['transport']} · 그림 압축 {env['compress']}")
    print(f"배치 폭 {layout_px}px → A4에 {scale:.0%}로 축소" + (f" · 이미 잘 보이는 글({cfg['keep']:g}pt 이상)은 키우지 않음" if cfg["keep"] and layout_px < REF_LAYOUT_PX else ""))
    print(f"저장했습니다: {os.path.relpath(out, ROOT) if out.startswith(ROOT) else out}  ({facts['pages']}쪽, {facts['mb']} MB)")
    print(f"PDF에 적힌 주소: {base or '(없음 — 페이지 주소 그대로)'}")
    if st and st.get("images"):
        print(f"그림 {st['images']}개 압축({env['compress']}): {st['before'] / 1e6:.1f} MB → {st['after'] / 1e6:.1f} MB"
              + (f", 투명해서 PNG 유지 {len(st['kept_png'])}개" if st.get("kept_png") else ""))
    for f in (st or {}).get("failed", []):
        print("  압축 실패(원본 사용):", f)
    if facts["local_links"]:
        print("경고: PDF에 localhost 링크가 남아 있습니다:", *facts["local_links"], sep="\n  ")
    if args.report:
        grew = None
        if layout:
            f = layout["fonts"]
            print(f"글씨(종이 위): 본문 {f['body_pt']}pt · 작은 글 {f['small_pt']}pt · 가장 작은 글 {f['min_pt']}pt (화면의 {f['screen_ratio']:.0%})")
            kr = layout.get("keep_readable") or {}
            if kr.get("largest"):
                print(f"글씨 비율: 원본에서 가장 큰 글('{kr['largest']['text']}' {kr['largest']['pt']}pt) 대비 비율이 가장 많이 달라진 곳 ×{kr['ratio_dev_max']}({kr['ratio_dev_at']})"
                      + (f" · 한도 ×{kr['ratio_limit']:g}로 맞춘 글 {kr['clamped']}곳" if kr.get("ratio_limit") else " · 한도 없음")
                      + "".join(f" · {g['name']} {g['pt']}pt" + ("" if g["enlarged"] else "(줄이 늘어 안 키움)") for g in kr.get("groups", [])))
            if layout.get("backdrops"):
                print("흐린 배경(그림으로 굳힘): " + " · ".join(f"{b['id']} {b['kb']}KB" + (f" 어둡게 {b['darken']:.0%}" if b['darken'] else "") + ("" if b.get("page") else " (절 배경)") for b in layout["backdrops"]))
            w, im = layout["wrap"], layout["images_mm"]
            tb = w.get("table")
            print(f"줄바꿈: 한 줄이어야 할 글이 여러 줄 {w['single_multi']}곳 · 주소 끊김 {w['url_broken']}곳 · 외톨이 줄 {w['orphans']}곳 · 문단 줄 합 {w['para_lines']}"
                  + (f" · 정보 표 가장 긴 칸 {tb['max']}줄({tb['max_at']})" if tb else ""))
            if any(v is not None for v in im.values()):
                print("종이 위 크기: " + " · ".join(f"{n} {v}mm" for n, v in (("대표 그림", im["cover_min"]), ("기능 그림", im["feature_min"]), ("정보 표", im["table_mm"])) if v is not None) + " (가장 작은 것)")
            pv = layout.get("print_vs_screen") or {}
            if pv and abs(pv.get("median", 1) - 1) > 0.1:
                print(f"알림: 이 페이지는 인쇄 규칙이 글씨 크기를 따로 정합니다(인쇄 ÷ 화면 = {pv['median']}). 인쇄용 크기 그대로 찍으려면 "
                      "theme/pdf.css에 /* layout-px: 688 */ · /* keep-readable: off */ · /* ratio-limit: off */ 로 시작하세요.")
            print("쪽 채움(덩어리마다 마지막 쪽): " + " · ".join(f"{c['at'].strip() or '?'} {c['pages']}쪽/{c['last_fill']}%" for c in layout["chunks"]))
            if args.against:
                grew = compare_wraps(args.against, layout)
                if grew is not None:
                    print(f"줄 늘어남(비교: {os.path.basename(args.against)}): 큰 글 {len(grew['big'])}곳 · 본문 크게 늘어남 {len(grew['body'])}곳 · 새 외톨이 줄 {len(grew['short'])}곳")
                    for k in ("big", "body", "short"):
                        for g in grew[k][:6]:
                            print(f"  [{k}] {g['key']}  {g['from']}→{g['to']}줄")
        rep = {"pdf": out, "base": base, "env": env, "layout_px": layout_px, "ready": ready, "grew": grew,
               "css": args.css or (PDF_CSS if os.path.isfile(PDF_CSS) else None), **facts,
               "compress": st and {**st, "tool": env["compress"]}, "page": audit, "layout": layout}
        with open(args.report, "w", encoding="utf-8") as f:
            json.dump(rep, f, ensure_ascii=False, indent=2)
        print(f"점검 결과: {args.report}")
    if args.pages:
        print(rasterize(env, chrome, out, os.path.abspath(args.pages), args.pages_scale))


if __name__ == "__main__":
    main()
