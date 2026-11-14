#!/usr/bin/env python3
"""aitjb 影片特效包 (by @ai_tjb): 37 effects in the aitjb menu, 繁體中文 captions and fonts, sound effects.
Based on the Adam Digital edition (55 effects, captions, sound) of claude-video-effects.

Built on claude-video-effects by Vibha Ramprakash (MIT). Adam Digital adds captions, sound effects,
pause trimming (trim.py), a name/handle profile and the pop-word, logo-link, card-drop and halftone-paper effects.

One effect:    python fx.py orbit in.mp4 out.mp4 --start 3.2 --end 6
Many effects:  python fx.py --plan plan.json in.mp4 out.mp4
Quick check:   python fx.py --plan plan.json in.mp4 check.png --still 4.5
Your name:     python fx.py --profile "Your Name" "@yourhandle"
List them:     python fx.py --list
"""
import argparse, json, math, os, random, re, subprocess, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))  # sibling helpers: words.py, sfx.py, logos.py
FONT = {k: os.path.join(ROOT, 'fonts', v) for k, v in {
    'bold': 'ArchivoBlack-Regular.ttf', 'serif': 'InstrumentSerif-Italic.ttf', 'mono': 'SpaceMono-Bold.ttf',
    'hand': 'PermanentMarker-Regular.ttf', 'ui': 'Inter.ttf', 'uim': 'Inter.ttf', 'uib': 'Inter.ttf', 'ui7': 'Inter.ttf',
    'anton': 'Anton-Regular.ttf', 'mont': 'Montserrat.ttf', 'monts': 'Montserrat.ttf', 'montb': 'Montserrat.ttf',
    'didone': 'PlayfairDisplay.ttf', 'didoneb': 'PlayfairDisplay.ttf', 'didonei': 'PlayfairDisplay-Italic.ttf',
    'didoneib': 'PlayfairDisplay-Italic.ttf', 'pop': 'Poppins-Black.ttf', 'popx': 'Poppins-ExtraBold.ttf', 'popb': 'Poppins-Bold.ttf'}.items()}
WGHT = {'ui': (24, 640), 'uim': (24, 540), 'uib': (32, 860), 'ui7': (32, 700), 'mont': (700,), 'monts': (600,), 'montb': (800,), 'didone': (500,), 'didoneb': (800,), 'didonei': (500,), 'didoneib': (800,)}  # Inter variable: (optical size, weight)

# Your name and handle, used by the effects that show a profile card. Saved once with --profile.
PROFILE_PATH = os.path.join(ROOT, 'profile.json')
def load_profile():
    try: p = json.load(open(PROFILE_PATH))
    except Exception: p = {}
    name = str(p.get('name') or 'Your Name').strip(); handle = str(p.get('handle') or '@yourhandle').strip()
    return {'name': name, 'handle': handle if handle.startswith('@') else '@' + handle}
PROFILE = load_profile()
CREAM, INK, PEACH, YELLOW = (244, 233, 216), (22, 22, 24), (255, 183, 165), (255, 214, 10)
NAMES = ['The Noise', 'The Lineup', 'Locked On', 'Orbit', 'Lean-In', 'Backdrop Word', 'Spotlight', 'The Bill',
         'Moody', 'Swipe', 'The To-Do', 'Comment Box', 'The Tap', 'Pause & Point', 'Uninstall', 'Reel Frame',
         'Shortcut Rain', 'Reject Stamp', 'Countdown Flip', 'Rabbit Hole', 'Cover Star', 'Scribble']
EFFECTS = {}
ALIASES = {'the-noise': 'noise', 'the-lineup': 'lineup', 'bill': 'the-bill', 'to-do': 'todo', 'the-todo': 'todo', 'the-to-do': 'todo',
           'the-tap': 'tap', 'follow': 'tap', 'comment': 'comment-box', 'pause': 'pause-point', 'pause-and-point': 'pause-point',
           'backdrop': 'backdrop-word', 'stamp': 'reject-stamp', 'countdown': 'countdown-flip', 'cover': 'cover-star', 'rain': 'shortcut-rain',
           'glass': 'glass-widgets', 'widgets': 'glass-widgets', 'collage': 'red-collage', 'split': 'split-headline', 'pastel': 'pastel-word',
           'pills': 'check-pills', 'auto-edit': 'timeline', 'headline': 'headline-box', 'wall': 'profile-wall', 'tiers': 'tier-list',
           'tier': 'tier-list', 'broll': 'broll-split', 'b-roll': 'broll-split', 'fan': 'phone-fan', 'dots': 'dot-reveal',
           'headlines': 'headline-wall', 'tasks': 'checklist',
           'liquid-glass': 'liquid-glass-graph', 'glass-graph': 'liquid-glass-graph', 'carousel': 'carousel-spin', 'match': 'match-cut',
           'toggles': 'apple-toggles', 'led': 'led-sign', 'push': 'slow-push', 'push-in': 'slow-push',
           'ots': 'over-the-shoulder-zoom', 'shoulder-zoom': 'over-the-shoulder-zoom', 'corner-zoom': 'over-the-shoulder-zoom',
           'tape': 'tape-label', 'select': 'select-resize', 'resize': 'select-resize', 'wave': 'wave-trim', 'strike': 'huge-strike', 'crayon': 'crayon-write', 'deal': 'fan-build', 'imessage': 'messages', 'texts': 'messages', 'notifications': 'messages', 'grid': 'place-in-grid', 'profile-grid': 'place-in-grid',
           'pop': 'pop-word', 'big-word': 'pop-word', 'logo': 'logo-link', 'logos': 'logo-link', 'link': 'logo-link',
           'card': 'card-drop', 'drop': 'card-drop', 'paper': 'halftone-paper', 'halftone': 'halftone-paper',
           'caption': 'captions', 'subtitles': 'captions', 'subs': 'captions',
           # aitjb：頁面上的寫法 (底線) 和中文名都能用
           'ui_world': 'ui-world', 'ui world': 'ui-world', 'phone mockup': 'phone-mockup', 'glass type': 'glass-type', 'chart grow': 'chart-grow',
           'paper_cut': 'paper-cut', 'paper cut': 'paper-cut', 'doodle boil': 'doodle-boil', 'headline wall': 'headline-wall',
           'cover story': 'cover-story', 'frame break': 'frame-break', 'glass_widgets': 'glass-widgets', 'carousel_spin': 'carousel-spin',
           '彈跳長條圖': 'split-graph', '繞頭轉圈': 'orbit', '剪輯時間軸': 'timeline', '設定開關': 'apple-toggles', '透明面板': 'glass-widgets',
           '勾選按鈕': 'check-pills', '隧道': 'rabbit-hole', '紅色拼貼': 'red-collage', '大字拼貼': 'red-collage', '旋轉木馬': 'carousel-spin', '玻璃圖表': 'liquid-glass-graph',
           '待辦清單': 'checklist', 'led看板': 'led-sign', '新聞切換': 'match-cut', '肩後拉近': 'over-the-shoulder-zoom', '發光字': 'spotlight',
           '聊天畫面': 'ui-world', '手機模型': 'phone-mockup', '玻璃字': 'glass-type', '發光折線': 'chart-grow', '剪紙拼貼': 'paper-cut',
           '訊息通知': 'messages', '蠟筆塗鴉': 'doodle-boil', '標題牆': 'headline-wall', '雜誌封面': 'cover-story', '衝出手機': 'frame-break',
           '分身': 'clone-row', '分身列隊': 'clone-row', '程式碼身體': 'code-body', '文字俯衝': 'letter-dive', '斬擊': 'blade-slice', '斬擊切片': 'blade-slice',
           '報紙頭版': 'press-front', '頭頂疊標籤': 'head-stack', '紙鈔': 'banknote', '即時游標': 'live-cursor', '游標': 'live-cursor',
           '撕報紙': 'paper-tear', '漫畫': 'impact-frame', '漫畫衝擊格': 'impact-frame', '隨風消散': 'blow-away', '鉛筆手寫字': 'sketch-words', '手寫字': 'sketch-words',
           '字幕': 'captions', 'clones': 'clone-row', 'matrix': 'code-body', 'slice': 'blade-slice', 'newspaper': 'press-front', 'tags': 'head-stack',
           'money': 'banknote', 'cursor': 'live-cursor', 'tear': 'paper-tear', 'manga': 'impact-frame', 'dust': 'blow-away', 'sketch': 'sketch-words'}
LOOK_NAMES = {'glitter-spotlight': ('spotlight', 'sparkle'), 'glitter': ('spotlight', 'sparkle')}  # a named look of another effect
CARD_FX = ('ui-world', 'fan-build', 'noise', 'orbit', 'carousel-spin', 'place-in-grid', 'check-pills', 'profile-wall', 'phone-fan', 'broll-split', 'timeline')


def effect(name, desc):
    def deco(fn):
        EFFECTS[name] = (fn, desc)
        return fn
    return deco


# ---------- small helpers ----------
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease_out(x): x = clamp(x); return 1 - (1 - x) ** 3
def ease_inout(x): x = clamp(x); return 3 * x * x - 2 * x * x * x
def ease_back(x): x = clamp(x); s = 1.7; x -= 1; return x * x * ((s + 1) * x + s) + 1
def ramp(c, e, t_in=0.25, t_out=0.2): return clamp(c.lt / t_in) * clamp((e.d - c.lt) / t_out) if t_out else clamp(c.lt / t_in)
def rgb(v, default):
    if v is None: return default
    if isinstance(v, (list, tuple)): return tuple(int(x) for x in v[:3])
    v = str(v).lstrip('#'); return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))


# ---------- 繁體中文：字串裡有中文時，自動換成同風格的繁中字體 ----------
# 每個拉丁字體都配一個繁中字體 (檔名, 字重)。Noto 字體也有拉丁字母，所以中英混排不會缺字。
TC_FONT = {'sans': 'NotoSansTC.ttf', 'serif': 'NotoSerifTC.ttf', 'hand': 'LXGWWenKaiTC-Medium.ttf', 'round': 'jf-openhuninn.ttf'}
TC_MAP = {'bold': ('sans', 900), 'anton': ('sans', 900), 'pop': ('sans', 900), 'popx': ('sans', 800), 'popb': ('sans', 700),
          'uib': ('sans', 800), 'ui7': ('sans', 700), 'montb': ('sans', 800), 'mont': ('sans', 700), 'monts': ('sans', 600),
          'ui': ('sans', 600), 'uim': ('sans', 500), 'mono': ('sans', 700),
          'serif': ('serif', 700), 'didone': ('serif', 600), 'didoneb': ('serif', 900), 'didonei': ('serif', 600), 'didoneib': ('serif', 900),
          'hand': ('hand', None), 'round': ('round', None),
          'tc': ('sans', 900), 'tcm': ('sans', 500), 'tcserif': ('serif', 900), 'tchand': ('hand', None)}
_CJK = re.compile(r'[⺀-鿿豈-﫿　-〿＀-￯]')
def has_cjk(s): return isinstance(s, str) and bool(_CJK.search(s))

_tcc = {}
def tc_font(kind, size):
    fam, w = TC_MAP.get(kind, ('sans', 700))
    k = (fam, w, int(size))
    if k not in _tcc:
        f = ImageFont.truetype(os.path.join(ROOT, 'fonts', TC_FONT[fam]), max(6, int(size)))
        if w:
            try: f.set_variation_by_axes([w])
            except Exception: pass
        _tcc[k] = f
    return _tcc[k]


def _install_tc_fallback():
    """Every Latin font made by font() remembers its Chinese twin. Any measuring or drawing call
    with Chinese text quietly uses the twin, so all effects work in 繁體中文 without changes."""
    F = ImageFont.FreeTypeFont
    for name in ('getbbox', 'getlength', 'getmask', 'getmask2'):
        orig = getattr(F, name)
        def wrap(self, text, *a, _o=orig, **k):
            tw = getattr(self, '_tc', None)
            if tw is not None and has_cjk(text): return _o(tw, text, *a, **k)
            return _o(self, text, *a, **k)
        setattr(F, name, wrap)
_install_tc_fallback()


_fc = {}
def font(kind, size):
    k = (kind, int(size))
    if k not in _fc:
        if kind in ('tc', 'tcm', 'tcserif', 'tchand', 'round'):
            f = tc_font(kind, size)  # a Chinese-first font, asked for by name
        else:
            f = ImageFont.truetype(FONT[kind], max(6, int(size)))
            if kind in WGHT:
                try: f.set_variation_by_axes(list(WGHT[kind]))
                except Exception: pass
            f._tc = tc_font(kind, size)
        _fc[k] = f
    return _fc[k]


def text_img(s, size, kind='bold', fill=(255, 255, 255), stroke=0, stroke_fill=INK, shadow=0, glow=None):
    f = font(kind, size)
    bb = f.getbbox(s, stroke_width=stroke)
    pad = int(size * 0.2 + shadow * 2.5 + (glow[1] * 2.5 if glow else 0)) + 4
    w, h = bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad
    pos = (pad - bb[0], pad - bb[1])
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    if shadow:
        sh = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((pos[0], pos[1] + shadow * 0.5), s, font=f, fill=(0, 0, 0, 160), stroke_width=stroke)
        im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(shadow)))
    if glow:
        g = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(g).text(pos, s, font=f, fill=tuple(glow[0]) + (255,), stroke_width=int(size * 0.04))
        g = g.filter(ImageFilter.GaussianBlur(glow[1]))
        im = Image.alpha_composite(Image.alpha_composite(im, g), g)
    ImageDraw.Draw(im).text(pos, s, font=f, fill=tuple(fill) + (255,), stroke_width=stroke, stroke_fill=tuple(stroke_fill) + (255,))
    return im


def fit_text(s, max_w, kind='bold', start=400, **kw):
    size = start
    while size > 10 and font(kind, size).getlength(s) > max_w: size = int(size * 0.92)
    return text_img(s, size, kind, **kw)


def rrect(w, h, r, fill, outline=None, width=0):
    im = Image.new('RGBA', (int(w), int(h)), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, int(w) - 1, int(h) - 1], int(r), fill=fill, outline=outline, width=width)
    return im


def shadowed(im, blur=18, dy=10, alpha=120):
    pad = blur * 2 + abs(dy)
    out = Image.new('RGBA', (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    a = im.split()[3].point(lambda v: v * alpha // 255)
    sh = Image.new('RGBA', im.size, (0, 0, 0, 255)); sh.putalpha(a)
    out.paste(sh, (pad, pad + dy), sh)
    out = out.filter(ImageFilter.GaussianBlur(blur))
    out.alpha_composite(im, (pad, pad))
    return out


def to_np(im): return np.asarray(im.convert('RGBA'), dtype=np.float32) / 255.0


def comp(c, layer, x, y, alpha=1.0, behind=False, guard=False):
    """Alpha-composite an RGBA layer with its top-left at (x, y).
    behind=True hides it wherever the person is (so it sits behind you).
    guard=True only hides it where it would cover your face."""
    L = to_np(layer) if isinstance(layer, Image.Image) else layer
    h, w = L.shape[:2]; x, y = int(round(x)), int(round(y))
    x0, y0, x1, y1 = max(0, x), max(0, y), min(c.W, x + w), min(c.H, y + h)
    if x1 <= x0 or y1 <= y0 or alpha <= 0: return
    L = L[y0 - y:y1 - y, x0 - x:x1 - x]
    a = L[..., 3:4] * alpha
    m = c.m[y0:y1, x0:x1, None]
    if behind: a = a * (1 - m)
    elif guard:
        yy, xx = np.ogrid[y0:y1, x0:x1]
        e = ((xx - c.fx) / (c.fw * 0.95)) ** 2 + ((yy - c.fy) / (c.fw * 1.35)) ** 2
        a = a * (1 - np.clip((1.2 - e) / 0.3, 0, 1)[..., None] * m)
    dst = c.img[y0:y1, x0:x1]
    dst[:] = dst * (1 - a) + L[..., :3] * a


def place(c, im, cx, cy, scale=1.0, rot=0.0, alpha=1.0, behind=False, guard=False):
    """Draw a PIL image centred on (cx, cy), scaled and rotated (degrees, counter-clockwise)."""
    if scale <= 0.01 or alpha <= 0: return
    if abs(scale - 1) > 0.005:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
    if abs(rot) > 0.05: im = im.rotate(rot, Image.BICUBIC, expand=True)
    comp(c, im, cx - im.width / 2, cy - im.height / 2, alpha, behind, guard)


def camera(c, zoom, cx, cy):
    """Zoom the whole frame (and the person mask) towards (cx, cy). Capped at 2x so it stays sharp."""
    zoom = min(zoom, 2.0)
    if zoom <= 1.002: return
    cw, ch = c.W / zoom, c.H / zoom
    x0 = clamp(cx - cw / 2, 0, c.W - cw); y0 = clamp(cy - ch / 2, 0, c.H - ch)
    M = np.float32([[zoom, 0, -x0 * zoom], [0, zoom, -y0 * zoom]])
    c.img = cv2.warpAffine(c.img, M, (c.W, c.H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    c.m = cv2.warpAffine(c.m, M, (c.W, c.H), flags=cv2.INTER_LINEAR)
    c.fx, c.fy, c.fw = (c.fx - x0) * zoom, (c.fy - y0) * zoom, c.fw * zoom


def face_cam(c, zoom, head_at=0.40):
    """Zoom on the face, keeping it at `head_at` of the frame height."""
    z = min(zoom, 2.0)
    camera(c, z, c.fx, c.fy + (c.H / z) * (0.5 - head_at))


def grade(img, kind='moody'):
    lum = (img @ np.float32([0.299, 0.587, 0.114]))[..., None]
    if kind == 'bw':
        g = np.clip((lum - 0.5) * 1.25 + 0.5, 0, 1); return np.repeat(g, 3, axis=2)
    if kind == 'warm': return np.clip(img * np.float32([1.08, 1.0, 0.86]) + 0.02, 0, 1)
    if kind == 'cool': return np.clip(img * np.float32([0.9, 1.0, 1.1]), 0, 1)
    if kind == 'pop':
        o = lum + (img - lum) * 1.35; return np.clip((o - 0.5) * 1.12 + 0.5, 0, 1)
    # moody: a little darker, softer colour, teal shadows, warm highlights, gentle contrast
    o = lum + (img - lum) * 0.6
    o = np.power(np.clip(o, 0, 1), 1.3) * 0.88
    o = o + (1 - lum) * np.float32([-0.03, 0.035, 0.065]) + lum * np.float32([0.05, 0.015, -0.04])
    o = np.clip((o - 0.42) * 1.12 + 0.42, 0, 1)
    return o


_vig = {}
def vignette(c, strength=0.35):
    k = (c.W, c.H)
    if k not in _vig:
        yy, xx = np.ogrid[0:c.H, 0:c.W]
        d = ((xx - c.W / 2) / (c.W * 0.75)) ** 2 + ((yy - c.H / 2) / (c.H * 0.7)) ** 2
        _vig[k] = np.clip(d, 0, 1).astype(np.float32)
    c.img *= (1 - strength * _vig[k])[..., None]


def card(im, w, radius=0.07):
    """A reel-shaped (9:16) rounded card with a soft shadow."""
    h = int(w * 16 / 9)
    src = im.convert('RGB'); sw, sh = src.size
    s = max(w / sw, h / sh)
    src = src.resize((max(w, int(sw * s)), max(h, int(sh * s))), Image.LANCZOS)
    l, t = (src.width - w) // 2, (src.height - h) // 2
    src = src.crop((l, t, l + w, t + h)).convert('RGBA')
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], int(w * radius), fill=255)
    src.putalpha(m)
    ImageDraw.Draw(src).rounded_rectangle([0, 0, w - 1, h - 1], int(w * radius), outline=(0, 0, 0, 70), width=2)
    return shadowed(src, blur=max(6, w // 16), dy=w // 22, alpha=150)


def vary(im, i):
    """Give each card its own look, so a pile of frames reads as different reels."""
    kind = ('pop', 'bw', 'warm', 'cool', 'moody')[i % 5]
    a = np.asarray(im.convert('RGB'), np.float32) / 255
    return Image.fromarray((grade(a, kind) * 255).astype(np.uint8))


def cached(e, key, fn):
    if key not in e.state: e.state[key] = fn()
    return e.state[key]


# ---------- the 22 effects ----------
@effect('noise', 'reels pile up behind your head, one every quarter second')
def fx_noise(c, e):
    cw = int(c.W * float(e.o.get('size', 0.34)))
    def setup():
        rnd = random.Random(7); n = min(16, max(4, int(e.d / 0.22)))
        return [(rnd.uniform(0.14, 0.86), rnd.uniform(0.12, 0.52), rnd.uniform(-7, 7)) for _ in range(n)]
    pos = cached(e, 'pos', setup)
    cards = cached(e, 'cards', lambda: [card(vary(im, i) if e.o.get('images') is None else im, cw) for i, im in enumerate(e.cards)])
    out = clamp((e.d - c.lt) / 0.2)
    for i, (x, y, r) in enumerate(pos):
        t0 = i * 0.22
        if c.lt < t0: break
        k = ease_back((c.lt - t0) / 0.25)
        place(c, cards[i % len(cards)], x * c.W, y * c.H, 0.6 + 0.4 * k, r, clamp((c.lt - t0) / 0.08) * out, behind=True)


@effect('lineup', 'numbered tiles fan out in an arc above your head')
def fx_lineup(c, e):
    names = e.o.get('text', '|'.join(NAMES)).split('|')
    tw = int(c.W * 0.105)
    def tile(i, name):
        im = rrect(tw, int(tw * 1.25), tw * 0.16, (24, 24, 28, 225), (255, 255, 255, 60), 2)
        d = ImageDraw.Draw(im)
        num = text_img(f'{i + 1:02d}', tw * 0.42, 'serif', CREAM)
        im.alpha_composite(num, ((tw - num.width) // 2, int(tw * 0.04)))
        words = name.split(' ')
        lines = [' '.join(words[:len(words) // 2 or 1]), ' '.join(words[len(words) // 2 or 1:])] if len(name) > 10 else [name]
        f = font('ui', tw * 0.15)
        for j, ln in enumerate([l for l in lines if l]):
            d.text((tw / 2, tw * (0.78 + 0.19 * j)), ln, font=f, fill=(255, 255, 255, 235), anchor='mm')
        return shadowed(im, 8, 5, 90)
    tiles = cached(e, 'tiles', lambda: [tile(i, n) for i, n in enumerate(names)])
    n = len(tiles); outer = math.ceil(n / 2 + 0.5); inner = n - outer
    cx, cy = c.W / 2 * 0.6 + c.fx * 0.4, c.fy + c.fw * 0.3
    slots = []
    for row, cnt, R in ((0, outer, c.W * 0.47), (1, inner, c.W * 0.33)):
        for k in range(cnt):
            a = math.pi * (0.94 - 0.88 * k / max(1, cnt - 1))
            slots.append((cx + R * math.cos(a), cy - R * math.sin(a) * 1.05, math.degrees(a - math.pi / 2) * 0.3))
    out = clamp((e.d - c.lt) / 0.2)
    for i, (x, y, r) in enumerate(slots[:n]):
        t0 = 0.035 * i
        if c.lt < t0: continue
        k = ease_back((c.lt - t0) / 0.3)
        place(c, tiles[i], x, y + (1 - k) * 40, 0.5 + 0.5 * k, r, clamp((c.lt - t0) / 0.1) * out, behind=True)


@effect('locked-on', 'corner brackets snap onto your face and the camera follows you')
def fx_locked_on(c, e):
    face_cam(c, 1 + (float(e.o.get('zoom', 1.35)) - 1) * ease_out(c.lt / 0.6))
    snap = ease_out(c.lt / 0.22); s = c.fw * 0.85 * (1 + 0.6 * (1 - snap))
    al = clamp(c.lt / 0.12) * clamp((e.d - c.lt) / 0.2)
    size = int(2 * s + 40); im = Image.new('RGBA', (size, int(size * 1.25)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = 20, 20, size - 20, im.height - 20; L = int(s * 0.32); wd = max(4, int(c.W / 200))
    for (px, py, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        d.line([(px, py + dy * L), (px, py), (px + dx * L, py)], fill=(255, 255, 255, 255), width=wd, joint='curve')
    place(c, shadowed(im, 6, 2, 120), c.fx, c.fy, alpha=al)
    tag = text_img(e.o.get('text', 'LOCKED ON').upper(), c.W * 0.022, 'mono', INK)
    pill = rrect(tag.width + 10, tag.height, tag.height / 2, (255, 255, 255, 235)); pill.alpha_composite(tag, (5, 0))
    place(c, pill, c.fx, c.fy + s * 1.25 + pill.height, alpha=clamp((c.lt - 0.15) / 0.15) * al, guard=True)


@effect('orbit', 'your reels circle your head: in front at the bottom, behind you at the top')
def fx_orbit(c, e):
    K = int(e.o.get('count', 6)); cw = int(c.W * float(e.o.get('size', 0.2)))
    cards = cached(e, 'cards', lambda: [card(vary(im, i) if e.o.get('images') is None else im, cw) for i, im in enumerate(e.cards)])
    intro, out = ease_out(c.lt / 0.4), clamp((e.d - c.lt) / 0.25)
    rx, ry = c.W * 0.38 * intro, max(c.fw * 1.5, c.H * 0.1)
    oy = c.fy + c.fw * 0.9
    items = []
    for i in range(K):
        th = i * 2 * math.pi / K + c.lt * float(e.o.get('speed', 1.9))
        items.append((math.sin(th), th, i))
    for depth, th, i in sorted(items):
        place(c, cards[i % len(cards)], c.fx + rx * math.cos(th), oy + ry * math.sin(th), (0.78 + 0.24 * (depth + 1) / 2) * (0.5 + 0.5 * intro),
              -6 * math.cos(th), out * clamp(c.lt / 0.15), behind=depth < 0, guard=depth >= 0)


@effect('lean-in', 'a fast punch-in on one word')
def fx_lean_in(c, e):
    z = float(e.o.get('zoom', 1.45))
    face_cam(c, 1 + (z - 1) * ease_out(c.lt / float(e.o.get('speed', 0.18))), 0.42)


@effect('backdrop-word', 'a giant word drops in behind you')
def fx_backdrop_word(c, e):
    word = e.o.get('text', 'CLAUDE')
    im = cached(e, 'w', lambda: fit_text(word, c.W * 0.94, e.o.get('font', 'bold'), fill=rgb(e.o.get('color'), CREAM), shadow=10))
    k = ease_back(c.lt / 0.42)
    y_end = c.fy - c.fw * 1.05
    y = -im.height + (y_end + im.height) * k
    place(c, im, c.W / 2 * 0.6 + c.fx * 0.4, y, alpha=clamp((e.d - c.lt) / 0.2), behind=True)


_grid = {}
def grid(c):
    if (c.W, c.H) not in _grid:
        yy, xx = np.mgrid[0:c.H, 0:c.W].astype(np.float32); _grid[(c.W, c.H)] = (xx, yy)
    return _grid[(c.W, c.H)]


@effect('spotlight', 'kill the lights, keep you lit')
def fx_spotlight(c, e):
    if e.o.get('look') == 'sparkle': return spotlight_sparkle(c, e)
    face_cam(c, 1 + (float(e.o.get('push', 1.1)) - 1) * ease_inout(c.lt / e.d))
    k = ramp(c, e, 0.3, 0.25)
    xx, yy = grid(c)
    d = ((xx - c.fx) / (c.W * 0.5)) ** 2 + ((yy - (c.fy + c.H * 0.2)) / (c.H * 0.46)) ** 2
    pool = np.clip(1 - d, 0, 1) ** 1.6
    bright = 1 - k * (1 - (0.2 + 0.45 * pool))
    f = bright * (1 - c.m) + c.m * (1 + 0.04 * k)
    if e.o.get('text'):
        word = e.o['text']; col = rgb(e.o.get('color'), PEACH)
        im = cached(e, 'w', lambda: fit_text(word, c.W * 0.9, e.o.get('font', 'serif'), fill=col, glow=(col, 26)))
        c.img *= f[..., None]
        place(c, im, c.W / 2, c.fy - c.fw * 1.1, alpha=k, behind=True)
    else:
        c.img *= f[..., None]


@effect('the-bill', 'prints every instruction like a ticket, into the wall above your head')
def fx_bill(c, e):
    lines = e.o.get('text', 'ORDER #1021|1x orbit|1x spotlight|1x lean-in|cut the dead air|TOTAL: 1 prompt').split('|')
    def build():
        pw = int(c.W * 0.5); lh = int(pw * 0.085); pad = int(pw * 0.08)
        h = pad * 2 + lh * (len(lines) + 1)
        im = Image.new('RGBA', (pw, h), CREAM + (255,)); d = ImageDraw.Draw(im)
        f = font('mono', lh * 0.62)
        for i, ln in enumerate(lines):
            y = pad + lh * i + (lh if i == len(lines) - 1 else 0)
            if i == len(lines) - 1:
                for x in range(pad, pw - pad, 14): d.line([(x, y - lh * 0.45), (x + 7, y - lh * 0.45)], fill=INK + (140,), width=2)
            d.text((pad, y), ln, font=f, fill=INK + (255,))
        return im
    rec = cached(e, 'r', build)
    slot_y, sw = c.H * 0.075, c.W * 0.62
    max_h = max(80, c.fy - c.fw * 1.3 - slot_y)
    s = min(1.0, max_h / rec.height)
    pr = ease_inout(c.lt / (e.d * 0.75)); L = int(rec.height * pr)
    al = clamp((e.d - c.lt) / 0.25)
    cx = c.W / 2
    if L > 2:
        paper = rec.crop((0, 0, rec.width, L))
        z = 14; jag = Image.new('RGBA', (rec.width, L + z), (0, 0, 0, 0)); jag.paste(paper, (0, 0))
        ImageDraw.Draw(jag).polygon([(x, L) for x in range(0, rec.width + 1, 2 * z)] + [(rec.width, L)] +
                                    [(x + z, L + z) for x in range(rec.width - 2 * z, -1, -2 * z)], fill=CREAM + (255,))
        paper = shadowed(jag, 10, 6, 90)
        if s < 1: paper = paper.resize((int(paper.width * s), int(paper.height * s)), Image.BILINEAR)
        comp(c, paper, cx - paper.width / 2, slot_y - 10 * s, al, behind=True)
    slot = rrect(sw, c.H * 0.03, c.H * 0.015, (30, 30, 34, 255), (90, 90, 96, 255), 3)
    place(c, shadowed(slot, 10, 6, 140), cx, slot_y, alpha=al * clamp(c.lt / 0.15), behind=True)


@effect('moody', 'a moody colour grade: darker, softer, teal shadows')
def fx_moody(c, e):
    k = ramp(c, e, 0.35, 0)
    c.img = c.img * (1 - k) + grade(c.img, e.o.get('grade', 'moody')) * k
    vignette(c, 0.4 * k)


@effect('swipe', 'a before and after slider that sweeps across you')
def fx_swipe(c, e):
    after = grade(c.img, e.o.get('grade', 'moody'))
    p = c.lt / e.d
    sp = 1.05 - 0.95 * ease_inout(p / 0.5) if p < 0.5 else 0.1 + 0.4 * ease_inout((p - 0.5) / 0.4)
    xx, yy = grid(c)
    line = sp * c.W + 0.22 * (yy - c.H / 2)
    a = np.clip((xx - line) / 3 + 0.5, 0, 1)[..., None]
    c.img = c.img * (1 - a) + after * a
    hy = c.H * 0.62; hx = sp * c.W + 0.22 * (hy - c.H / 2)
    edge = np.clip(1 - np.abs(xx - line) / 3.5, 0, 1)[..., None]
    c.img = c.img * (1 - edge) + edge
    r = int(c.W * 0.035); h = Image.new('RGBA', (2 * r + 4, 2 * r + 4), (0, 0, 0, 0)); d = ImageDraw.Draw(h)
    d.ellipse([2, 2, 2 * r + 2, 2 * r + 2], fill=(255, 255, 255, 255))
    d.text((r + 2, r + 2), '< >', font=font('mono', r * 0.7), fill=INK + (255,), anchor='mm')
    place(c, shadowed(h, 8, 4, 110), hx, hy)
    for lab, x in (('before', 0.14), ('after', 0.86)):
        t = text_img(lab, c.W * 0.03, 'serif', INK); pill = rrect(t.width + 16, t.height, t.height / 2, (255, 255, 255, 225))
        pill.alpha_composite(t, (8, 0)); place(c, pill, c.W * x, c.H * 0.88)


@effect('todo', 'a checklist card beside your head that ticks off as you talk')
def fx_todo(c, e):
    items = e.o.get('text', 'drop your video into Claude|install the skill|type /effects').split('|')
    # ticks = video seconds when each item gets ticked (e.g. when you say it); default is evenly spaced
    ticks = [float(t) - e.start for t in str(e.o['ticks']).split('|')] if e.o.get('ticks') else [e.d * (i + 1) / (len(items) + 1) for i in range(len(items))]
    cw = int(c.W * 0.5); lh = int(cw * 0.13); pad = int(cw * 0.07)
    im = rrect(cw, pad * 2 + lh * (len(items) + 1), cw * 0.07, (250, 248, 242, 235)); d = ImageDraw.Draw(im)
    done = sum(c.lt >= t for t in ticks)
    d.text((pad, pad), e.o.get('title', 'TO DO').upper(), font=font('ui', lh * 0.42), fill=(200, 140, 20, 255))
    d.text((cw - pad, pad), f'{done} of {len(items)}', font=font('ui', lh * 0.36), fill=(120, 120, 120, 255), anchor='ra')
    f = font('ui', lh * 0.4)
    for i, it in enumerate(items):
        y = pad + lh * (i + 1); bx = lh * 0.42
        d.rounded_rectangle([pad, y + lh * 0.12, pad + bx, y + lh * 0.12 + bx], 6, outline=(160, 160, 160, 255), width=3)
        d.text((pad + bx * 1.5, y + lh * 0.1), it, font=f, fill=INK + (255,))
        if c.lt >= ticks[i]:
            k = ease_out((c.lt - ticks[i]) / 0.25)
            d.rounded_rectangle([pad, y + lh * 0.12, pad + bx, y + lh * 0.12 + bx], 6, fill=(52, 199, 89, 255))
            d.line([(pad + bx * .22, y + lh * .12 + bx * .52), (pad + bx * .42, y + lh * .12 + bx * .74), (pad + bx * .8, y + lh * .12 + bx * .28)], fill=(255, 255, 255, 255), width=4)
            tw = f.getlength(it) * k
            d.line([(pad + bx * 1.5, y + lh * 0.36), (pad + bx * 1.5 + tw, y + lh * 0.36)], fill=INK + (255,), width=3)
    left = c.fx > c.W / 2
    x = c.W * 0.05 + cw / 2 if left else c.W * 0.95 - cw / 2
    pop = ease_back(c.lt / 0.3)
    place(c, shadowed(im, 14, 8, 90), x, max(im.height / 2 + c.H * 0.06, c.fy - c.fw * 1.4), 0.8 + 0.2 * pop, 0, clamp(c.lt / 0.12) * clamp((e.d - c.lt) / 0.2), behind=True)


def heart(size, color=(255, 48, 64)):
    s = int(size); im = Image.new('RGBA', (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    pts = [(s / 2 + s * 0.48 * (16 * math.sin(t) ** 3) / 16, s * 0.46 - s * 0.46 * (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)) / 16)
           for t in np.linspace(0, 2 * math.pi, 60)]
    d.polygon(pts, fill=color + (255,)); return im


def comment_bar(c, e):
    word = e.o.get('text', 'EFFECTS')
    bw, bh = int(c.W * 0.9), int(c.W * 0.11)
    slide = ease_out(c.lt / 0.3); y = c.H * 0.8 + (1 - slide) * c.H * 0.25
    type_t, post_t = 0.35, 0.35 + 0.08 * len(word) + 0.25
    typed = word[:int(clamp((c.lt - type_t) / (0.08 * len(word))) * len(word) + 0.001)] if c.lt < post_t else ''
    im = rrect(bw, bh, bh / 2, (255, 255, 255, 245)); d = ImageDraw.Draw(im)
    r = bh * 0.32; d.ellipse([bh * 0.2, bh / 2 - r, bh * 0.2 + 2 * r, bh / 2 + r], fill=(214, 41, 118, 255))
    f = font('ui', bh * 0.3)
    if typed: d.text((bh * 0.95, bh / 2), typed + ('|' if int(c.lt * 4) % 2 else ''), font=f, fill=INK + (255,), anchor='lm')
    elif c.lt < post_t: d.text((bh * 0.95, bh / 2), 'Add a comment...', font=f, fill=(150, 150, 150, 255), anchor='lm')
    d.text((bw - bh * 0.4, bh / 2), 'Post', font=f, fill=((0, 149, 246, 255) if typed else (180, 210, 240, 255)), anchor='rm')
    al = clamp((e.d - c.lt) / 0.2)
    place(c, shadowed(im, 14, 6, 100), c.W / 2, y, alpha=al, guard=True)
    if c.lt >= post_t:
        k = ease_back((c.lt - post_t) / 0.3)
        b = rrect(int(c.W * 0.52), int(bh * 0.85), bh * 0.3, (255, 255, 255, 240)); bd = ImageDraw.Draw(b)
        bd.text((bh * 0.3, b.height * 0.32), 'you', font=font('ui', bh * 0.2), fill=(120, 120, 120, 255), anchor='lm')
        bd.text((bh * 0.3, b.height * 0.66), word, font=font('ui', bh * 0.3), fill=INK + (255,), anchor='lm')
        hk = ease_back((c.lt - post_t - 0.3) / 0.3)
        if hk > 0:
            hh = heart(bh * 0.4 * hk); b.alpha_composite(hh, (int(b.width - bh * 0.3 - hh.width), int(b.height / 2 - hh.height / 2)))
        place(c, shadowed(b, 12, 5, 90), c.W * 0.07 + b.width / 2, y - bh * 1.05, 0.7 + 0.3 * k, 0, al * clamp((c.lt - post_t) / 0.1), guard=True)


@effect('tap', 'a Follow button pops up and flips to Following')
def fx_tap(c, e):
    at = float(e.o['at']) - e.start if 'at' in e.o else e.d * 0.45  # 'at' = video second of the tap
    bw, bh = int(c.W * 0.3), int(c.W * 0.09)
    x = clamp(float(e.o['x']) * c.W if 'x' in e.o else c.fx + c.fw * 1.9, bw / 2 + 30, c.W - bw / 2 - 30)
    y = clamp(float(e.o['y']) * c.H if 'y' in e.o else c.fy + c.fw * 1.6, bh + 30, c.H - bh - 30)
    on = c.lt >= at
    col = rgb(e.o.get('color'), (124, 92, 255)) if on else (0, 149, 246)
    im = rrect(bw, bh, bh * 0.28, col + (255,)); d = ImageDraw.Draw(im)
    d.text((bw / 2, bh / 2), 'Following' if on else '+ Follow', font=font('ui', bh * 0.4), fill=(255, 255, 255, 255), anchor='mm')
    pop = ease_back(c.lt / 0.3)
    sq = 1.0
    if on: q = (c.lt - at) / 0.3; sq = 1 - 0.12 * math.sin(math.pi * clamp(q)) if q < 1 else 1
    place(c, shadowed(im, 12, 6, 110), x, y, (0.6 + 0.4 * pop) * sq, 0, clamp(c.lt / 0.1) * clamp((e.d - c.lt) / 0.2), guard=True)
    if on and c.lt - at < 0.4:
        q = (c.lt - at) / 0.4; r = int(bh * (0.3 + 0.9 * q)); ring = Image.new('RGBA', (2 * r + 8, 2 * r + 8), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse([4, 4, 2 * r + 4, 2 * r + 4], outline=(255, 255, 255, int(220 * (1 - q))), width=5)
        place(c, ring, x, y, guard=True)


def hand_path(d, pts, color, width, frac):
    n = max(2, int(len(pts) * clamp(frac)))
    if frac > 0: d.line(pts[:n], fill=color, width=width, joint='curve')
    return pts[n - 1]


def arrow_pts(x0, y0, x1, y1, bend=0.25, n=40):
    mx, my = (x0 + x1) / 2 - (y1 - y0) * bend, (y0 + y1) / 2 + (x1 - x0) * bend
    return [((1 - t) ** 2 * x0 + 2 * (1 - t) * t * mx + t * t * x1, (1 - t) ** 2 * y0 + 2 * (1 - t) * t * my + t * t * y1) for t in np.linspace(0, 1, n)]


def arrow_head(d, pts, color, width, size):
    (xa, ya), (xb, yb) = pts[-4], pts[-1]; a = math.atan2(yb - ya, xb - xa)
    for s in (2.6, -2.6):
        d.line([(xb, yb), (xb + size * math.cos(a + s), yb + size * math.sin(a + s))], fill=color, width=width)


@effect('pause-point', 'freeze the frame and point at something with a hand-drawn arrow')
def fx_pause_point(c, e):
    if 'f' not in e.state: e.state['f'] = (c.img.copy(), c.m.copy(), c.fx, c.fy, c.fw)
    img, m, c.fx, c.fy, c.fw = e.state['f']; c.img, c.m = img.copy(), m
    face_cam(c, 1 + 0.06 * ease_out(c.lt / e.d), 0.4)
    c.img = c.img * 0.92 + grade(c.img, 'bw') * 0.08
    col = rgb(e.o.get('color'), YELLOW) + (255,)
    lay = Image.new('RGBA', (c.W, c.H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle([c.W * 0.05, c.H * 0.06, c.W * 0.05 + c.W * 0.1, c.H * 0.06 + c.W * 0.1], 16, fill=(0, 0, 0, 150))
    for bx in (0.075, 0.11): d.rectangle([c.W * bx, c.H * 0.06 + c.W * 0.025, c.W * (bx + 0.017), c.H * 0.06 + c.W * 0.075], fill=(255, 255, 255, 230))
    tx, ty = c.W * float(e.o.get('label_x', 0.72)), c.fy - c.fw * 2.2
    pts = arrow_pts(tx - c.W * 0.05, ty + c.W * 0.06, c.fx + c.fw * 0.75, c.fy - c.fw * 0.35, 0.3)
    k = ease_out((c.lt - 0.15) / 0.4)
    hand_path(d, pts, col, max(6, c.W // 140), k)
    if k >= 0.99: arrow_head(d, pts, col, max(6, c.W // 140), c.W * 0.04)
    comp(c, to_np(lay), 0, 0)
    lab = text_img(e.o.get('text', 'look here'), c.W * 0.07, 'hand', col[:3], shadow=6)
    place(c, lab, tx, ty - lab.height * 0.2, 0.7 + 0.3 * ease_back(c.lt / 0.3), -6, clamp(c.lt / 0.1), guard=True)


@effect('uninstall', 'a glitchy uninstall bar that breaks the frame apart')
def fx_uninstall(c, e):
    p = clamp(c.lt / e.d); g = p ** 1.6
    rnd = np.random.default_rng(int(c.t * 30))
    sh = int(g * c.W * 0.025)
    if sh: c.img = np.stack([np.roll(c.img[..., 0], sh, 1), c.img[..., 1], np.roll(c.img[..., 2], -sh, 1)], -1)
    for _ in range(int(2 + g * 10)):
        y0 = int(rnd.uniform(0, c.H)); hh = int(rnd.uniform(8, 60)); off = int(rnd.uniform(-1, 1) * g * c.W * 0.08)
        c.img[y0:y0 + hh] = np.roll(c.img[y0:y0 + hh], off, 1)
    if p > 0.82:
        q = (p - 0.82) / 0.18; f = 1 + int(q * 40)
        small = cv2.resize(c.img, (max(1, c.W // f), max(1, c.H // f)), interpolation=cv2.INTER_AREA)
        c.img = cv2.resize(small, (c.W, c.H), interpolation=cv2.INTER_NEAREST) * (1 - 0.6 * q)
    bw, bh = int(c.W * 0.7), int(c.W * 0.2)
    im = rrect(bw, bh, 22, (245, 245, 247, 240)); d = ImageDraw.Draw(im)
    d.text((bw * 0.06, bh * 0.28), e.o.get('text', 'Uninstalling...'), font=font('ui', bh * 0.18), fill=INK + (255,), anchor='lm')
    d.rounded_rectangle([bw * 0.06, bh * 0.56, bw * 0.94, bh * 0.7], 8, fill=(215, 215, 220, 255))
    d.rounded_rectangle([bw * 0.06, bh * 0.56, bw * 0.06 + bw * 0.88 * max(0.03, ease_inout(p)), bh * 0.7], 8, fill=(0, 122, 255, 255))
    d.text((bw * 0.94, bh * 0.85), f'{int(ease_inout(p) * 100)}%', font=font('ui', bh * 0.13), fill=(110, 110, 110, 255), anchor='rm')
    place(c, shadowed(im, 16, 8, 120), c.W / 2, c.H * 0.16, 0.8 + 0.2 * ease_back(c.lt / 0.3), 0, clamp(c.lt / 0.1))


def reel_icons(size):
    s = int(size); im = Image.new('RGBA', (s, int(s * 3.6)), (0, 0, 0, 0)); d = ImageDraw.Draw(im); w = max(3, s // 12)
    h = heart(s * 0.8, (255, 255, 255)); im.alpha_composite(h, (int(s * 0.1), 0))
    d.text((s / 2, s * 0.95), '26.9K', font=font('ui', s * 0.24), fill=(255, 255, 255, 255), anchor='mm')
    d.ellipse([s * 0.15, s * 1.25, s * 0.85, s * 1.95], outline=(255, 255, 255, 255), width=w)
    d.text((s / 2, s * 2.15), '412', font=font('ui', s * 0.24), fill=(255, 255, 255, 255), anchor='mm')
    d.polygon([(s * 0.12, s * 2.75), (s * 0.9, s * 2.45), (s * 0.55, s * 3.25), (s * 0.45, s * 2.88)], outline=(255, 255, 255, 255), width=w)
    return im


@effect('reel-frame', 'your video shrinks into an Instagram reel card')
def fx_reel_frame(c, e):
    k = ease_out(c.lt / 0.35) * clamp((e.d - c.lt) / 0.3)
    if k <= 0: return
    s = 1 - 0.2 * k
    small = cv2.resize(c.img, (c.W // 16, c.H // 16), interpolation=cv2.INTER_AREA)
    bg = cv2.GaussianBlur(cv2.resize(small, (c.W, c.H), interpolation=cv2.INTER_LINEAR), (0, 0), 12) * (1 - 0.45 * k)
    iw, ih = int(c.W * s), int(c.H * s)
    inset = cv2.resize(c.img, (iw, ih), interpolation=cv2.INTER_AREA)
    m = to_np(rrect(iw, ih, c.W * 0.05 * k + 1, (255, 255, 255, 255)))[..., 3:4]
    x0, y0 = (c.W - iw) // 2, int((c.H - ih) * 0.42)
    out = bg.copy(); reg = out[y0:y0 + ih, x0:x0 + iw]; reg[:] = reg * (1 - m) + inset * m
    c.img = out
    mm = np.zeros_like(c.m); mm[y0:y0 + ih, x0:x0 + iw] = cv2.resize(c.m, (iw, ih)); c.m = mm
    c.fx, c.fy, c.fw = x0 + c.fx * s, y0 + c.fy * s, c.fw * s
    ic = cached(e, 'ic', lambda: shadowed(reel_icons(c.W * 0.075), 6, 2, 120))
    comp(c, ic, x0 + iw - ic.width - c.W * 0.01, y0 + ih * 0.52, k)
    hdl = text_img(e.o.get('text', PROFILE['handle']), c.W * 0.032, 'ui', (255, 255, 255), shadow=4)
    comp(c, hdl, x0 + c.W * 0.03, y0 + ih - hdl.height - c.W * 0.04, k)


@effect('shortcut-rain', 'keyboard keys rain down behind you')
def fx_shortcut_rain(c, e):
    keys = e.o.get('text', 'cmd|/|C|V|Z|esc|tab|shift|enter|opt').split('|')
    ks = int(c.W * 0.1)
    def cap(k):
        w = max(ks, int(font('mono', ks * 0.36).getlength(k) + ks * 0.5))
        im = rrect(w, ks, ks * 0.18, (190, 190, 198, 255)); top = rrect(w - 8, ks - 14, ks * 0.16, (246, 246, 248, 255))
        im.alpha_composite(top, (4, 3)); ImageDraw.Draw(im).text((w / 2, ks * 0.44), k, font=font('mono', ks * 0.36), fill=INK + (255,), anchor='mm')
        return shadowed(im, 8, 6, 100)
    caps = cached(e, 'caps', lambda: [cap(k) for k in keys])
    parts = cached(e, 'p', lambda: [(random.Random(i).random(), random.Random(i + 99).random() * max(0.1, e.d - 0.8),
                                     0.45 + 0.4 * random.Random(i + 7).random(), random.Random(i + 3).uniform(-25, 25),
                                     random.Random(i + 5).uniform(-60, 60)) for i in range(int(e.o.get('count', 26)))])
    for i, (x, t0, v, r0, w) in enumerate(parts):
        if c.lt < t0: continue
        y = -ks + (c.lt - t0) * v * c.H
        place(c, caps[i % len(caps)], c.W * (0.04 + 0.92 * x), y, 0.75 + 0.35 * v, r0 + w * (c.lt - t0), clamp((e.d - c.lt) / 0.2), behind=True)


@effect('reject-stamp', 'a big red stamp slams onto the screen')
def fx_reject_stamp(c, e):
    word = e.o.get('text', 'REJECTED').upper(); col = rgb(e.o.get('color'), (214, 40, 40))
    def build():
        t = fit_text(word, c.W * 0.62, 'bold', 200, fill=col); pad = int(t.height * 0.12)
        im = Image.new('RGBA', (t.width + 4 * pad, t.height + 2 * pad), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.rounded_rectangle([3, 3, im.width - 4, im.height - 4], 18, outline=col + (255,), width=max(6, pad // 2))
        im.alpha_composite(t, (2 * pad, pad))
        a = np.asarray(im.split()[3], np.float32) * np.clip(np.random.default_rng(3).uniform(0.55, 1.6, (im.height, im.width)), 0, 1)
        im.putalpha(Image.fromarray(a.astype(np.uint8)))
        return im
    st = cached(e, 's', build)
    k = clamp(c.lt / 0.16); sc = 2.3 - 1.3 * k * k
    if 0.16 < c.lt < 0.45:
        a = (0.45 - c.lt) / 0.29 * c.W * 0.012; rnd = np.random.default_rng(int(c.t * 30))
        M = np.float32([[1, 0, rnd.uniform(-a, a)], [0, 1, rnd.uniform(-a, a)]])
        c.img = cv2.warpAffine(c.img, M, (c.W, c.H), borderMode=cv2.BORDER_REFLECT)
    y = clamp(float(e.o['y']) * c.H if 'y' in e.o else c.fy + c.fw * 2.7, 0, c.H * 0.85)
    place(c, st, c.W / 2, y, sc, float(e.o.get('angle', 12)), k * clamp((e.d - c.lt) / 0.2), guard=True)


@effect('countdown-flip', 'a 3, 2, 1 flip clock above your head')
def fx_countdown(c, e):
    n0 = int(e.o.get('from', 3)); seg = e.d / n0
    i = min(n0 - 1, int(c.lt / seg)); cur, prev = n0 - i, n0 - i + 1
    f = clamp((c.lt - i * seg) / 0.3) if i > 0 else 1.0
    tw, th = int(c.W * 0.3), int(c.W * 0.38)
    def half(num, top):
        im = rrect(tw, th, tw * 0.1, (30, 30, 34, 255)); d = ImageDraw.Draw(im)
        d.text((tw / 2, th / 2), str(num), font=font('bold', th * 0.62), fill=CREAM + (255,), anchor='mm')
        return im.crop((0, 0, tw, th // 2)) if top else im.crop((0, th // 2, tw, th))
    hv = cached(e, 'h', lambda: {(n, t): half(n, t) for n in range(0, n0 + 2) for t in (True, False)})
    im = Image.new('RGBA', (tw, th), (0, 0, 0, 0))
    im.paste(hv[(cur, True)], (0, 0)); im.paste(hv[(prev if f < 1 else cur, False)], (0, th // 2))
    if f < 0.5:
        h = max(1, int(th / 2 * (1 - 2 * f))); fl = hv[(prev, True)].resize((tw, h)); im.paste(fl, (0, th // 2 - h))
    elif f < 1:
        h = max(1, int(th / 2 * (2 * f - 1))); fl = hv[(cur, False)].resize((tw, h)); im.paste(fl, (0, th // 2))
    ImageDraw.Draw(im).line([(0, th // 2), (tw, th // 2)], fill=(0, 0, 0, 255), width=4)
    y = max(th / 2 + c.H * 0.05, c.fy - c.fw * 2.3)
    place(c, shadowed(im, 16, 10, 120), c.W / 2 * 0.6 + c.fx * 0.4, y, 0.7 + 0.3 * ease_back(c.lt / 0.3), 0, clamp((e.d - c.lt) / 0.2), behind=True)


_rect = {}
@effect('rabbit-hole', 'the frame tunnels into itself, spinning')
def fx_rabbit_hole(c, e):
    k = ease_out(c.lt / 0.4) * clamp((e.d - c.lt) / 0.3)
    if k <= 0: return
    if (c.W, c.H) not in _rect:
        a = np.ones((c.H, c.W), np.float32); b = np.zeros((c.H, c.W), np.float32); t = max(4, c.W // 120)
        b[:t] = b[-t:] = 1; b[:, :t] = b[:, -t:] = 1; _rect[(c.W, c.H)] = (a, b)
    ones, border = _rect[(c.W, c.H)]
    r = float(e.o.get('ratio', 0.62)); z = (c.lt * float(e.o.get('speed', 0.8))) % 1.0
    src = c.img; cx, cy = c.fx, c.fy
    out = None
    for lev in range(0, 7):
        s = r ** (lev - z * k) if lev else 1.0
        ang = (lev - z) * float(e.o.get('spin', 10)) * k if lev else 0
        if lev and s < 0.03: break
        M = cv2.getRotationMatrix2D((cx, cy), ang, s)
        if lev == 0:
            out = src.copy(); continue
        L = cv2.warpAffine(src, M, (c.W, c.H), flags=cv2.INTER_LINEAR)
        a = cv2.warpAffine(ones, M, (c.W, c.H))[..., None] * k
        bd = cv2.warpAffine(border, M, (c.W, c.H))[..., None] * k
        out = out * (1 - a) + L * a
        out = out * (1 - bd) + bd
    m = c.m[..., None] * k  # you stay in front while the room tunnels behind you
    c.img = out * (1 - m) + src * m


@effect('cover-star', 'you become a magazine cover, with the title behind your head')
def fx_cover_star(c, e):
    if e.o.get('look') == 'editorial': return cover_editorial(c, e)
    k = ease_out(c.lt / 0.35); al = clamp((e.d - c.lt) / 0.2)
    c.img = c.img * (1 - 0.6 * k) + grade(c.img, 'pop') * 0.6 * k
    title = e.o.get('text', 'VIBE').upper(); col = rgb(e.o.get('color'), (232, 36, 52))
    mast = cached(e, 'm', lambda: fit_text(title, c.W * 0.92, 'bold', 600, fill=col))
    mast_h = min(mast.height, c.H * 0.24)
    place(c, mast, c.W / 2, c.H * 0.035 + mast_h / 2 - (1 - k) * mast_h, mast_h / mast.height, 0, al * k, behind=True)
    iss = cached(e, 'i', lambda: text_img(e.o.get('issue', 'THE AI ISSUE  ·  2026'), c.W * 0.025, 'mono', (255, 255, 255), shadow=3))
    place(c, iss, c.W / 2, c.H * 0.03, alpha=al * k, behind=True)
    lines = e.o.get('lines', '55 effects|you can steal|no editor|needed').split('|')
    y = c.H * 0.5
    for j, ln in enumerate(lines):
        big = j == 0
        im = cached(e, ('l', j), lambda: text_img(ln, c.W * (0.085 if big else 0.045), 'serif' if big else 'bold', YELLOW if big else (255, 255, 255), shadow=5))
        kj = ease_out((c.lt - 0.15 - 0.08 * j) / 0.3)
        comp(c, im, c.W * 0.05 - (1 - kj) * 60, y, al * kj, guard=True); y += im.height * 0.86
    def barcode():
        rnd = random.Random(1); bw, bh = int(c.W * 0.16), int(c.W * 0.09)
        im = Image.new('RGBA', (bw, bh), (255, 255, 255, 255)); d = ImageDraw.Draw(im); x = 8
        while x < bw - 8:
            w = rnd.choice((2, 2, 3, 5)); d.rectangle([x, 6, x + w - 1, bh - 18], fill=(0, 0, 0, 255)); x += w + rnd.choice((2, 3, 4))
        return im
    bc = cached(e, 'b', barcode)
    comp(c, bc, c.W * 0.95 - bc.width, c.H * 0.93 - bc.height, al * k, guard=True)


@effect('scribble', 'marker doodles draw themselves around you')
def fx_scribble(c, e):
    col = rgb(e.o.get('color'), YELLOW) + (255,); wd = max(6, c.W // 130)
    lay = Image.new('RGBA', (c.W, c.H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    rx, ry = c.fw * 1.0, c.fw * 1.3
    angs = np.linspace(-1.9, -1.9 + 2 * math.pi * 1.08, 70)
    ring = [(c.fx + rx * (1 + 0.04 * math.sin(3 * a)) * math.cos(a), c.fy + ry * (1 + 0.04 * math.cos(2 * a)) * math.sin(a)) for a in angs]
    hand_path(d, ring, col, wd, ease_inout(c.lt / 0.5))
    lx, ly = clamp(c.fx + c.fw * 2.3, c.W * 0.2, c.W * 0.8), max(c.H * 0.08, c.fy - c.fw * 2.4)
    pts = arrow_pts(lx - c.fw * 0.3, ly + c.fw * 0.5, c.fx + rx * 0.85, c.fy - ry * 0.75, -0.3)
    k2 = ease_out((c.lt - 0.45) / 0.35)
    if k2 > 0: hand_path(d, pts, col, wd, k2)
    if k2 >= 0.99: arrow_head(d, pts, col, wd, c.W * 0.035)
    for j, (sx, sy) in enumerate(((c.fx - c.fw * 1.9, c.fy - c.fw * 1.2), (c.fx - c.fw * 1.5, c.fy + c.fw * 0.6), (c.fx + c.fw * 1.6, c.fy + c.fw * 0.3))):
        ks = ease_back((c.lt - 0.8 - 0.1 * j) / 0.25) * c.fw * 0.28
        if ks > 0:
            d.line([(sx - ks, sy), (sx + ks, sy)], fill=col, width=wd); d.line([(sx, sy - ks), (sx, sy + ks)], fill=col, width=wd)
    al = clamp((e.d - c.lt) / 0.2)
    comp(c, to_np(lay), 0, 0, al)
    if c.lt > 0.7:
        lab = text_img(e.o.get('text', 'me!'), c.W * 0.075, 'hand', col[:3], shadow=6)
        place(c, lab, lx, ly - lab.height * 0.15, 0.7 + 0.3 * ease_back((c.lt - 0.7) / 0.3), 8, al)


# ---------- pack 2: app-style effects (added 21 Oct 2026) ----------
def pop(c, t0, dur=0.3): return ease_back((c.lt - t0) / dur) if c.lt > t0 else 0.0
def fade(c, e, t=0.2): return clamp((e.d - c.lt) / t)
GREEN, BLUE, PURPLE, ORANGE, RED = (34, 197, 94), (10, 132, 255), (124, 92, 255), (217, 119, 87), (238, 34, 34)


def glass(c, w, h, r, cx, cy, amt=0.22, tint=(255, 255, 255), blur=None, alpha=240, dark=0.0, liquid=True):
    """A glass panel made from whatever sits behind it. liquid=True (default since 27 Oct 2026) is see-through liquid
    glass after liquid-glass-js (MIT, dashersw): light blur, refraction bending the room at the rim, a red/blue fringe
    (after React Bits' GlassSurface) and a specular edge lit from the top-left. liquid=False is the old frosted card."""
    w, h = int(w), int(h); blur = blur or max(8, c.W // 40); x0, y0 = int(cx - w / 2), int(cy - h / 2)
    if not liquid:
        pad = blur * 2
        xs = np.clip(np.arange(x0 - pad, x0 + w + pad), 0, c.W - 1); ys = np.clip(np.arange(y0 - pad, y0 + h + pad), 0, c.H - 1)
        reg = cv2.GaussianBlur(np.ascontiguousarray(c.img[np.ix_(ys, xs)]), (0, 0), blur)[pad:pad + h, pad:pad + w]
        reg = reg * (1 - dark) * (1 - amt) + np.float32(tint) / 255 * amt
        im = Image.fromarray((np.clip(reg, 0, 1) * 255).astype(np.uint8)).convert('RGBA')
        m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], int(r), fill=alpha); im.putalpha(m)
        ImageDraw.Draw(im).rounded_rectangle([1, 1, w - 2, h - 2], int(r), outline=(255, 255, 255, 120), width=max(2, c.W // 540))
        return im
    u = c.W / 2160; pad = int(140 * u) + 4
    xs = np.clip(np.arange(x0 - pad, x0 + w + pad), 0, c.W - 1); ys = np.clip(np.arange(y0 - pad, y0 + h + pad), 0, c.H - 1)
    tex = cv2.GaussianBlur(np.ascontiguousarray(c.img[np.ix_(ys, xs)]), (0, 0), max(3.0, blur * 0.3))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32); r = max(2.0, float(r))
    q = np.stack([np.abs(xx - w / 2) - (w / 2 - r), np.abs(yy - h / 2) - (h / 2 - r)], -1)
    sdf = np.linalg.norm(np.maximum(q, 0), axis=-1) + np.minimum(np.maximum(q[..., 0], q[..., 1]), 0) - r
    d = np.maximum(-sdf, 0) / u
    nx, ny = xx - w / 2, yy - h / 2; nl = np.sqrt(nx * nx + ny * ny) + 1e-3; nx, ny = nx / nl, ny / nl
    k = (70 * np.exp(-d / 14) + 34 * np.exp(-d / 70) + 10 * np.exp(-d / 260)) * u
    out = np.zeros((h, w, 3), np.float32)
    for ch, fr in enumerate((1.10, 1.0, 0.90)):
        out[..., ch] = cv2.remap(tex[..., ch], (xx + pad + nx * k * fr).astype(np.float32), (yy + pad + ny * k * fr).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    out = out * (1 - dark * 0.3) * 0.9 + np.float32(tint) / 255 * amt * 0.25 + 0.05 * (1.0 - 0.30 * (yy / h))[..., None] - 0.04
    spec = np.exp(-d / 5) * np.clip(0.55 - 0.45 * (nx * 0.6 + ny * 0.8), 0, 1)
    out = np.clip(out + (spec * 0.85 + np.exp(-d / 30) * 0.10)[..., None], 0, 1)
    a = (np.clip(0.5 - sdf, 0, 1) * alpha).astype(np.uint8)
    im = Image.fromarray((out * 255).astype(np.uint8)).convert('RGBA'); im.putalpha(Image.fromarray(a))
    return im


def face_chip(c, e, size):
    """A round avatar cut from your own face (grabbed once, at the start of the effect)."""
    def grab():
        r = c.fw * 0.9; x0, y0 = int(max(0, c.fx - r)), int(max(0, c.fy - r * 1.05))
        crop = c.img[y0:int(y0 + 2 * r), x0:int(x0 + 2 * r)]
        im = Image.fromarray((np.clip(crop, 0, 1) * 255).astype(np.uint8)).convert('RGBA')
        return im
    src = cached(e, 'face', grab).resize((int(size), int(size)), Image.LANCZOS)
    m = Image.new('L', src.size, 0); ImageDraw.Draw(m).ellipse([0, 0, src.width - 1, src.height - 1], fill=255); src.putalpha(m)
    return src


def cursor(size):
    s = float(size); im = Image.new('RGBA', (int(s * 0.95), int(s * 1.45)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    pts = [(3, 3), (3, s * 1.12), (s * 0.3, s * 0.87), (s * 0.5, s * 1.33), (s * 0.66, s * 1.26), (s * 0.46, s * 0.8), (s * 0.82, s * 0.8)]
    d.polygon(pts, fill=(255, 255, 255, 255)); d.line(pts + [pts[0]], fill=(0, 0, 0, 255), width=max(2, int(s / 14)), joint='curve')
    return shadowed(im, 6, 3, 110)


def tick(d, x, y, s, color=(255, 255, 255, 255), w=None):
    d.line([(x, y + s * 0.5), (x + s * 0.36, y + s * 0.85), (x + s, y + s * 0.1)], fill=color, width=w or max(3, int(s / 5)), joint='curve')


def lines_fit(lines, max_w, kind, start):
    size = start
    while size > 10 and max(font(kind, size).getlength(l) for l in lines) > max_w: size = int(size * 0.94)
    return size


def shift(c, dy):
    """Slide the whole picture (and you) down by dy pixels."""
    if abs(dy) < 0.5: return
    M = np.float32([[1, 0, 0], [0, 1, dy]])
    c.img = cv2.warpAffine(c.img, M, (c.W, c.H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    c.m = cv2.warpAffine(c.m, M, (c.W, c.H), flags=cv2.INTER_LINEAR); c.fy += dy


def thumb_grid(cards, cols, rows, cell, gap, i0=0, look=True):
    im = Image.new('RGBA', (cols * cell + (cols - 1) * gap, rows * int(cell * 1.25) + (rows - 1) * gap), (0, 0, 0, 0))
    ch = int(cell * 1.25)
    for k in range(cols * rows):
        src = cards[(i0 + k) % len(cards)]; src = vary(src, i0 + k) if look else src.convert('RGB')
        sw, sh = src.size; s = max(cell / sw, ch / sh); t = src.resize((max(cell, int(sw * s)), max(ch, int(sh * s))), Image.LANCZOS)
        l, tp = (t.width - cell) // 2, int((t.height - ch) * 0.3); t = t.crop((l, tp, l + cell, tp + ch)).convert('RGBA')
        m = Image.new('L', t.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, cell - 1, ch - 1], max(4, cell // 12), fill=255); t.putalpha(m)
        im.alpha_composite(t, ((k % cols) * (cell + gap), (k // cols) * (ch + gap)))
    return im


def glass_widgets_v1(c, e):
    k0 = ramp(c, e, 0.3, 0)
    if e.o.get('grade', 'warm') != 'none': c.img = c.img * (1 - 0.6 * k0) + grade(c.img, e.o.get('grade', 'warm')) * 0.6 * k0
    al = fade(c, e); W = c.W; mg = W * 0.055
    S = W * 0.31; y_top = c.H * 0.07
    gd = float(e.o.get('dark', 0.2))
    a = glass(c, S, S, S * 0.2, mg + S / 2, y_top + S / 2, amt=0.14, dark=gd); d = ImageDraw.Draw(a)
    d.ellipse([S * 0.1, S * 0.115, S * 0.1 + S * 0.06, S * 0.115 + S * 0.06], fill=ORANGE + (255,))
    d.text((S * 0.2, S * 0.145), e.o.get('title', 'Claude'), font=font('uim', S * 0.085), fill=(255, 255, 255, 235), anchor='lm')
    d.text((S * 0.08, S * 0.2), e.o.get('text', '22'), font=font('uib', S * 0.44), fill=(255, 255, 255, 255))
    for j, ln in enumerate(e.o.get('sub', 'effects|one clip').split('|')):
        d.text((S * 0.1, S * (0.7 + 0.11 * j)), ln, font=font('uim', S * 0.085), fill=(255, 255, 255, 235))
    place(c, a, mg + S / 2, y_top + S / 2, 0.6 + 0.4 * pop(c, 0.0), 0, al * clamp(c.lt / 0.1), behind=True)
    bw, bh = W * 0.37, W * 0.15; bx = W - mg - bw / 2
    b = glass(c, bw, bh, bh * 0.28, bx, y_top + bh / 2, amt=0.14, dark=gd); d = ImageDraw.Draw(b)
    d.ellipse([bh * 0.17, bh * 0.2, bh * 0.17 + bh * 0.11, bh * 0.31], fill=(255, 69, 58, 255))
    d.text((bh * 0.36, bh * 0.255), 'Rendering', font=font('uim', bh * 0.19), fill=(255, 255, 255, 240), anchor='lm')
    p = ease_inout(c.lt / max(0.3, e.d * 0.85))
    d.rounded_rectangle([bh * 0.17, bh * 0.5, bw - bh * 0.17, bh * 0.6], bh * 0.05, fill=(255, 255, 255, 70))
    d.rounded_rectangle([bh * 0.17, bh * 0.5, bh * 0.17 + (bw - bh * 0.34) * max(0.04, p), bh * 0.6], bh * 0.05, fill=(255, 255, 255, 245))
    d.text((bh * 0.17, bh * 0.78), f"{e.o.get('label', 'glass UI')}  ·  {int(p * 100)}%", font=font('uim', bh * 0.14), fill=(255, 255, 255, 210), anchor='lm')
    place(c, b, bx, y_top + bh / 2, 0.6 + 0.4 * pop(c, 0.12), 0, al * clamp((c.lt - 0.12) / 0.1), behind=True)
    cy2 = y_top + bh + mg * 0.45 + bh / 2
    g = glass(c, bw, bh, bh * 0.28, bx, cy2, amt=0.14, dark=gd); d = ImageDraw.Draw(g)
    av = face_chip(c, e, bh * 0.62); g.alpha_composite(av, (int(bw - bh * 0.19 - av.width), int((bh - av.height) / 2)))
    d.text((bh * 0.2, bh * 0.36), e.o.get('name', PROFILE['name']), font=font('uib', bh * 0.22), fill=(255, 255, 255, 255), anchor='lm')
    d.text((bh * 0.2, bh * 0.66), e.o.get('handle', PROFILE['handle']), font=font('uim', bh * 0.14), fill=(255, 255, 255, 215), anchor='lm')
    place(c, g, bx, cy2, 0.6 + 0.4 * pop(c, 0.24), 0, al * clamp((c.lt - 0.24) / 0.1), behind=True)
    f1, f2 = font('uim', W * 0.045), font('uib', W * 0.045)
    pre, hi = e.o.get('pill', 'Edited by |Claude').split('|') if '|' in e.o.get('pill', 'Edited by |Claude') else (e.o['pill'], '')
    tw = f1.getlength(pre) + f2.getlength(hi); ph = W * 0.105; pw = tw + ph * 0.9; py = c.H * 0.865
    q = glass(c, pw, ph, ph / 2, W / 2, py, amt=0.16, tint=(70, 70, 76)); d = ImageDraw.Draw(q)
    d.text(((pw - tw) / 2, ph / 2), pre, font=f1, fill=(255, 255, 255, 255), anchor='lm')
    d.text(((pw - tw) / 2 + f1.getlength(pre), ph / 2), hi, font=f2, fill=(255, 176, 146, 255), anchor='lm')
    place(c, shadowed(q, 14, 6, 70), W / 2, py, 0.7 + 0.3 * pop(c, 0.4), 0, al * clamp((c.lt - 0.4) / 0.1), guard=True)


@effect('red-collage', 'black and white you, a giant red word behind, kinetic type stacked beside you')
def fx_red_collage(c, e):
    k = ramp(c, e, 0.15, 0); m = c.m[..., None]
    bw = grade(c.img, 'bw'); out = bw * m + bw * 0.62 * (1 - m)
    c.img = c.img * (1 - k) + out * k
    vignette(c, 0.45 * k)
    red = rgb(e.o.get('color'), (255, 46, 166)); al = fade(c, e)  # 電光粉 #FF2EA6
    w = cached(e, 'w', lambda: fit_text(e.o.get('text', 'EDIT').upper(), c.W * 0.98, 'uib', 700, fill=red, glow=(red, int(e.o.get('glow', 12)))))
    s = 1.12 - 0.12 * ease_out(c.lt / 0.4)
    place(c, w, c.W / 2, max(w.height * 0.42, c.fy - c.fw * 1.05), s, 0, clamp(c.lt / 0.12) * al, behind=True)
    lines = e.o.get('lines', 'ONE CLIP.|55 EFFECTS.|ZERO APPS.').split('|')
    size = cached(e, 'sz', lambda: lines_fit(lines, c.W * 0.8, 'uib', int(c.W * 0.14)))
    y = max(c.H * 0.5, c.fy + c.fw * 1.55)
    for j, ln in enumerate(lines):
        im = cached(e, ('l', j), lambda: text_img(ln, size, 'uib', rgb(e.o.get('color2'), red) if j == 1 else (255, 255, 255), shadow=8))
        kk = clamp((c.lt - 0.18 - 0.13 * j) / 0.16)
        if kk > 0: place(c, im, c.W * 0.05 + im.width / 2, y + im.height / 2, 1.4 - 0.4 * ease_out(kk), 0, kk * al, guard=True)
        y += size * 1.0
    if e.o.get('tag'):  # 預設不顯示左下角小標；要的話給 tag
        tag = cached(e, 'tag', lambda: text_img(e.o.get('tag'), c.W * 0.027, 'mono', red))
        dot = Image.new('RGBA', (int(tag.height * 0.4),) * 2, (0, 0, 0, 0)); ImageDraw.Draw(dot).ellipse([0, 0, dot.width - 1, dot.width - 1], fill=red + (255,))
        blink = 1.0 if int(c.lt * 2.5) % 2 == 0 else 0.35
        place(c, dot, c.W * 0.07, c.H * 0.93, alpha=al * k * blink, guard=True)
        place(c, tag, c.W * 0.07 + dot.width + tag.width / 2, c.H * 0.93, alpha=al * k, guard=True)


@effect('split-headline', 'a clean headline card slides down and pushes you into the bottom of the frame')
def fx_split_headline(c, e):
    k = ease_out(c.lt / 0.38) * clamp((e.d - c.lt) / 0.25)
    ch = c.H * float(e.o.get('height', 0.36))
    shift(c, ch * float(e.o.get('push', 0.72)) * k)
    top = ch * k; W = c.W; col = rgb(e.o.get('color'), GREEN)
    lay = Image.new('RGBA', (W, int(ch)), (244, 242, 236, 255)); d = ImageDraw.Draw(lay)
    lines = e.o.get('text', 'Claude|edits my|reels.').split('|'); hl = e.o.get('hl', 'edits')
    S = cached(e, 'sz', lambda: lines_fit(lines, W * 0.84, 'uib', int(W * 0.135))); f = font('uib', S)
    x0, y0 = W * 0.07, ch * 0.13
    for j, ln in enumerate(lines):
        kj = clamp((c.lt - 0.12 - 0.08 * j) / 0.18)
        if kj <= 0: continue
        y = y0 + j * S * 1.04 + (1 - ease_out(kj)) * S * 0.35; a = int(255 * kj)
        x = x0
        for wi, word in enumerate(ln.split(' ')):
            tail = '.' if word.endswith('.') else ''; core = word[:-1] if tail else word
            wl = f.getlength(core)
            if core == hl:
                hk = ease_out((c.lt - 0.42) / 0.22); pad = S * 0.12
                if hk > 0: d.rounded_rectangle([x - pad, y + S * 0.02, x - pad + (wl + 2 * pad) * hk, y + S * 1.1], S * 0.16, fill=col + (a,))
                d.text((x, y), core, font=f, fill=((255, 255, 255, a) if hk > 0.55 else (20, 20, 22, a)))
            else: d.text((x, y), core, font=f, fill=(20, 20, 22, a))
            x += wl
            if tail: d.text((x, y), tail, font=f, fill=col + (a,)); x += f.getlength(tail)
            x += f.getlength(' ') + (S * 0.12 if core == hl else 0)
    d.rectangle([0, ch - max(5, W // 180), W, ch], fill=col + (255,))
    comp(c, lay, 0, top - ch)
    pt = text_img(e.o.get('pill', 'in seconds ↗'), W * 0.034, 'uib', (255, 255, 255))
    pill = rrect(pt.width + W * 0.02, pt.height * 0.95, pt.height * 0.47, col + (255,)); pill.alpha_composite(pt, (int(W * 0.01), int(-pt.height * 0.025)))
    place(c, shadowed(pill, 10, 4, 80), W * 0.93 - pill.width / 2, top + pill.height * 0.95, 0.6 + 0.4 * pop(c, 0.62), 0, clamp((c.lt - 0.62) / 0.1) * k, guard=True)


_grad = {}
@effect('pastel-word', 'a soft lavender backdrop, a giant word behind you and a profile card that gets followed')
def fx_pastel_word(c, e):
    W, H = c.W, c.H; k = ramp(c, e, 0.2, 0); m = c.m[..., None]; al = fade(c, e)
    if (W, H) not in _grad:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); t = np.clip((yy / H) * 0.8 + (xx / W) * 0.2, 0, 1)[..., None]
        _grad[(W, H)] = np.float32([0.70, 0.67, 0.97]) * (1 - t) + np.float32([0.93, 0.90, 1.0]) * t
    lum = (c.img @ np.float32([0.299, 0.587, 0.114]))[..., None]
    bg = _grad[(W, H)] * (0.86 + 0.22 * lum)
    you = np.clip(c.img * 0.93 + 0.05, 0, 1)
    c.img = c.img * (1 - k) + (you * m + bg * (1 - m)) * k
    word = cached(e, 'w', lambda: fit_text(e.o.get('text', 'REELS').upper(), W * 0.96, 'uib', 700, fill=(255, 255, 255)))
    dk = ease_out(c.lt / 0.45)
    place(c, shadowed(word, 24, 12, 60), W / 2, max(word.height * 0.45, c.fy - c.fw * 1.2) - (1 - dk) * H * 0.06, 1, 0, al * clamp(c.lt / 0.15), behind=True)
    cw, chh = W * 0.86, W * 0.15; cy = H * 0.865 + (1 - ease_out((c.lt - 0.15) / 0.35)) * H * 0.2
    card_ = rrect(cw, chh, chh * 0.3, (255, 255, 255, 248)); d = ImageDraw.Draw(card_)
    av = face_chip(c, e, chh * 0.64); card_.alpha_composite(av, (int(chh * 0.18), int((chh - av.height) / 2)))
    d.text((chh * 0.98, chh * 0.38), e.o.get('name', PROFILE['name']), font=font('uib', chh * 0.22), fill=(20, 20, 22, 255), anchor='lm')
    h1 = e.o.get('handle', PROFILE['handle'] + '  ·  '); f = font('uim', chh * 0.15)
    d.text((chh * 0.98, chh * 0.66), h1, font=f, fill=(140, 140, 150, 255), anchor='lm')
    d.text((chh * 0.98 + f.getlength(h1), chh * 0.66), e.o.get('role', 'creator'), font=f, fill=PURPLE + (255,), anchor='lm')
    at = e.d * 0.6; on = c.lt >= at
    bx = cw - chh * 0.22
    d.text((bx, chh / 2), 'Following' if on else 'Follow', font=font('uib', chh * 0.2), fill=((140, 140, 150, 255) if on else PURPLE + (255,)), anchor='rm')
    sq = 1 - 0.06 * math.sin(math.pi * clamp((c.lt - at) / 0.25)) if on else 1
    place(c, shadowed(card_, 18, 8, 90), W / 2, cy, sq, 0, al * clamp((c.lt - 0.15) / 0.12), guard=True)
    cu = cached(e, 'cur', lambda: cursor(W * 0.06))
    ck = ease_inout((c.lt - 0.25) / max(0.2, at - 0.3))
    tx, ty = W / 2 + cw / 2 - chh * 0.55, cy + chh * 0.12
    sx, sy = W * 1.02, H * 1.02
    place(c, cu, sx + (tx - sx) * ck + cu.width / 2, sy + (ty - sy) * ck + cu.height / 2, 0.85 if on and c.lt - at < 0.15 else 1, 0, al * clamp((c.lt - 0.25) / 0.1))


_gp = {}
@effect('check-pills', 'grid-paper room, your reels pinned behind you and blue pills that get clicked')
def fx_check_pills(c, e):
    W, H = c.W, c.H; k = ramp(c, e, 0.15, 0); m = c.m[..., None]; al = fade(c, e)
    if (W, H) not in _gp:
        g = np.ones((H, W, 3), np.float32) * np.float32([0.935, 0.945, 0.96]); st = max(20, W // 20); lw = max(1, W // 700)
        for x in range(0, W, st): g[:, x:x + lw] = np.float32([0.86, 0.875, 0.9])
        for y in range(0, H, st): g[y:y + lw] = np.float32([0.86, 0.875, 0.9])
        _gp[(W, H)] = g
    c.img = c.img * (1 - k) + (c.img * m + _gp[(W, H)] * (1 - m)) * k
    def board(i, title):
        bw = int(W * 0.44); im = rrect(bw, int(bw * 1.12), bw * 0.07, (255, 255, 255, 255)); d = ImageDraw.Draw(im)
        d.ellipse([bw * 0.06, bw * 0.055, bw * 0.06 + bw * 0.09, bw * 0.145], fill=(255, 160, 140, 255))
        d.text((bw * 0.19, bw * 0.1), title, font=font('uib', bw * 0.06), fill=(20, 20, 22, 255), anchor='lm')
        gr = thumb_grid(e.cards, 3, 3, int(bw * 0.28), int(bw * 0.025), i0=i * 3)
        im.alpha_composite(gr, ((bw - gr.width) // 2, int(bw * 0.2))); return shadowed(im, 16, 8, 70)
    b1 = cached(e, 'b1', lambda: board(0, e.o.get('handle', PROFILE['handle'])))
    b2 = cached(e, 'b2', lambda: board(1, e.o.get('board', 'Reels  ·  55 effects')))
    by = max(H * 0.17, c.fy - c.fw * 0.9)
    place(c, b1, W * 0.25, by, 0.6 + 0.4 * pop(c, 0.0), 8, al * clamp(c.lt / 0.1), behind=True)
    place(c, b2, W * 0.76, by - W * 0.02, 0.6 + 0.4 * pop(c, 0.1), -8, al * clamp((c.lt - 0.1) / 0.1), behind=True)
    names = e.o.get('text', 'Hook|Captions|Cuts|B-roll').split('|')
    spots = [(-0.95, 2.35), (0.55, 2.0), (-0.35, 2.95), (0.95, 2.75), (0.1, 3.45), (-1.1, 3.3)]
    ph = W * 0.078; cu = cached(e, 'cur', lambda: cursor(W * 0.055))
    pos = []
    for i, n in enumerate(names):
        sx, sy = spots[i % len(spots)]
        x = clamp(c.fx + sx * c.fw * 1.6, W * 0.16, W * 0.84); y = clamp(c.fy + sy * c.fw, H * 0.3, H * 0.9)
        t0 = 0.22 + 0.2 * i; pos.append((x, y, t0))
        if c.lt < t0: continue
        clicked = c.lt >= t0 + 0.12
        t = text_img(n, ph * 0.42, 'uib', (255, 255, 255)); pw = int(t.width + ph * (0.75 if clicked else 0.35))
        pill = rrect(pw, ph, ph / 2, BLUE + (255,)); pill.alpha_composite(t, (int(ph * 0.18), int((ph - t.height) / 2)))
        if clicked: tick(ImageDraw.Draw(pill), pw - ph * 0.55, ph * 0.33, ph * 0.33)
        sq = 1 - 0.1 * math.sin(math.pi * clamp((c.lt - t0 - 0.12) / 0.2))
        place(c, shadowed(pill, 10, 5, 90), x, y, (0.5 + 0.5 * pop(c, t0, 0.25)) * sq, 0, al, guard=True)
    if pos and c.lt > pos[0][2] - 0.1:
        seg = [p for p in pos if p[2] <= c.lt + 0.1]; tx, ty, t0 = seg[-1]
        px, py = (pos[len(seg) - 2][0], pos[len(seg) - 2][1]) if len(seg) > 1 else (W * 0.9, H * 0.95)
        q = ease_inout((c.lt - (t0 - 0.12)) / 0.2)
        place(c, cu, px + (tx - px) * q + ph * 0.3 + cu.width / 2, py + (ty - py) * q + ph * 0.1 + cu.height / 2, 1, 0, al)


def red_timeline(c, e):
    W, H = c.W, c.H; k = ramp(c, e, 0.2, 0); m = c.m[..., None]; al = fade(c, e)
    lum = (c.img @ np.float32([0.299, 0.587, 0.114]))[..., None]
    bg = np.clip(lum * np.float32([1.05, 0.3, 0.27]) * 0.85, 0, 1)
    you = np.clip(c.img * np.float32([1.04, 0.86, 0.82]), 0, 1)
    c.img = c.img * (1 - k) + (you * m + bg * (1 - m)) * k; vignette(c, 0.5 * k)
    red = rgb(e.o.get('color'), (255, 52, 44))
    sl = (1 - ease_out(c.lt / 0.35)) * W * 0.08; tb = clamp(c.lt / 0.15) * al
    secs = 21 + int(c.lt * 3)
    rec = text_img(f"{e.o.get('tc', 'REC')} 00:{secs:02d}", W * 0.032, 'mono', red)
    dot = Image.new('RGBA', (int(rec.height * 0.36),) * 2, (0, 0, 0, 0)); ImageDraw.Draw(dot).ellipse([0, 0, dot.width - 1, dot.width - 1], fill=red + (255,))
    comp(c, dot, W * 0.065 - sl, H * 0.075 + (rec.height - dot.height) / 2, tb * (1.0 if int(c.lt * 2.5) % 2 == 0 else 0.35), guard=True)
    comp(c, rec, W * 0.065 + dot.width * 1.4 - sl, H * 0.075, tb, guard=True)
    ti = cached(e, 'ti', lambda: text_img(e.o.get('text', 'AUTO-EDIT'), W * 0.13, 'uib', (255, 255, 255), shadow=10))
    comp(c, ti, W * 0.055 - sl, H * 0.075 + rec.height * 0.85, tb, guard=True)
    su = cached(e, 'su', lambda: text_img(e.o.get('sub', 'timeline by Claude'), W * 0.037, 'uim', red))
    comp(c, su, W * 0.065 - sl, H * 0.075 + rec.height * 0.85 + ti.height * 0.88, tb, guard=True)
    pw, phh = int(W * 0.9), int(H * 0.19); py = H * 0.755 + (1 - ease_out((c.lt - 0.1) / 0.35)) * H * 0.3
    lay = rrect(pw, phh, W * 0.03, (14, 10, 10, 215), (255, 70, 60, 90), 2); d = ImageDraw.Draw(lay)
    for j in range(4): d.text((pw * (0.05 + 0.3 * j), phh * 0.12), f'00:0{j}', font=font('mono', W * 0.022), fill=(170, 170, 175, 255), anchor='lm')
    clips = cached(e, 'cl', lambda: [(r, a, b) for r, segs in enumerate([[(0.04, 0.24), (0.26, 0.5), (0.53, 0.76), (0.79, 0.96)],
                                                                            [(0.04, 0.3), (0.33, 0.45), (0.48, 0.7)], [(0.04, 0.55), (0.6, 0.96)]]) for a, b in segs])
    p = 0.04 + 0.92 * clamp(c.lt / (e.d * 0.95)); ph_x = pw * p
    glow = Image.new('RGBA', (pw, phh), (0, 0, 0, 0)); gd = ImageDraw.Draw(glow)
    for r, a, b in clips:
        y0 = phh * (0.27 + 0.235 * r); x0, x1 = pw * a, pw * b; on = pw * a < ph_x
        fill = red + (255,) if on else (120, 30, 28, 255)
        d.rounded_rectangle([x0, y0, x1, y0 + phh * 0.17], phh * 0.04, fill=fill)
        if on: gd.rounded_rectangle([x0, y0, x1, y0 + phh * 0.17], phh * 0.04, fill=red + (200,))
    d.line([(ph_x, phh * 0.2), (ph_x, phh * 0.97)], fill=(255, 255, 255, 255), width=max(3, W // 300))
    gd.line([(ph_x, phh * 0.2), (ph_x, phh * 0.97)], fill=(255, 255, 255, 255), width=max(8, W // 100))
    lay = Image.alpha_composite(glow.filter(ImageFilter.GaussianBlur(W // 90)), lay)
    comp(c, lay, (W - pw) / 2, py, al, guard=True)


@effect('headline-box', 'a punch-in with a clean two-line headline, the second line in a white box')
def fx_headline_box(c, e):
    face_cam(c, 1 + (float(e.o.get('zoom', 1.2)) - 1) * ease_out(c.lt / 0.22), 0.45)
    W = c.W; al = fade(c, e); lines = e.o.get('text', 'How I got Claude|to edit my reels.').split('|')
    S = cached(e, 'sz', lambda: lines_fit(lines, W * 0.84, 'uib', int(W * 0.085)))
    y = max(c.H * 0.06, c.fy - c.fw * 1.3 - S * 1.3 * len(lines))
    for j, ln in enumerate(lines):
        kj = clamp((c.lt - 0.1 - 0.12 * j) / 0.18)
        if kj <= 0: y += S * 1.3; continue
        boxed = j == len(lines) - 1
        t = cached(e, ('t', j), lambda: text_img(ln, S, 'uib', (16, 16, 18) if boxed else (255, 255, 255), shadow=0 if boxed else 9))
        if boxed:
            bx = rrect(t.width - S * 0.15, S * 1.22, S * 0.08, (255, 255, 255, 255))
            wk = ease_out(kj); bx = bx.crop((0, 0, max(1, int(bx.width * wk)), bx.height))
            comp(c, bx, W / 2 - (t.width - S * 0.15) / 2, y, al, guard=True)
        place(c, t, W / 2, y + S * 0.6, 0.92 + 0.08 * ease_out(kj), 0, al * kj, guard=True)
        y += S * 1.3


@effect('profile-wall', 'your profile grid fills the wall behind you while a counter ticks up')
def fx_profile_wall(c, e):
    W, H = c.W, c.H; al = fade(c, e)
    def wall():
        pw = int(W * 0.92); ph = int(H * 0.36); im = rrect(pw, ph, W * 0.035, (16, 16, 18, 240)); d = ImageDraw.Draw(im)
        tabs = ('Posts', 'Reels', 'Tagged'); f = font('uim', W * 0.032)
        for j, tb in enumerate(tabs):
            x = pw * (0.2 + 0.3 * j); d.text((x, ph * 0.06), tb, font=f, fill=((255, 255, 255, 255) if j == 1 else (130, 130, 136, 255)), anchor='mm')
            if j == 1: d.rectangle([x - pw * 0.08, ph * 0.1, x + pw * 0.08, ph * 0.1 + 4], fill=(255, 255, 255, 255))
        gr = thumb_grid(e.cards, 4, 2, int(pw * 0.225), int(pw * 0.012), look=False)
        im.alpha_composite(gr, ((pw - gr.width) // 2, int(ph * 0.14))); return shadowed(im, 20, 10, 110)
    wl = cached(e, 'wall', wall)
    place(c, wl, W / 2, H * 0.04 + wl.height / 2, 0.94 + 0.06 * ease_out(c.lt / 0.35), 0, al * clamp(c.lt / 0.15), behind=True)
    cw, chh = W * 0.76, W * 0.25; cy = min(H * 0.86, c.fy + c.fw * 2.6)
    g = glass(c, cw, chh, chh * 0.18, W / 2, cy, amt=0.5, tint=(12, 12, 14)); d = ImageDraw.Draw(g)
    target = int(e.o.get('count', 197000)); n = int(target * ease_out((c.lt - 0.2) / 0.8))
    swap = clamp((c.lt - 1.15) / 0.2)
    if swap < 1: d.text((cw / 2, chh * 0.33), f'{n:,}', font=font('uib', chh * 0.3), fill=(255, 255, 255, int(255 * (1 - swap))), anchor='mm')
    if swap > 0: d.text((cw / 2, chh * 0.33), e.o.get('label', 'views'), font=font('uib', chh * 0.3), fill=(255, 255, 255, int(255 * swap)), anchor='mm')
    av = face_chip(c, e, chh * 0.3); g.alpha_composite(av, (int(chh * 0.14), int(chh * 0.58)))
    d.text((chh * 0.52, chh * 0.68), e.o.get('name', PROFILE['handle'].lstrip('@')), font=font('uib', chh * 0.09), fill=(255, 255, 255, 255), anchor='lm')
    d.text((chh * 0.52, chh * 0.8), e.o.get('sub', 'top reel'), font=font('uim', chh * 0.075), fill=(170, 170, 176, 255), anchor='lm')
    on = c.lt >= e.d * 0.7
    d.rounded_rectangle([cw - chh * 0.95, chh * 0.62, cw - chh * 0.14, chh * 0.86], chh * 0.12, fill=((60, 60, 66, 255) if on else (255, 255, 255, 255)))
    d.text((cw - chh * 0.545, chh * 0.74), 'Following' if on else 'Follow', font=font('uib', chh * 0.08), fill=((255, 255, 255, 255) if on else (16, 16, 18, 255)), anchor='mm')
    place(c, g, W / 2, cy + (1 - ease_out((c.lt - 0.05) / 0.3)) * H * 0.1, 1, 0, al * clamp((c.lt - 0.05) / 0.12), guard=True)


@effect('tier-list', 'a tier list drops in front of you and Claude flies into S tier')
def fx_tier_list(c, e):
    W, H = c.W, c.H; al = fade(c, e)
    ttl = cached(e, 'ttl', lambda: fit_text(e.o.get('title', 'best way to edit a reel?'), W * 0.88, 'serif', int(W * 0.11), fill=YELLOW, shadow=8))
    place(c, ttl, W / 2, max(ttl.height * 0.6, c.fy - c.fw * 1.65), 0.9 + 0.1 * ease_out(c.lt / 0.3), 0, al * clamp(c.lt / 0.15), behind=True)
    tiers = [('S', (255, 127, 127)), ('A', (255, 191, 127)), ('B', (255, 223, 127)), ('C', (191, 255, 127)), ('D', (127, 191, 255)), ('F', (191, 127, 255))]
    cw = int(W * 0.66); rh = int(W * 0.082); pad = int(W * 0.015); chh = pad * 2 + rh * 6 + pad * 5
    fill = dict(zip('BCDF', e.o.get('others', 'templates|timelines|apps|doing it by hand').split('|')))
    def board():
        im = rrect(cw, chh, W * 0.025, (22, 22, 26, 240)); d = ImageDraw.Draw(im)
        for i, (lab, col) in enumerate(tiers):
            y = pad + i * (rh + pad)
            d.rounded_rectangle([pad, y, pad + rh, y + rh], rh * 0.14, fill=col + (255,))
            d.text((pad + rh / 2, y + rh / 2), lab, font=font('uib', rh * 0.5), fill=(20, 20, 22, 255), anchor='mm')
            d.rounded_rectangle([pad * 2 + rh, y, cw - pad, y + rh], rh * 0.14, fill=(40, 40, 46, 255))
            if lab in fill:
                f = font('uim', rh * 0.3); tw = f.getlength(fill[lab]) + rh * 0.4
                d.rounded_rectangle([pad * 3 + rh, y + rh * 0.15, pad * 3 + rh + tw, y + rh * 0.85], rh * 0.12, fill=(78, 78, 86, 255))
                d.text((pad * 3 + rh + rh * 0.2, y + rh / 2), fill[lab], font=f, fill=(225, 225, 230, 255), anchor='lm')
        return shadowed(im, 18, 10, 120)
    bd = cached(e, 'bd', board)
    top = min(H * 0.95 - bd.height, max(c.fy + c.fw * 1.4, H * 0.45))
    k = ease_back(c.lt / 0.35); bx, by = W / 2, top + bd.height / 2 + (1 - k) * H * 0.15
    place(c, bd, bx, by, 1, 0, al * clamp(c.lt / 0.12), guard=True)
    tile = cached(e, 'tile', lambda: shadowed(rrect(int(rh * 2.6), int(rh * 0.8), rh * 0.16, ORANGE + (255,)), 8, 4, 100))
    tx = cached(e, 'tx', lambda: text_img(e.o.get('item', 'Claude'), rh * 0.36, 'uib', (255, 255, 255)))
    tl = tile.copy(); tl.alpha_composite(tx, ((tl.width - tx.width) // 2, (tl.height - tx.height) // 2 - 3))
    sx, sy = W * 0.86, c.fy + c.fw * 0.4
    ex = bx - bd.width / 2 + 18 + pad * 3 + rh + tile.width / 2 - 10; ey = by - bd.height / 2 + 18 + pad + rh / 2
    q = ease_back((c.lt - 0.45) / 0.4)
    if c.lt > 0.4: place(c, tl, sx + (ex - sx) * q, sy + (ey - sy) * q, 1.25 - 0.25 * clamp(q), 18 * (1 - clamp(q)), al, guard=True)


@effect('broll-split', 'split screen: b-roll on top with a price-tag sticker, you on the bottom')
def fx_broll_split(c, e):
    W, H = c.W, c.H; k = ease_out(c.lt / 0.3) * clamp((e.d - c.lt) / 0.2); al = fade(c, e)
    shift(c, (H * 0.72 - c.fy) * k)
    sh = int(H * 0.5 * k)
    if sh > 2:
        src = e.cards[int(e.o.get('pick', 0)) % len(e.cards)].convert('RGB')
        z = 1.0 + 0.06 * clamp(c.lt / e.d); tw, th = int(W * z), int(H * 0.5 * z)
        s = max(tw / src.width, th / src.height); im = src.resize((int(src.width * s) + 1, int(src.height * s) + 1), Image.BILINEAR)
        l, t = (im.width - W) // 2, int((im.height - H * 0.5) * 0.35); im = im.crop((l, t, l + W, t + int(H * 0.5)))
        top = np.asarray(im, np.float32) / 255
        c.img[:sh] = top[int(H * 0.5) - sh:]; c.m[:sh] = 0
        c.img[max(0, sh - 3):sh + 3] = 1.0
    tag = cached(e, 'tag', lambda: text_img(e.o.get('text', '4 hrs  →  4 min'), W * 0.06, 'uib', (16, 16, 18)))
    tw, th = int(tag.width + W * 0.11), int(tag.height * 1.25)
    st = Image.new('RGBA', (tw, th), (0, 0, 0, 0)); d = ImageDraw.Draw(st); n = th * 0.5
    d.polygon([(0, th / 2), (n, 0), (tw, 0), (tw, th), (n, th)], fill=(255, 255, 255, 255))
    d.ellipse([n * 0.55, th / 2 - n * 0.16, n * 0.87, th / 2 + n * 0.16], fill=(200, 200, 205, 255))
    st.alpha_composite(tag, (int(n * 1.05), (th - tag.height) // 2))
    place(c, shadowed(st, 12, 6, 110), W * 0.66, H * 0.39 * k + H * 0.0, 0.5 + 0.5 * pop(c, 0.3), 8, al * clamp((c.lt - 0.3) / 0.08))


@effect('phone-fan', 'your reels fan out like a hand of phones in front of you, under a two-line headline')
def fx_phone_fan(c, e):
    W, H = c.W, c.H; al = fade(c, e)
    lines = e.o.get('text', '55 effects.|zero editing apps.').split('|')
    S = cached(e, 'sz', lambda: lines_fit(lines, W * 0.84, 'uib', int(W * 0.08)))
    y = max(H * 0.06, c.fy - c.fw * 1.3 - S * 1.3 * len(lines))
    for j, ln in enumerate(lines):
        kj = clamp((c.lt - 0.05 - 0.1 * j) / 0.18); last = j == len(lines) - 1
        t = cached(e, ('t', j), lambda: text_img(ln, S, 'uib', (16, 16, 18) if last else (255, 255, 255), shadow=0 if last else 9))
        if last: comp(c, rrect(t.width - S * 0.15, S * 1.22, S * 0.08, (255, 255, 255, 255)), W / 2 - (t.width - S * 0.15) / 2, y, al * kj, guard=True)
        place(c, t, W / 2, y + S * 0.6, 1, 0, al * kj, guard=True); y += S * 1.3
    pw = int(W * 0.23); ph = int(pw * 2.0)
    def phone(i):
        im = rrect(pw, ph, pw * 0.16, (14, 14, 16, 255))
        scr = card(vary(e.cards[i % len(e.cards)], i) if e.o.get('images') is None else e.cards[i % len(e.cards)], pw - 10)
        inner = scr.crop(((scr.width - (pw - 10)) // 2, (scr.height - (ph - 10)) // 2 - 6, (scr.width + pw - 10) // 2, (scr.height + ph - 10) // 2 - 6))
        im.alpha_composite(inner, (5, 5))
        ImageDraw.Draw(im).rounded_rectangle([pw * 0.36, ph * 0.025, pw * 0.64, ph * 0.045], pw * 0.03, fill=(0, 0, 0, 255))
        return shadowed(im, 14, 8, 120)
    ph_ = cached(e, 'ph', lambda: [phone(i) for i in range(4)])
    cx = W / 2 * 0.5 + c.fx * 0.5; cy = max(c.fy + c.fw * 1.1 + ph / 2, H * 0.62)
    cy = min(cy, H - ph * 0.42)
    for i, o in enumerate((-1.5, -0.5, 0.5, 1.5)):
        q = ease_back((c.lt - 0.2 - 0.06 * i) / 0.4)
        place(c, ph_[i], cx + o * W * 0.19 * q, cy + o * o * W * 0.025 * q, 0.9, -o * 11 * q, al * clamp((c.lt - 0.2) / 0.1), guard=True)


@effect('dot-reveal', 'your shot builds itself out of glowing dots, then snaps into the full picture')
def fx_dot_reveal(c, e):
    p = clamp(c.lt / e.d); W, H = c.W, c.H
    cell = max(6, int(W * float(e.o.get('cell', 0.017)))); gh, gw = H // cell + 1, W // cell + 1
    def geo():
        yy, xx = np.mgrid[0:gh * cell, 0:gw * cell].astype(np.float32)
        dist = np.sqrt((xx % cell - cell / 2 + 0.5) ** 2 + (yy % cell - cell / 2 + 0.5) ** 2)[:H, :W]
        return dist, np.random.default_rng(5).random((gh, gw)).astype(np.float32)
    dist, thr = cached(e, 'geo', geo)
    pad = np.pad(c.img, ((0, gh * cell - H), (0, gw * cell - W), (0, 0)), mode='edge')
    small = cv2.resize(pad, (gw, gh), interpolation=cv2.INTER_AREA)
    lum = small @ np.float32([0.299, 0.587, 0.114])
    on = np.clip((p * 1.7 - thr * 0.95) / 0.3, 0, 1)
    sparkle = 0.75 + 0.25 * np.sin(thr * 40 + c.lt * 18)
    r = (0.18 + 0.32 * np.sqrt(np.clip(lum, 0, 1))) * cell * on
    col = rgb(e.o.get('color'), (255, 128, 80))
    q2 = clamp((p - 0.3) / 0.35)
    dc = np.float32(col) / 255 * (0.55 + 0.6 * lum[..., None]) * sparkle[..., None] * (1 - q2) + np.clip(small * 1.15, 0, 1) * q2
    R = np.repeat(np.repeat(r, cell, 0), cell, 1)[:H, :W]
    DC = np.repeat(np.repeat(dc, cell, 0), cell, 1)[:H, :W]
    dm = np.clip(R - dist + 0.5, 0, 1)[..., None]
    bgc = np.float32(rgb(e.o.get('bg'), (20, 20, 22))) / 255
    dots = bgc * (1 - dm) + DC * dm
    q = ease_inout((p - 0.6) / 0.4)
    c.img = dots * (1 - q) + c.img * q


def tracked(s, size, kind, fill, spacing, colors=None):
    """Letter-spaced text. colors: optional per-character fill list."""
    f = font(kind, size); w = sum(f.getlength(ch) for ch in s) + spacing * max(0, len(s) - 1)
    bb = f.getbbox('Ag'); im = Image.new('RGBA', (int(w) + 8, int(bb[3] - bb[1] + size * 0.4)), (0, 0, 0, 0)); d = ImageDraw.Draw(im); x = 4
    for i, ch in enumerate(s):
        d.text((x, -bb[1] + size * 0.2), ch, font=f, fill=(colors[i] if colors else fill) + (255,)); x += f.getlength(ch) + spacing
    return im


def rich(parts, size, kind, base, accent, accent_kind=None, shadow=0):
    """One line of text where *starred* words take the accent colour (and optionally another font)."""
    segs = []
    for j, p in enumerate(parts.split('*')):
        if p: segs.append(text_img(p, size, accent_kind if (j % 2 and accent_kind) else kind, accent if j % 2 else base, shadow=shadow))
    pad = int(size * 0.2 + shadow * 2.5) + 4
    w = sum(s.width - 2 * pad for s in segs) + 2 * pad; h = max(s.height for s in segs)
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); x = 0
    for s in segs: im.alpha_composite(s, (x, (h - s.height) // 2)); x += s.width - 2 * pad
    return im


@effect('headline-wall', 'a wall of your own reel headlines piles up behind your head, then your total views pop in front')
def fx_headline_wall(c, e):
    W, H = c.W, c.H; u = W / 1080; al = fade(c, e)
    items = [x.split('::') for x in e.o.get('text', 'Protect your personal data with ChatGPT Agent Mode::197K views|Easiest no-code scroll animation websites::124K views|'
                                         'How to make your resume un-rejectable using Claude::83K views|Same prompt: Claude Fable 5 vs ChatGPT 5.6 Sol::50K views|'
                                         'Jev, the new AI model faster and cheaper than Claude::40K views|Scrape LinkedIn automatically::38K views|'
                                         'Protect your personal data on the internet::140K views').split('|')]
    looks = [((255, 255, 255), (20, 20, 22)), ((22, 20, 24), (255, 255, 255)), ((246, 238, 226), (30, 24, 20)), ((255, 214, 10), (20, 20, 22))]
    def hcard(i):
        title, meta = (items[i % len(items)] + [''])[:2]; bg, fg = looks[i % len(looks)]
        cw = int(W * 0.5); f = font('uib', cw * 0.085); words = title.split(' '); lines, cur = [], ''
        for w_ in words:
            tst = (cur + ' ' + w_).strip()
            if f.getlength(tst) > cw * 0.84 and cur: lines.append(cur); cur = w_
            else: cur = tst
        lines.append(cur); lh = cw * 0.1
        chh = int(cw * 0.1 + lh * len(lines) + cw * 0.16)
        im = rrect(cw, chh, cw * 0.04, bg + (255,)); d = ImageDraw.Draw(im)
        for j, ln in enumerate(lines): d.text((cw * 0.08, cw * 0.07 + j * lh), ln, font=f, fill=fg + (255,))
        my = chh - cw * 0.085; s = cw * 0.04
        d.polygon([(cw * 0.08, my - s / 2), (cw * 0.08, my + s / 2), (cw * 0.08 + s * 0.9, my)], fill=(255, 48, 64, 255))
        d.text((cw * 0.08 + s * 1.5, my), (e.o.get('handle', PROFILE['handle']) + '  ·  ' + meta) if meta else e.o.get('handle', PROFILE['handle']), font=font('uim', cw * 0.045), fill=fg + (170,), anchor='lm')
        return shadowed(im, 14, 8, 110)
    N = int(e.o.get('count', 13))
    cards = cached(e, 'cards', lambda: [hcard(i) for i in range(N)])
    pos = cached(e, 'pos', lambda: [(random.Random(i * 7 + 1).uniform(0.2, 0.8), random.Random(i * 7 + 2).uniform(0.07, 0.42), random.Random(i * 7 + 3).uniform(-9, 9)) for i in range(N)])
    gap = float(e.o.get('gap', 0.09))
    for i in range(N):
        t0 = i * gap
        if c.lt < t0: break
        x, y, r = pos[i]; kk = ease_back((c.lt - t0) / 0.22)
        place(c, cards[i], x * W, y * H, 0.55 + 0.45 * kk, r, al * clamp((c.lt - t0) / 0.06), behind=True)
    t1 = N * gap + 0.1
    if c.lt > t1:
        tot = e.o.get('total', '672K'); lab = e.o.get('label', 'views from 7 reels')
        a = text_img(tot, 96 * u, 'anton', (255, 255, 255)); b = text_img(lab, 34 * u, 'uib', (255, 255, 255))
        pw = int(a.width + b.width + 30 * u); ph = int(max(a.height, b.height) + 10 * u)
        pill = rrect(pw, ph, ph * 0.28, (217, 119, 87, 245)); pill.alpha_composite(a, (int(8 * u), (ph - a.height) // 2)); pill.alpha_composite(b, (int(a.width + 8 * u), (ph - b.height) // 2))
        place(c, shadowed(pill, 18, 8, 110), W / 2, max(c.fy + c.fw * 1.8, H * 0.6), 0.6 + 0.4 * pop(c, t1, 0.3), -3, al * clamp((c.lt - t1) / 0.08), guard=True)


@effect('checklist', 'a Claude task list builds under your chin: each step spins, then ticks green')
def fx_checklist(c, e):
    W, H = c.W, c.H; u = W / 1080; al = fade(c, e)
    rows = [x.split('::') for x in e.o.get('text', 'Found your face::every frame|Cut you out of the room::AI mask|Put the text behind you::depth|'
                                        'Graded the colour::warm|Rendered in 4K::2160p').split('|')]
    n = len(rows); cw = W * 0.9; rh = 104 * u; hh = 120 * u; chh = hh + rh * n + 26 * u
    y0 = min(max(c.fy + c.fw * 1.35, H * 0.42), H * 0.93 - chh); cy = y0 + chh / 2 + (1 - ease_out(c.lt / 0.35)) * H * 0.12
    span = max(0.4, e.d - 0.55); done_at = [0.3 + span * (i + 1) / n for i in range(n)]
    g = glass(c, cw, chh, 40 * u, W / 2, cy, amt=0.78, tint=(14, 13, 16), blur=int(30 * u)); d = ImageDraw.Draw(g)
    sx, sy = 44 * u, hh / 2
    for a in range(4):
        ang = a * math.pi / 2 + math.pi / 4
        d.line([(sx, sy), (sx + 18 * u * math.cos(ang), sy + 18 * u * math.sin(ang))], fill=(217, 119, 87, 255), width=int(7 * u))
        d.line([(sx, sy), (sx + 18 * u * math.cos(ang + math.pi / 4), sy + 18 * u * math.sin(ang + math.pi / 4))], fill=(217, 119, 87, 255), width=int(5 * u))
    d.text((80 * u, hh / 2), e.o.get('title', 'Claude is editing your clip'), font=font('uib', 42 * u), fill=(255, 255, 255, 255), anchor='lm')
    nd = sum(c.lt >= t for t in done_at)
    d.text((cw - 36 * u, hh / 2), f'{nd}/{n}', font=font('uim', 28 * u), fill=(170, 170, 176, 255), anchor='rm')
    d.line([(30 * u, hh), (cw - 30 * u, hh)], fill=(255, 255, 255, 30), width=max(1, int(2 * u)))
    for i, (txt, meta) in enumerate([(r + [''])[:2] for r in rows]):
        y = hh + 13 * u + rh * i + rh / 2; x = 56 * u; r_ = 24 * u
        start = done_at[i - 1] if i else 0.3
        if c.lt >= done_at[i]:
            q = ease_back((c.lt - done_at[i]) / 0.25); rr = r_ * (0.6 + 0.4 * q)
            d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(52, 199, 89, 255)); tick(d, x - rr * 0.5, y - rr * 0.45, rr, w=int(5 * u))
            fc, mc = (255, 255, 255, 255), (52, 199, 89, 255)
        elif c.lt >= start:
            a0 = (c.lt * 540) % 360; d.ellipse([x - r_, y - r_, x + r_, y + r_], outline=(255, 255, 255, 50), width=int(5 * u))
            d.arc([x - r_, y - r_, x + r_, y + r_], a0, a0 + 100, fill=(217, 119, 87, 255), width=int(5 * u)); fc, mc = (255, 255, 255, 255), (170, 170, 176, 255)
        else:
            d.ellipse([x - r_, y - r_, x + r_, y + r_], outline=(255, 255, 255, 60), width=int(4 * u)); fc, mc = (255, 255, 255, 110), (170, 170, 176, 90)
        d.text((x + 48 * u, y), txt, font=font('uib', 40 * u), fill=fc, anchor='lm')
        d.text((cw - 36 * u, y), meta, font=font('mono', 28 * u), fill=mc, anchor='rm')
    place(c, shadowed(g, 24, 12, 120), W / 2, cy, 1, 0, al * clamp(c.lt / 0.12), guard=True)


def np_thumb(c, w, h):
    """The current frame as a small PIL thumbnail (cropped to w:h around your face)."""
    ar = w / h; ch = c.H * 0.62; cw = ch * ar
    x0 = int(clamp(c.fx - cw / 2, 0, c.W - cw)); y0 = int(clamp(c.fy - ch * 0.4, 0, c.H - ch))
    crop = c.img[y0:int(y0 + ch), x0:int(x0 + cw)]
    return Image.fromarray((np.clip(crop, 0, 1) * 255).astype(np.uint8)).resize((int(w), int(h)), Image.LANCZOS)


def glow_panel(w, h, r, top, bot, line, glow, gblur):
    """A rounded panel with a vertical gradient fill, a thin border and an outer glow."""
    w, h = int(w), int(h); pad = int(gblur * 2.2)
    out = Image.new('RGBA', (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    g = Image.new('RGBA', out.size, (0, 0, 0, 0)); ImageDraw.Draw(g).rounded_rectangle([pad, pad, pad + w, pad + h], r, fill=glow)
    out.alpha_composite(g.filter(ImageFilter.GaussianBlur(gblur)))
    t = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    fill = (np.float32(top) * (1 - t) + np.float32(bot) * t) * np.ones((1, w, 1), np.float32)
    body = Image.fromarray(np.concatenate([fill, np.full((h, w, 1), 255, np.float32)], 2).astype(np.uint8), 'RGBA')
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], r, fill=255); body.putalpha(m)
    ImageDraw.Draw(body).rounded_rectangle([1, 1, w - 2, h - 2], r, outline=line, width=max(2, int(w / 400)))
    out.alpha_composite(body, (pad, pad))
    return out, pad


def np_thumb_pil(im, w, h):
    src = im.convert('RGB'); s = max(w / src.width, h / src.height)
    t = src.resize((max(w, int(src.width * s) + 1), max(h, int(src.height * s) + 1)), Image.LANCZOS)
    l, tp = (t.width - w) // 2, int((t.height - h) * 0.3); t = t.crop((l, tp, l + w, tp + h)).convert('RGBA')
    m = Image.new('L', t.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], max(3, w // 10), fill=255); t.putalpha(m)
    return t


def glass_widgets_v2(c, e):
    """More widgets, artifact-style: stat tile, render bar, profile, a mini views artifact, now-playing, calendar, a 4K ring and the Edited by Claude pill."""
    W, H = c.W, c.H; u = W / 1080
    k0 = ramp(c, e, 0.3, 0)
    if e.o.get('grade', 'warm') != 'none': c.img = c.img * (1 - 0.6 * k0) + grade(c.img, e.o.get('grade', 'warm')) * 0.6 * k0
    al = fade(c, e); gd = float(e.o.get('dark', 0.22)); white = (255, 255, 255)
    def bob(i): return 6 * u * math.sin(2 * math.pi * (c.lt * 0.55 + i * 0.17))
    def show(im, x, y, i, front=False):
        t0 = 0.07 * i
        if c.lt < t0: return
        place(c, im, x, y + bob(i), 0.6 + 0.4 * pop(c, t0, 0.32), 0, al * clamp((c.lt - t0) / 0.08), behind=not front, guard=front)
    G = lambda w, h, cx, cy, r=None: glass(c, w, h, r or min(w, h) * 0.2, cx, cy, amt=0.14, dark=gd)
    # 1 · stat tile
    S = 300 * u; ax, ay = 50 * u + S / 2, 118 * u + S / 2
    a = G(S, S, ax, ay); d = ImageDraw.Draw(a)
    d.ellipse([S * 0.1, S * 0.115, S * 0.16, S * 0.175], fill=ORANGE + (255,))
    d.text((S * 0.2, S * 0.145), e.o.get('title', 'Claude'), font=font('uim', S * 0.085), fill=white + (235,), anchor='lm')
    d.text((S * 0.08, S * 0.2), e.o.get('text', '38'), font=font('uib', S * 0.44), fill=white + (255,))
    for j, ln in enumerate(e.o.get('sub', 'effects|one clip').split('|')): d.text((S * 0.1, S * (0.7 + 0.11 * j)), ln, font=font('uim', S * 0.085), fill=white + (235,))
    show(a, ax, ay, 0)
    # 2 · render bar
    bw, bh = 400 * u, 150 * u; bx, by = W - 50 * u - bw / 2, 118 * u + bh / 2
    b = G(bw, bh, bx, by, bh * 0.28); d = ImageDraw.Draw(b); p = ease_inout(c.lt / max(0.3, e.d * 0.85))
    d.ellipse([bh * 0.17, bh * 0.2, bh * 0.28, bh * 0.31], fill=(255, 69, 58, 255))
    d.text((bh * 0.36, bh * 0.255), 'Rendering', font=font('uim', bh * 0.19), fill=white + (240,), anchor='lm')
    d.rounded_rectangle([bh * 0.17, bh * 0.5, bw - bh * 0.17, bh * 0.6], bh * 0.05, fill=white + (70,))
    d.rounded_rectangle([bh * 0.17, bh * 0.5, bh * 0.17 + (bw - bh * 0.34) * max(0.04, p), bh * 0.6], bh * 0.05, fill=white + (245,))
    d.text((bh * 0.17, bh * 0.78), f"4K render  ·  {int(p * 100)}%", font=font('uim', bh * 0.14), fill=white + (210,), anchor='lm')
    show(b, bx, by, 1)
    # 3 · profile
    cy3 = by + bh / 2 + 22 * u + bh / 2
    g = G(bw, bh, bx, cy3, bh * 0.28); d = ImageDraw.Draw(g)
    av = face_chip(c, e, bh * 0.62); g.alpha_composite(av, (int(bw - bh * 0.19 - av.width), int((bh - av.height) / 2)))
    d.text((bh * 0.2, bh * 0.36), e.o.get('name', PROFILE['name']), font=font('uib', bh * 0.22), fill=white + (255,), anchor='lm')
    d.text((bh * 0.2, bh * 0.66), e.o.get('handle', PROFILE['handle']), font=font('uim', bh * 0.14), fill=white + (215,), anchor='lm')
    show(g, bx, cy3, 2)
    # 4 · views artifact (a mini page inside the glass)
    aw, ah = 330 * u, 330 * u; dx, dy = 50 * u + aw / 2, ay + S / 2 + 26 * u + ah / 2
    art = G(aw, ah, dx, dy, 44 * u); d = ImageDraw.Draw(art)
    d.text((24 * u, 30 * u), 'artifact · views.html', font=font('mono', 15 * u), fill=white + (220,), anchor='lm')
    inn = rrect(aw - 36 * u, ah - 74 * u, 20 * u, (250, 248, 244, 255)); di = ImageDraw.Draw(inn); iw, ih = inn.size
    for j in range(3): di.ellipse([14 * u + j * 16 * u, 14 * u, 24 * u + j * 16 * u, 24 * u], fill=((255, 95, 87), (255, 189, 46), (40, 200, 64))[j] + (255,))
    di.text((16 * u, 40 * u), 'Top reels', font=font('uib', 26 * u), fill=(24, 22, 26, 255))
    di.text((16 * u, 72 * u), '197K', font=font('anton', 44 * u), fill=(200, 85, 61, 255))
    vals = [197, 140, 124, 83, 50, 40, 38]; gx0, gx1, gy1 = 16 * u, iw - 16 * u, ih - 18 * u; bwid = (gx1 - gx0) / 7 * 0.66
    for j, v in enumerate(vals):
        q = ease_out((c.lt - 0.35 - 0.05 * j) / 0.4); hh = (ih * 0.42) * v / 197 * q; x0 = gx0 + (gx1 - gx0) * j / 7
        if hh > 1: di.rounded_rectangle([x0, gy1 - hh, x0 + bwid, gy1], 5 * u, fill=((242, 196, 109) if j == 0 else (200, 85, 61)) + (255,))
    art.alpha_composite(inn, (int(18 * u), int(56 * u)))
    show(art, dx, dy, 3)
    # 5 · now playing
    mw, mh = 360 * u, 220 * u; mx, my = W - 50 * u - mw / 2, cy3 + bh / 2 + 22 * u + mh / 2
    mu = G(mw, mh, mx, my, 40 * u); d = ImageDraw.Draw(mu); A = 96 * u
    t = np.linspace(0, 1, int(A), dtype=np.float32)[:, None, None]
    art2 = Image.fromarray(np.concatenate([(np.float32([255, 150, 110]) * (1 - t) + np.float32([217, 90, 70]) * t) * np.ones((1, int(A), 1), np.float32), np.full((int(A), int(A), 1), 255, np.float32)], 2).astype(np.uint8), 'RGBA')
    am = Image.new('L', art2.size, 0); ImageDraw.Draw(am).rounded_rectangle([0, 0, art2.width - 1, art2.height - 1], 16 * u, fill=255); art2.putalpha(am)
    ad = ImageDraw.Draw(art2)
    for k_ in range(6):
        ang = k_ * math.pi / 3; ad.line([(A / 2 - 26 * u * math.cos(ang), A / 2 - 26 * u * math.sin(ang)), (A / 2 + 26 * u * math.cos(ang), A / 2 + 26 * u * math.sin(ang))], fill=(255, 255, 255, 255), width=int(7 * u))
    mu.alpha_composite(art2, (int(22 * u), int(22 * u)))
    d.text((134 * u, 44 * u), 'NOW EDITING', font=font('mono', 15 * u), fill=white + (200,), anchor='lm')
    d.text((134 * u, 78 * u), e.o.get('song', 'soft UI pops'), font=font('uib', 28 * u), fill=white + (255,), anchor='lm')
    d.text((134 * u, 108 * u), 'sfx · 25.7s', font=font('uim', 20 * u), fill=white + (200,), anchor='lm')
    pp = clamp(c.lt / max(0.5, e.d)); d.rounded_rectangle([22 * u, 140 * u, mw - 22 * u, 146 * u], 3 * u, fill=white + (70,))
    d.rounded_rectangle([22 * u, 140 * u, 22 * u + (mw - 44 * u) * pp, 146 * u], 3 * u, fill=white + (240,))
    cxm, cym = mw / 2, 184 * u
    d.polygon([(cxm - 12 * u, cym - 16 * u), (cxm - 12 * u, cym + 16 * u), (cxm + 16 * u, cym)], fill=white + (255,))
    for sgn in (-1, 1):
        x = cxm + sgn * 80 * u
        d.polygon([(x - sgn * 10 * u, cym - 11 * u), (x - sgn * 10 * u, cym + 11 * u), (x + sgn * 6 * u, cym)], fill=white + (220,))
        d.polygon([(x + sgn * 4 * u, cym - 11 * u), (x + sgn * 4 * u, cym + 11 * u), (x + sgn * 20 * u, cym)], fill=white + (220,))
    show(mu, mx, my, 4)
    # 6 · calendar
    kw, kh = 330 * u, 190 * u; kx, ky = 50 * u + kw / 2, dy + ah / 2 + 26 * u + kh / 2
    ca = G(kw, kh, kx, ky, 40 * u); d = ImageDraw.Draw(ca)
    d.text((26 * u, 36 * u), e.o.get('day', 'WED'), font=font('uib', 22 * u), fill=(255, 92, 82, 255), anchor='lm')
    d.text((26 * u, 82 * u), e.o.get('date', '21'), font=font('uib', 56 * u), fill=white + (255,), anchor='lm')
    d.rounded_rectangle([22 * u, 120 * u, kw - 22 * u, 168 * u], 12 * u, fill=(255, 92, 82, 210))
    d.text((36 * u, 144 * u), e.o.get('event', 'Post 2 reels · tonight'), font=font('uib', 22 * u), fill=white + (255,), anchor='lm')
    show(ca, kx, ky, 5)
    # 7 · 4K ring
    R = 250 * u; rx, ry = W - 50 * u - R / 2, my + mh / 2 + 26 * u + R / 2
    rg = G(R, R, rx, ry, 56 * u); d = ImageDraw.Draw(rg); rp = ease_inout((c.lt - 0.4) / 1.0); rr = R * 0.34
    d.ellipse([R / 2 - rr, R / 2 - rr - 8 * u, R / 2 + rr, R / 2 + rr - 8 * u], outline=white + (60,), width=int(16 * u))
    if rp > 0: d.arc([R / 2 - rr, R / 2 - rr - 8 * u, R / 2 + rr, R / 2 + rr - 8 * u], -90, -90 + 360 * rp, fill=(52, 199, 89, 255), width=int(16 * u))
    d.text((R / 2, R / 2 - 8 * u), '4K', font=font('uib', 52 * u), fill=white + (255,), anchor='mm')
    d.text((R / 2, R - 26 * u), 'render', font=font('uim', 20 * u), fill=white + (210,), anchor='mm')
    show(rg, rx, ry, 6)
    # 8 · Edited by Claude pill (in front)
    f1, f2 = font('uim', W * 0.045), font('uib', W * 0.045); pre, hi = 'Edited by ', 'Claude'
    tw = f1.getlength(pre) + f2.getlength(hi); ph = W * 0.105; pw = tw + ph * 0.9; py = H * 0.875
    q = glass(c, pw, ph, ph / 2, W / 2, py, amt=0.16, tint=(70, 70, 76)); d = ImageDraw.Draw(q)
    d.text(((pw - tw) / 2, ph / 2), pre, font=f1, fill=white + (255,), anchor='lm')
    d.text(((pw - tw) / 2 + f1.getlength(pre), ph / 2), hi, font=f2, fill=(255, 176, 146, 255), anchor='lm')
    show(shadowed(q, 14, 6, 70), W / 2, py, 7, front=True)


@effect('glass-widgets', 'frosted glass phone widgets and mini artifacts float around your head, with an Edited by Claude pill')
def fx_glass_widgets(c, e):
    (glass_widgets_v1 if e.o.get('look') == 'simple' else glass_widgets_v2)(c, e)


@effect('timeline', 'a dark red cinematic grade with an editing timeline, a REC timecode and a glowing playhead')
def fx_timeline(c, e):
    studio = globals().get('studio_timeline')
    (studio if studio and e.o.get('look') != 'red' else red_timeline)(c, e)


_emoji = {}
def emoji(ch, size):
    """A colour emoji as an RGBA image (Apple Color Emoji on a Mac). Returns None where the font is missing."""
    k = (ch, int(size))
    if k not in _emoji:
        try:
            f = ImageFont.truetype('/System/Library/Fonts/Apple Color Emoji.ttc', 160)
            im = Image.new('RGBA', (200, 200), (0, 0, 0, 0)); ImageDraw.Draw(im).text((20, 10), ch, font=f, embedded_color=True)
            im = im.crop(im.getbbox()); _emoji[k] = im.resize((int(size), int(size * im.height / im.width)), Image.LANCZOS)
        except Exception:
            _emoji[k] = None
    return _emoji[k]


def comment_sheet(c, e):
    """Reels 1021 + VOX look: an Instagram Comments sheet above your head (your hair in front). The word types in, posts,
    gets a heart, then your reply drops in with a link chip."""
    W, H = c.W, c.H; u = W / 1080; al = fade(c, e)
    word = e.o.get('text', 'EFFECTS'); handle = e.o.get('handle', PROFILE['handle'].lstrip('@'))
    reply = e.o.get('reply', 'Sent you the pack'); chip = e.o.get('chip', '55 effects')
    sw, sh = 740 * u, 450 * u
    t_post = 0.3 + 0.06 * len(word) + 0.1; t_heart, t_rep = t_post + 0.25, t_post + 0.4
    sheet = rrect(sw, sh, 30 * u, (38, 38, 40, 248)); d = ImageDraw.Draw(sheet)
    white, grey, blue = (245, 245, 245, 255), (160, 160, 166, 255), (0, 149, 246, 255)
    d.rounded_rectangle([sw / 2 - 32 * u, 14 * u, sw / 2 + 32 * u, 20 * u], 3 * u, fill=(110, 110, 116, 255))
    d.text((sw / 2, 50 * u), 'Comments', font=font('uib', 26 * u), fill=white, anchor='mm')
    d.line([(0, 80 * u), (sw, 80 * u)], fill=(60, 60, 64, 255), width=max(1, int(2 * u)))
    def avatar(sz):
        a = Image.new('RGBA', (int(sz), int(sz)), (0, 0, 0, 0)); ad = ImageDraw.Draw(a)
        ad.ellipse([0, 0, sz - 1, sz - 1], fill=(233, 90, 140, 255)); ad.text((sz / 2, sz / 2), 'V', font=font('uib', sz * 0.5), fill=(255, 255, 255, 255), anchor='mm')
        return a
    if c.lt < t_post:
        d.text((sw / 2, 190 * u), 'Start the conversation.', font=font('uim', 21 * u), fill=grey, anchor='mm')
    else:
        q = ease_out((c.lt - t_post) / 0.25); oy = (1 - q) * -20 * u; a8 = int(255 * clamp(q * 1.5))
        av = avatar(46 * u); av.putalpha(av.split()[3].point(lambda v: v * a8 // 255)); sheet.alpha_composite(av, (int(26 * u), int(100 * u + oy)))
        d.text((88 * u, 108 * u + oy), 'you', font=font('uib', 19 * u), fill=white[:3] + (a8,), anchor='lm')
        d.text((88 * u + font('uib', 19 * u).getlength('you ') + 4 * u, 108 * u + oy), 'now', font=font('uim', 18 * u), fill=grey[:3] + (a8,), anchor='lm')
        d.text((86 * u, 128 * u + oy), word, font=font('uib', 50 * u), fill=white[:3] + (a8,))
        d.text((88 * u, 196 * u + oy), 'Reply', font=font('uim', 17 * u), fill=grey[:3] + (a8,), anchor='lm')
        hk = ease_back((c.lt - t_heart) / 0.3)
        if hk > 0:
            hh = heart(30 * u * hk, (255, 48, 64)); sheet.alpha_composite(hh, (int(sw - 46 * u - hh.width / 2), int(130 * u - hh.height / 2)))
        rk = ease_out((c.lt - t_rep) / 0.25)
        if rk > 0:
            ra = int(255 * clamp(rk * 1.5)); ry = 226 * u + (1 - rk) * 16 * u; rx = 88 * u
            fc = face_chip(c, e, 34 * u); fc.putalpha(fc.split()[3].point(lambda v: v * ra // 255)); sheet.alpha_composite(fc, (int(rx), int(ry)))
            d.text((rx + 46 * u, ry + 8 * u), handle, font=font('uib', 18 * u), fill=white[:3] + (ra,), anchor='lm')
            d.text((rx + 46 * u + font('uib', 18 * u).getlength(handle) + 10 * u, ry + 8 * u), 'Author', font=font('uim', 16 * u), fill=grey[:3] + (ra,), anchor='lm')
            d.text((rx + 46 * u, ry + 36 * u), reply, font=font('uim', 22 * u), fill=white[:3] + (ra,), anchor='lm')
            gift = emoji('🎁', 24 * u)
            if gift is not None:
                g2 = gift.copy(); g2.putalpha(g2.split()[3].point(lambda v: v * ra // 255))
                sheet.alpha_composite(g2, (int(rx + 52 * u + font('uim', 22 * u).getlength(reply)), int(ry + 36 * u - g2.height / 2)))
            ck = ease_back((c.lt - t_rep - 0.12) / 0.3)
            if ck > 0:
                ct = text_img(chip, 19 * u, 'uib', (20, 20, 22)); lk = emoji('🔗', 20 * u)
                cw_ = ct.width + (lk.width + 4 * u if lk is not None else 0) + 10 * u
                cp = rrect(cw_, ct.height * 0.9, ct.height * 0.45, (255, 214, 10, 255))
                x0 = 6 * u
                if lk is not None: cp.alpha_composite(lk, (int(x0 + 4 * u), int((cp.height - lk.height) / 2))); x0 += lk.width + 4 * u
                cp.alpha_composite(ct, (int(x0), int((cp.height - ct.height) / 2)))
                cp = cp.resize((max(1, int(cp.width * (0.6 + 0.4 * ck))), max(1, int(cp.height * (0.6 + 0.4 * ck)))))
                sheet.alpha_composite(cp, (int(rx + 46 * u), int(ry + 56 * u)))
    ey = sh - 140 * u
    chars = ['❤️', '🙌', '🔥', '👏', '😢', '😍', '😮', '😂']
    for j, ch in enumerate(chars):
        im = emoji(ch, 36 * u)
        if im is not None: sheet.alpha_composite(im, (int(36 * u + j * (sw - 72 * u - 36 * u) / 7), int(ey)))
    iy = sh - 78 * u
    sheet.alpha_composite(avatar(48 * u), (int(22 * u), int(iy)))
    d.rounded_rectangle([82 * u, iy, sw - 22 * u, iy + 48 * u], 24 * u, fill=(54, 54, 58, 255))
    typed = word[:int(clamp((c.lt - 0.3) / (0.06 * len(word))) * len(word) + 1e-3)] if c.lt < t_post else ''
    if typed:
        d.text((104 * u, iy + 24 * u), typed, font=font('uib', 26 * u), fill=white, anchor='lm')
        if int(c.lt * 4) % 2: d.rectangle([104 * u + font('uib', 26 * u).getlength(typed) + 3 * u, iy + 10 * u, 106 * u + font('uib', 26 * u).getlength(typed) + 3 * u, iy + 38 * u], fill=(0, 149, 246, 255))
    else:
        d.text((104 * u, iy + 24 * u), f'Add a comment for {handle}', font=font('uim', 20 * u), fill=grey, anchor='lm')
    pressed = t_post - 0.08 <= c.lt < t_post
    d.text((sw - 44 * u, iy + 24 * u), 'Post', font=font('uib', 23 * u), fill=(blue if typed else (70, 110, 160, 255)) if not pressed else (140, 200, 255, 255), anchor='rm')
    sheet = shadowed(sheet, 22, 10, 120)
    bottom = c.fy - c.fw * 0.5; top = bottom - sheet.height
    s = 1.0
    if top < H * 0.02: s = max(0.6, (bottom - H * 0.02) / sheet.height)
    cy = bottom - sheet.height * s / 2 + 3 * u * math.sin(c.lt * 3.2)
    place(c, sheet, W / 2 * 0.5 + c.fx * 0.5, cy, s * (0.85 + 0.15 * ease_back(c.lt / 0.3)), 1.2, al * clamp(c.lt / 0.1), behind=True)


@effect('comment-box', 'an Instagram comments sheet above your head types your word, posts it, gets a heart and your reply')
def fx_comment_box(c, e):
    (comment_bar if e.o.get('look') == 'bar' else comment_sheet)(c, e)


# ---------- pack 3: showcase effects (added 23 Oct 2026) ----------
def num_parts(s):
    """'197K' -> (197.0, 'K', 0 decimals); '59%' -> (59.0, '%', 0); '4.8' -> (4.8, '', 1)."""
    s = str(s).strip(); i = len(s)
    while i and not (s[i - 1].isdigit()): i -= 1
    n = s[:i].replace(',', '') or '0'
    return float(n), s[i:], (len(n.split('.')[1]) if '.' in n else 0)


@effect('liquid-glass-graph', 'a liquid glass card floats under your chin while a graph climbs and the number counts up')
def fx_liquid_glass_graph(c, e):
    if e.o.get('look') == 'bento': return glass_bento(c, e)
    q = ease_out(c.lt / 0.4); al = fade(c, e) * clamp(c.lt / 0.12)
    if al <= 0: return
    W = c.W; cw, ch = int(W * 0.74), int(W * 0.46); sc = 0.88 + 0.12 * q
    cx = W / 2; cy = min(c.H - ch * 0.62, c.fy + c.fw * 2.7) + (1 - q) * W * 0.08
    gw, gh = int(cw * sc), int(ch * sc)
    im = glass(c, gw, gh, gh * 0.12, cx, cy, amt=0.16, blur=max(10, W // 30), dark=0.12)
    hi = cached(e, ('hi', gw, gh), lambda: Image.fromarray(np.dstack([np.full((gh, gw, 3), 255, np.uint8),
        (np.clip(1 - np.linspace(0, 1, gh) * 2.2, 0, 1)[:, None] * np.ones(gw) * 46).astype(np.uint8)]), 'RGBA'))
    hm = Image.new('L', (gw, gh), 0); ImageDraw.Draw(hm).rounded_rectangle([0, 0, gw - 1, gh - 1], int(gh * 0.12), fill=255)
    hl = hi.copy(); hl.putalpha(Image.fromarray(np.minimum(np.asarray(hi)[..., 3], np.asarray(hm)))); im.alpha_composite(hl)
    lay = Image.new('RGBA', (gw, gh), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); pad = gw * 0.07
    g = ease_inout((c.lt - 0.25) / max(0.3, e.d * 0.72))
    lab = e.o.get('text', 'RETENTION').upper()
    d.text((pad, pad * 0.9), lab, font=font('mono', gw * 0.04), fill=(255, 255, 255, 190))
    a, _, _ = num_parts(e.o.get('from', '0')); b, suf, dp = num_parts(e.o.get('to', '59%'))
    v = a + (b - a) * g; s = f'{v:.{dp}f}{suf}'
    f = font('uib', gw * 0.12); d.text((gw - pad - f.getlength(s), pad * 0.55), s, font=f, fill=(255, 255, 255, 255))
    x0, x1, y0, y1 = pad, gw - pad, gh - pad * 0.9, gh * 0.36
    def ycurve(u): return y0 - (y0 - y1) * (u ** 1.5) + math.sin(u * 13) * gh * 0.018 * (1 - u)
    n = 60; pts = [(x0 + (x1 - x0) * j / n, ycurve(j / n)) for j in range(int(n * g) + 1)]
    green = rgb(e.o.get('color'), (52, 211, 110))
    if len(pts) > 1:
        area = Image.new('RGBA', (gw, gh), (0, 0, 0, 0))
        ImageDraw.Draw(area).polygon(pts + [(pts[-1][0], y0), (x0, y0)], fill=green + (55,)); lay.alpha_composite(area)
        glow = Image.new('RGBA', (gw, gh), (0, 0, 0, 0)); lw = max(4, int(gw * 0.011))
        ImageDraw.Draw(glow).line(pts, fill=green + (255,), width=lw * 3, joint='curve')
        lay.alpha_composite(glow.filter(ImageFilter.GaussianBlur(lw * 2)))
        ImageDraw.Draw(lay).line(pts, fill=green + (255,), width=lw, joint='curve')
        hx, hy = pts[-1]; r = lw * 1.9
        ImageDraw.Draw(lay).ellipse([hx - r, hy - r, hx + r, hy + r], fill=(255, 255, 255, 255), outline=green + (255,), width=max(2, lw // 2))
    for j in range(1, 4):
        yy = y0 - (y0 - y1) * j / 3.4
        d.line([(x0, yy), (x1, yy)], fill=(255, 255, 255, 40), width=max(1, int(gw * 0.002)))
    im.alpha_composite(lay)
    place(c, shadowed(im, max(10, W // 70), W // 90, 90), cx, cy, alpha=al, guard=True)


@effect('carousel-spin', 'your reels spin around you in a 3D carousel, then slow to a stop')
def fx_carousel_spin(c, e):
    K = int(e.o.get('count', max(6, min(12, len(e.cards))))); cw = int(c.W * float(e.o.get('size', 0.3)))
    def mk():
        out = []
        for i, im in enumerate(e.cards):
            f = card(vary(im, i) if e.o.get('images') is None else im, cw)
            dk = f.copy(); a = np.asarray(dk).copy(); a[..., :3] = (a[..., :3] * 0.55).astype(np.uint8); out.append((f, Image.fromarray(a, 'RGBA')))
        return out
    cards = cached(e, 'cards', mk)
    k = ramp(c, e, 0.3, 0.25); xx, yy = grid(c)
    d = ((xx - c.fx) / (c.W * 0.55)) ** 2 + ((yy - (c.fy + c.H * 0.15)) / (c.H * 0.5)) ** 2
    dim = 1 - k * 0.5 * np.clip(d, 0, 1) - k * 0.12
    c.img *= (dim * (1 - c.m) + c.m)[..., None]
    p = clamp(c.lt / e.d); spin = float(e.o.get('turns', 1.1)) * 2 * math.pi * (1 - (1 - p) ** 2.4)
    intro, out = ease_out(c.lt / 0.45), fade(c, e, 0.25)
    R, ry = c.W * 0.56 * intro, c.H * 0.07
    cy = c.fy + c.fw * 1.8
    items = sorted((math.cos(i * 2 * math.pi / K + spin), i * 2 * math.pi / K + spin, i) for i in range(K))
    for depth, th, i in items:
        n = len(cards); f, dk = cards[(i * (3 if n % 3 else 2)) % n]; src = f if depth >= 0 else dk  # spread similar covers apart
        sx = max(0.06, abs(math.cos(th)) ** 0.6)
        s = (0.72 + 0.34 * (depth + 1) / 2) * (0.5 + 0.5 * intro)
        w2, h2 = max(2, int(src.width * s * sx)), max(2, int(src.height * s))
        place(c, src.resize((w2, h2), Image.BILINEAR), c.fx + R * math.sin(th), cy + ry * depth, 1.0, 0,
              out * clamp(c.lt / 0.12) * (0.85 + 0.15 * depth), behind=depth < 0, guard=depth >= 0)


MATCH_TXT = ('one clip went in and every cut came back before lunch while editors once spent whole weeks rebuilding the same '
             'timeline by hand early users called it unsettling then impossible to ignore the dead air was gone the captions '
             'matched and the colour finally looked like the room it was shot in nobody opened an editing app all week').split()


def match_page(c, e, j, wx, wy):
    """One article page, with the key word in a red box locked at (wx, wy)."""
    W, H = c.W, c.H; rnd = random.Random(31 + j)
    paper = [(246, 243, 236), (236, 229, 212), (251, 251, 250), (241, 236, 228), (232, 232, 230), (248, 240, 228)][j % 6]
    kind = ['serif', 'mont', 'ui', 'serif', 'anton', 'monts'][j % 6]
    size = W * [0.085, 0.07, 0.072, 0.095, 0.08, 0.068][j % 6]; lh = size * 1.22
    word = e.o.get('text', 'Claude'); red = rgb(e.o.get('color'), (214, 40, 40))
    im = Image.new('RGB', (W, H), paper); d = ImageDraw.Draw(im); ink = (40, 38, 36)
    zh = e.o.get('lang', 'zh') != 'en'
    if zh:  # 繁中報紙：把內文切成 2 到 4 個字一組，字之間不留空格
        txt = re.sub(r'[，。、；：！？「」]', '', ZH_FILLER); toks = []; i = 0; rr = random.Random(5)
        while i < len(txt): n = rr.choice((2, 3, 4)); toks.append(txt[i:i + n]); i += n
        kind = ['serif', 'mont', 'ui', 'serif', 'bold', 'monts'][j % 6]
    f = font(kind, size); base = f.getbbox('Ag'); asc = -base[1]
    ww = f.getlength(word); bx0 = wx - ww / 2
    def run(x, y, direction):
        while (x < W + size if direction > 0 else x > -size * 6):
            w_ = rnd.choice(toks) if zh else rnd.choice(MATCH_TXT) + ' '
            if direction < 0: x -= f.getlength(w_)
            d.text((x, y), w_, font=f, fill=ink)
            if direction > 0: x += f.getlength(w_)
    off = rnd.uniform(0, size * 3)
    ys = wy - asc - lh * math.ceil((wy - asc) / lh + 1)
    y = ys
    while y < H + lh:
        if abs(y - (wy - asc)) < 1: pass
        else: run(-off - rnd.uniform(0, size * 4), y, 1)
        y += lh
    ky = wy - asc
    d.rectangle([0, ky - lh * 0.1, W, ky + lh * 0.95], fill=paper)
    run(bx0 - size * 0.45, ky, -1); run(bx0 + ww + size * 0.45, ky, 1)
    a = np.asarray(im, np.float32) / 255
    bl = cv2.GaussianBlur(a, (0, 0), W * 0.006)
    yy, xx = np.ogrid[0:H, 0:W]
    dd = np.clip((((xx - wx) / (W * 0.62)) ** 2 + ((yy - wy) / (H * 0.32)) ** 2) - 0.15, 0, 1)[..., None]
    a = a * (1 - dd) + bl * dd
    a *= (1 - 0.18 * np.clip(dd * 1.4, 0, 1))
    pg = Image.fromarray((a * 255).astype(np.uint8)).convert('RGBA')
    bf = font(kind, size); bb = bf.getbbox(word); padx, pady = size * 0.22, size * 0.12
    box = rrect(ww + 2 * padx, (bb[3] - bb[1]) + 2 * pady + size * 0.08, size * 0.08, red + (255,))
    ImageDraw.Draw(box).text((padx, pady - bb[1]), word, font=bf, fill=(255, 255, 255, 255))
    pg.alpha_composite(box, (int(bx0 - padx), int(wy - asc + bb[1] - pady)))
    return np.asarray(pg.convert('RGB'), np.uint8)


@effect('match-cut', 'news pages cut on one word, locked in place behind your head')
def fx_match_cut(c, e):
    k = clamp(c.lt / 0.06) * fade(c, e, 0.12)
    face_cam(c, 1 + 0.06 * ease_out(c.lt / e.d), 0.44)
    wx, wy = cached(e, 'anchor', lambda: (c.W / 2, max(c.H * 0.1, c.fy - c.fw * 1.55)))
    durs = [0.15, 0.15, 0.17, 0.19, 0.22, 0.26, 0.3, 0.45]; t, j = c.lt, 0
    while j < len(durs) - 1 and t > durs[j]: t -= durs[j]; j += 1
    pg = cached(e, ('pg', j), lambda: match_page(c, e, j, wx, wy)).astype(np.float32) / 255
    m = c.m[..., None]
    c.img = c.img * (1 - k) + (pg * (1 - m) + c.img * m) * k


@effect('apple-toggles', 'an iPhone settings card under your chin flips its switches on, one line at a time')
def fx_apple_toggles(c, e):
    rows = e.o.get('text', 'One clip|Type /effects|Zero editing apps').split('|')
    if e.o.get('pos', 'above') != 'below': face_cam(c, 1 + (float(e.o.get('zoom', 1.12)) - 1) * ease_out(c.lt / 0.5), 0.56)
    W = c.W; cw = int(W * 0.72); rh = int(W * 0.125); ch = rh * len(rows); r = int(W * 0.055)
    tw, th = int(W * 0.135), int(W * 0.08); tx = cw - int(W * 0.05) - tw
    def base():
        im = rrect(cw, ch, r, (255, 255, 255, 250)); d = ImageDraw.Draw(im)
        f = font('ui', W * 0.05)
        for i, s in enumerate(rows):
            d.text((W * 0.05, i * rh + rh / 2), s, font=f, fill=(18, 18, 20, 255), anchor='lm')
            if i: d.line([(W * 0.05, i * rh), (cw, i * rh)], fill=(222, 222, 226, 255), width=max(2, W // 900))
        pad = max(10, W // 60) * 2 + W // 90
        return shadowed(im, max(10, W // 60), W // 90, 110), pad
    sh, pad = cached(e, 'base', base)
    ts = [float(x) for x in e.o['ticks'].split('|')] if e.o.get('ticks') else [0.45 + 0.34 * i for i in range(len(rows))]
    im = sh.copy(); d = ImageDraw.Draw(im)
    off, on = np.float32((233, 233, 235)), np.float32(rgb(e.o.get('color'), (52, 199, 89)))
    for i in range(len(rows)):
        u = ease_out((c.lt - ts[i]) / 0.2) if i < len(ts) else 0.0
        col = tuple(int(v) for v in off * (1 - u) + on * u) + (255,)
        x0, y0 = pad + tx, pad + i * rh + (rh - th) / 2
        d.rounded_rectangle([x0, y0, x0 + tw, y0 + th], th // 2, fill=col)
        kr = th / 2 - W * 0.006; kx = x0 + th / 2 + (tw - th) * u; ky = y0 + th / 2
        d.ellipse([kx - kr, ky - kr + W * 0.002, kx + kr, ky + kr + W * 0.004], fill=(0, 0, 0, 40))
        d.ellipse([kx - kr, ky - kr, kx + kr, ky + kr], fill=(255, 255, 255, 255))
    q = pop(c, 0.0, 0.38); al = fade(c, e) * clamp(c.lt / 0.1)
    if e.o.get('pos', 'above') == 'below':
        place(c, im, c.W / 2, min(c.H - ch * 0.75, c.fy + c.fw * 2.5), 0.6 + 0.4 * q, 0, al, guard=True); return
    # above you, tucked behind your head: your hair overlaps only the bottom edge
    cy = max(c.H * 0.08 + ch / 2, c.fy - c.fw * 0.95 + c.fw * float(e.o.get('overlap', 0.08)) - ch / 2)
    place(c, im, c.W / 2, cy + (1 - q) * c.W * 0.04, 0.6 + 0.4 * q, 0, al, behind=True)


@effect('led-sign', 'the lights drop and a glowing LED sign types itself out behind you')
def fx_led_sign(c, e):
    k = ramp(c, e, 0.2, 0.2)
    face_cam(c, 1 + (float(e.o.get('push', 1.08)) - 1) * ease_inout(c.lt / e.d), 0.42)
    lines = e.o.get('text', 'CLAUDE').upper().split('|'); col = np.float32(rgb(e.o.get('color'), (255, 146, 48))) / 255
    def setup():
        mats = []
        for s in lines:
            f = font('uib', 40); w = int(f.getlength(s)) + 8
            im = Image.new('L', (w, 56), 0); ImageDraw.Draw(im).text((4, 2), s, font=f, fill=255)
            bb = im.getbbox() or (0, 0, w, 56); im = im.crop(bb)
            rows = 11; cols = max(1, round(im.width / im.height * rows))
            mats.append(np.asarray(im.resize((cols, rows), Image.BOX), np.float32) / 255 > 0.42)
        cols = max(m.shape[1] for m in mats) + 2
        cell = int(min(c.W * 0.96 / cols, c.H * 0.3 / (len(mats) * 12)))
        L = np.zeros((len(mats) * 12 - 1, cols), np.float32)
        for i, m in enumerate(mats): o = (cols - m.shape[1]) // 2; L[i * 12:i * 12 + 11, o:o + m.shape[1]] = m
        yy, xx = np.mgrid[0:cell, 0:cell].astype(np.float32); rr = np.hypot(xx - cell / 2 + 0.5, yy - cell / 2 + 0.5)
        dot = np.clip(cell * 0.36 - rr + 0.5, 0, 1)
        return L, cell, dot, np.random.default_rng(3).random(L.shape).astype(np.float32)
    L, cell, dot, rnd = cached(e, 'm', setup)
    rows, cols = L.shape
    sweep = clamp((c.lt - 0.15) / 0.75) * (cols + 4)
    lit = L * np.clip((sweep - np.arange(cols)[None, :]) / 3, 0, 1)
    flick = 0.82 + 0.18 * np.sin(rnd * 50 + c.lt * 30)
    b = np.maximum(lit * flick, 0.09)
    pan = np.kron(b, dot)[..., None] * col
    glow = cv2.GaussianBlur(pan, (0, 0), cell * 0.9)
    pan = np.clip(pan + glow * 1.6, 0, 1)
    ph, pw = pan.shape[:2]; x0 = int(c.W / 2 - pw / 2)
    y0 = int(max(c.H * 0.03, c.fy - c.fw * 0.75 - ph))
    xx, yy = grid(c)
    d = ((xx - c.fx) / (c.W * 0.6)) ** 2 + ((yy - (c.fy + c.H * 0.25)) / (c.H * 0.55)) ** 2
    bright = 1 - k * (0.84 - 0.3 * np.clip(1 - d, 0, 1))
    c.img *= (bright * (1 - c.m) + c.m * (1 - 0.18 * k))[..., None]
    xa, xb = max(0, x0), min(c.W, x0 + pw); ya, yb = max(0, y0), min(c.H, y0 + ph)
    if xb > xa and yb > ya:
        sub = pan[ya - y0:yb - y0, xa - x0:xb - x0] * k * (1 - c.m[ya:yb, xa:xb, None])
        c.img[ya:yb, xa:xb] = np.clip(c.img[ya:yb, xa:xb] + sub, 0, 1)


@effect('slow-push', 'a slow cinematic push-in from the wide shot to your face, the room melting out of focus')
def fx_slow_push(c, e):
    p = ease_inout(c.lt / e.d)
    face_cam(c, 1 + (float(e.o.get('zoom', 1.6)) - 1) * p, 0.4)
    s = c.W * float(e.o.get('blur', 0.006)) * p
    if s > 0.6:
        bl = cv2.GaussianBlur(c.img, (0, 0), s); m = c.m[..., None]
        c.img = c.img * m + bl * (1 - m)
    vignette(c, 0.25 * p)


# ---------- pack 3 looks: sparkle spotlight, editorial cover, glass bento (added 23 Oct 2026) ----------
def star(size, color=(255, 244, 222)):
    """A 4-point sparkle with a soft glow."""
    s = max(8, int(size)); h = s / 2; t = s * 0.075
    im = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(im).polygon([(h, s * 0.02), (h + t, h - t), (s * 0.98, h), (h + t, h + t), (h, s * 0.98), (h - t, h + t), (s * 0.02, h), (h - t, h - t)], fill=tuple(color) + (255,))
    g = im.filter(ImageFilter.GaussianBlur(s * 0.07)); out = Image.alpha_composite(g, g); out.alpha_composite(im)
    r = s * 0.07; ImageDraw.Draw(out).ellipse([h - r, h - r, h + r, h + r], fill=(255, 255, 255, 255))
    return out


def gradient_text(s, size, kind, top, bot, glow=None):
    """Text filled with a vertical colour gradient (gold, chrome...), with an optional glow."""
    f = font(kind, size); bb = f.getbbox(s); pad = int(size * 0.25 + (glow[1] * 2.5 if glow else 0))
    w, h = bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).text((pad - bb[0], pad - bb[1]), s, font=f, fill=255)
    g = np.linspace(0, 1, h)[:, None, None]; col = np.float32(top) * (1 - g) + np.float32(bot) * g
    im = Image.fromarray(np.dstack([np.broadcast_to(col, (h, w, 3)).astype(np.uint8), np.asarray(m)]), 'RGBA')
    if glow:
        gl = Image.new('RGBA', (w, h), tuple(glow[0]) + (0,)); gl.putalpha(m.filter(ImageFilter.GaussianBlur(glow[1])))
        im = Image.alpha_composite(Image.alpha_composite(gl, gl), im)
    return im


def spotlight_sparkle(c, e):
    k = ramp(c, e, 0.25, 0.2); W, H = c.W, c.H
    face_cam(c, 1 + (float(e.o.get('push', 1.12)) - 1) * ease_inout(c.lt / e.d), 0.46)
    gold = np.float32(rgb(e.o.get('color'), (255, 190, 128))) / 255
    xx, yy = grid(c)
    d = ((xx - c.fx) / (W * 0.55)) ** 2 + ((yy - (c.fy + H * 0.15)) / (H * 0.5)) ** 2
    pool = np.clip(1 - d, 0, 1) ** 1.5
    c.img *= ((1 - k * (0.92 - 0.3 * pool)) * (1 - c.m) + c.m * (1 + 0.06 * k))[..., None]
    ox, oy = c.fx, c.fy - c.fw * 1.1
    q = 4; sy, sx = np.mgrid[0:H // q, 0:W // q].astype(np.float32) * q
    ang = np.arctan2(sy - oy, sx - ox); rad = np.hypot(sx - ox, sy - oy)
    rays = (0.5 + 0.5 * np.cos(16 * ang + c.lt * 0.9)) ** 5 * np.exp(-rad / (H * 0.42)) + 0.9 * np.exp(-(rad / (H * 0.2)) ** 2)
    rays = cv2.resize(rays.astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)
    halo = np.clip(cv2.GaussianBlur(c.m, (0, 0), W * 0.012) * 1.6 - c.m, 0, 1)
    c.img += (rays * 0.32 + halo * 0.7)[..., None] * gold * k * (1 - c.m[..., None])
    word = e.o.get('text', 'CLAUDE')
    def wimg():
        size = int(H * 0.2)
        while size > 20 and font('didonei', size).getlength(word) > W * 0.86: size = int(size * 0.94)
        im = gradient_text(word, size, 'didonei', (255, 255, 250), (255, 200, 130), glow=(tuple(int(v * 255) for v in gold), size * 0.06))
        im = shadowed(im, int(size * 0.05), 0, 200)
        return np.asarray(im, np.float32) / 255
    wa = cached(e, 'w', wimg); wh, ww = wa.shape[:2]
    band = np.exp(-(((np.arange(ww)[None, :] + np.arange(wh)[:, None] * 0.5) - (-0.3 + 1.6 * clamp((c.lt - 0.25) / 0.9)) * ww * 1.3) / (ww * 0.07)) ** 2)
    w2 = wa.copy(); w2[..., :3] = np.clip(w2[..., :3] + band[..., None] * 0.9, 0, 1)
    s = 1.08 - 0.08 * ease_out(c.lt / 0.5)
    im = Image.fromarray((w2 * 255).astype(np.uint8), 'RGBA')
    place(c, im, W / 2, max(wh * 0.5 + H * 0.06, c.fy - c.fw * 1.05 - wh * 0.28), s, 0, k, behind=True)
    def spots():
        rnd = random.Random(9)
        return [(rnd.uniform(0.04, 0.96), rnd.uniform(0.07, 0.62), rnd.uniform(0.025, 0.07), rnd.uniform(0, 6.3), rnd.uniform(5, 9), rnd.random() < 0.35) for _ in range(48)]
    spr = cached(e, 'star', lambda: star(W * 0.07))
    for x, y, sz, ph, sp, front in cached(e, 'sp', spots):
        a = max(0.0, math.sin(ph + c.lt * sp)) ** 2 * k
        if a < 0.03: continue
        sc = sz / 0.07 * (0.45 + 0.75 * a)
        place(c, spr, x * W, y * H, sc, c.lt * 40 + ph * 30, a, behind=not front, guard=front)


def cover_editorial(c, e):
    k = ease_out(c.lt / 0.35); al = fade(c, e); W, H = c.W, c.H
    lum = (c.img @ np.float32([0.299, 0.587, 0.114]))[..., None]
    soft = (c.img * 0.82 + lum * 0.18) * 0.9 + np.float32((252, 238, 228)) / 255 * 0.1
    q = 4; bl = cv2.resize(np.clip(c.img[::q, ::q] - 0.62, 0, 1), (W, H), interpolation=cv2.INTER_LINEAR)
    bloom = cv2.GaussianBlur(bl, (0, 0), W * 0.012)
    c.img = c.img * (1 - k) + np.clip(soft + bloom * 0.55, 0, 1) * k
    ink, rose = rgb(e.o.get('color'), (26, 20, 22)), rgb(e.o.get('accent'), (168, 70, 94))
    cream = (252, 244, 236)
    title = e.o.get('text', 'EFFECTS').upper()
    def mast():
        size = int(H * 0.16)
        while size > 20 and font('didoneb', size).getlength(title) + size * 0.04 * len(title) > W * 0.92: size = int(size * 0.95)
        return tracked(title, size, 'didoneb', ink, size * 0.04)
    m = cached(e, 'm', mast)
    s = 1.05 - 0.05 * ease_out(c.lt / 0.5)
    place(c, m, W / 2, H * 0.085 + m.height / 2, s, 0, al * k, behind=True)
    iss = cached(e, 'i', lambda: tracked(e.o.get('issue', 'THE ONE-CLIP ISSUE  ·  NO. 42  ·  OCTOBER 2026'), int(W * 0.022), 'ui', ink, W * 0.006))
    place(c, iss, W / 2, H * 0.075, alpha=al * k, behind=True)
    rule = cached(e, 'r', lambda: rrect(W * 0.86, max(3, W // 600), 1, ink + (255,)))
    place(c, rule, W / 2, H * 0.087 + m.height, alpha=al * k * 0.8, behind=True)
    lines = e.o.get('lines', 'One clip,|42 looks.|NO EDITOR  ·  NO APPS').split('|')
    styles = [('didonei', 0.085, ink), ('didoneb', 0.105, rose), ('ui', 0.03, ink)]
    y = H * float(e.o.get('lines_y', 0.575))
    for j, ln in enumerate(lines):
        kind, sz, col = styles[min(j, 2)]
        im = cached(e, ('l', j), lambda: (tracked(ln, int(W * sz), kind, col, W * 0.006) if kind == 'ui' else text_img(ln, W * sz, kind, col, glow=(cream, W * 0.012))))
        kj = ease_out((c.lt - 0.2 - 0.1 * j) / 0.35)
        comp(c, im, W * 0.05 - (1 - kj) * W * 0.03, y, al * kj); y += im.height * (0.82 if kind != 'ui' else 1.6)
    right = e.o.get('right', 'the art of the|effortless edit').split('|')
    y = H * float(e.o.get('right_y', 0.715))
    for j, ln in enumerate(right):
        im = cached(e, ('r', j), lambda: text_img(ln, W * 0.058, 'didonei', ink, glow=(cream, W * 0.01)))
        kj = ease_out((c.lt - 0.45 - 0.1 * j) / 0.35)
        comp(c, im, W * 0.95 - im.width + (1 - kj) * W * 0.03, y, al * kj); y += im.height * 0.78


def donut(size, pct, col, label, value):
    S = int(size) * 2; im = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im); w = int(S * 0.1); pad = int(S * 0.08)
    d.arc([pad, pad, S - pad, S - pad], 0, 360, fill=(255, 255, 255, 46), width=w)
    if pct > 0.002: d.arc([pad, pad, S - pad, S - pad], -90, -90 + 360 * pct, fill=tuple(col) + (255,), width=w)
    f = font('uib', S * 0.2); d.text((S / 2, S / 2 - S * 0.02), value, font=f, fill=(255, 255, 255, 255), anchor='mm')
    f2 = font('mono', S * 0.065); d.text((S / 2, S / 2 + S * 0.15), label.upper(), font=f2, fill=(255, 255, 255, 170), anchor='mm')
    return im.resize((int(size), int(size)), Image.LANCZOS)


def glass_bento(c, e):
    W, H = c.W, c.H; al = fade(c, e) * clamp(c.lt / 0.12)
    if al <= 0: return
    green = rgb(e.o.get('color'), (52, 211, 110)); peach = (255, 160, 122)
    # 1. the big graph, on a smoked glass screen behind you
    q = ease_out(c.lt / 0.4); pw, ph = int(W * 0.9), int(H * 0.3); pcx, pcy = W / 2, H * 0.08 + ph / 2 + (1 - q) * H * 0.02
    pan = glass(c, pw, ph, W * 0.04, pcx, pcy, amt=0.06, dark=0.62, blur=max(10, W // 30))
    lay = Image.new('RGBA', (pw, ph), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); pad = pw * 0.05
    g = ease_inout((c.lt - 0.2) / max(0.3, e.d * 0.75))
    d.text((pad, pad * 0.8), e.o.get('text', 'VIEWS').upper(), font=font('mono', pw * 0.026), fill=(255, 255, 255, 180))
    a, _, _ = num_parts(e.o.get('from', '0')); b, suf, dp = num_parts(e.o.get('to', '197K')); s = f'{a + (b - a) * g:.{dp}f}{suf}'
    f = font('uib', pw * 0.085); d.text((pw - pad - f.getlength(s), pad * 0.45), s, font=f, fill=(255, 255, 255, 255))
    x0, x1, y0, y1 = pad, pw - pad, ph - pad * 0.8, ph * 0.3
    for j in range(1, 4): yy = y0 - (y0 - y1) * j / 3.3; d.line([(x0, yy), (x1, yy)], fill=(255, 255, 255, 34), width=max(1, W // 1000))
    n = 80; pts = [(x0 + (x1 - x0) * j / n, y0 - (y0 - y1) * ((j / n) ** 1.7) + math.sin(j / n * 17) * ph * 0.02 * (1 - j / n)) for j in range(int(n * g) + 1)]
    if len(pts) > 1:
        area = Image.new('RGBA', (pw, ph), (0, 0, 0, 0)); ImageDraw.Draw(area).polygon(pts + [(pts[-1][0], y0), (x0, y0)], fill=green + (60,)); lay.alpha_composite(area)
        lw = max(4, int(pw * 0.006)); gl = Image.new('RGBA', (pw, ph), (0, 0, 0, 0)); ImageDraw.Draw(gl).line(pts, fill=green + (255,), width=lw * 3, joint='curve')
        lay.alpha_composite(gl.filter(ImageFilter.GaussianBlur(lw * 2))); ImageDraw.Draw(lay).line(pts, fill=green + (255,), width=lw, joint='curve')
        hx, hy = pts[-1]; r = lw * 2; ImageDraw.Draw(lay).ellipse([hx - r, hy - r, hx + r, hy + r], fill=(255, 255, 255, 255), outline=green + (255,), width=lw // 2)
    pan.alpha_composite(lay)
    place(c, pan, pcx, pcy, alpha=al * q, behind=True)
    # 2. the bento tiles in front of you
    def tile(i, cx, cy, tw, th, draw):
        k = pop(c, 0.15 + 0.12 * i, 0.4)
        if k <= 0: return
        t = glass(c, tw, th, W * 0.035, cx, cy, amt=0.08, dark=0.5, blur=max(10, W // 34))
        draw(t, ImageDraw.Draw(t), tw, th); place(c, shadowed(t, max(8, W // 80), W // 120, 90), cx, cy, 0.7 + 0.3 * k, 0, al * clamp(k * 2))
    dv, dl = (e.o.get('donut', '29%::ERASE share').split('::') + [''])[:2]; pct = num_parts(dv)[0] / 100
    def dr_donut(t, d, tw, th):
        p = ease_out((c.lt - 0.35) / 0.8) * pct
        dn = donut(tw * 0.86, p, peach, dl, f'{round(p * 100)}%'); t.alpha_composite(dn, (int((tw - dn.width) / 2), int((th - dn.height) / 2)))
    kv, kl = (e.o.get('kpi', '672K::views · top 7 reels').split('::') + [''])[:2]
    def dr_kpi(t, d, tw, th):
        b, suf, dp = num_parts(kv); v = b * ease_out((c.lt - 0.45) / 0.8)
        d.text((tw * 0.1, th * 0.18), f'{v:.{dp}f}{suf}', font=font('uib', th * 0.36), fill=(255, 255, 255, 255))
        d.text((tw * 0.1, th * 0.7), kl.upper(), font=font('mono', th * 0.1), fill=(255, 255, 255, 170))
    bv, bl = (e.o.get('bars', '197|140|124|83|50::top reels · K views').split('::') + [''])[:2]; vals = [num_parts(v)[0] for v in bv.split('|')]
    def dr_bars(t, d, tw, th):
        d.text((tw * 0.1, th * 0.06), bl.upper(), font=font('mono', tw * 0.055), fill=(255, 255, 255, 170))
        n = len(vals); bw = tw * 0.8 / n; top, base = th * 0.2, th * 0.88; mx = max(vals)
        for j, v in enumerate(vals):
            kk = ease_out((c.lt - 0.4 - 0.08 * j) / 0.5); hgt = (base - top) * v / mx * kk; x = tw * 0.1 + j * bw
            d.rounded_rectangle([x + bw * 0.14, base - hgt, x + bw * 0.86, base], int(bw * 0.18), fill=(green if j == 0 else (255, 255, 255)) + (255 if j == 0 else 150,))
            if kk > 0.6: d.text((x + bw / 2, base - hgt - tw * 0.02), f'{v:g}', font=font('uib', tw * 0.06), fill=(255, 255, 255, 230), anchor='md')
    tw = W * 0.25; gap = W * 0.02; ty = max(H * 0.5, c.fy + c.fw * 1.1)
    tile(0, W * 0.15, ty + tw * 0.5, tw, tw, dr_donut)
    tile(1, W * 0.15, ty + tw + gap + tw * 0.28, tw, tw * 0.56, dr_kpi)
    tile(2, W * 0.85, ty + tw * 0.65, tw, tw * 1.3, dr_bars)


# ---------- pack 4: over-the-shoulder zoom, messages, place-in-grid (added 27 Oct 2026) ----------
GREEN = (52, 211, 102)


def liquid_glass(c, box, r=None, blur=None):
    """Liquid glass panel on c.img, after liquid-glass-js (MIT, dashersw): rounded-rect SDF, edge + rim refraction
    along the normal, a light blur so the room still shows through, a faint top-to-bottom tint, a specular rim lit
    from the top-left, plus a red/blue fringe at the edge (after React Bits' GlassSurface)."""
    x0, y0, x1, y1 = [int(round(v)) for v in box]; w, h = x1 - x0, y1 - y0
    if w < 8 or h < 8: return
    u = c.W / 2160; r = r or 72 * u; M = int(140 * u)
    X0, Y0, X1, Y1 = max(0, x0 - M), max(0, y0 - M), min(c.W, x1 + M), min(c.H, y1 + M)
    tex = cv2.GaussianBlur(c.img[Y0:Y1, X0:X1], (0, 0), blur or 7 * u)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    q = np.stack([np.abs(xx - w / 2) - (w / 2 - r), np.abs(yy - h / 2) - (h / 2 - r)], -1)
    sdf = np.linalg.norm(np.maximum(q, 0), axis=-1) + np.minimum(np.maximum(q[..., 0], q[..., 1]), 0) - r
    d = np.maximum(-sdf, 0) / u
    nx, ny = xx - w / 2, yy - h / 2; nl = np.sqrt(nx * nx + ny * ny) + 1e-3; nx, ny = nx / nl, ny / nl
    k = (70 * np.exp(-d / 14) + 34 * np.exp(-d / 70) + 10 * np.exp(-d / 260)) * u
    out = np.zeros((h, w, 3), np.float32)
    for ch, fr in enumerate((1.10, 1.0, 0.90)):
        mx = (xx + x0 - X0 + nx * k * fr).astype(np.float32); my = (yy + y0 - Y0 + ny * k * fr).astype(np.float32)
        out[..., ch] = cv2.remap(tex[..., ch], mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    out = out * 0.86 + 0.06 * (1.0 - 0.30 * (yy / h))[..., None] - 0.05
    spec = np.exp(-d / 5) * np.clip(0.55 - 0.45 * (nx * 0.6 + ny * 0.8), 0, 1)
    out = np.clip(out + (spec * 0.85 + np.exp(-d / 30) * 0.10)[..., None], 0, 1)
    a = np.clip(0.5 - sdf, 0, 1)[..., None]
    gx0, gy0, gx1, gy1 = max(0, x0), max(0, y0), min(c.W, x1), min(c.H, y1)
    sl = (slice(gy0 - y0, gy1 - y0), slice(gx0 - x0, gx1 - x0))
    dst = c.img[gy0:gy1, gx0:gx1]; dst[:] = dst * (1 - a[sl]) + out[sl] * a[sl]


def split_num(s):
    """'197K' -> (197.0, 'K', 0 decimals); '82%' -> (82.0, '%', 0); '1.2M' -> (1.2, 'M', 1)."""
    import re as _re
    m = _re.match(r'\s*([\d.,]+)\s*(.*)', str(s)); n = m.group(1).replace(',', '') if m else '0'
    return float(n), (m.group(2) if m else ''), (len(n.split('.')[1]) if '.' in n else 0)


def glass_graph(c, cx, cy, k, prog, label, value, kind, scale=1.0):
    """A see-through glass stat card: spaced-caps label, a number that counts up, a glowing line or bar chart."""
    if k <= 0: return
    u = c.W / 2160 * scale; sc = 0.82 + 0.18 * ease_back(k)
    w, h = 1760 * u * sc, 1056 * u * sc; lift = 40 * u * (1 - k)
    x0, y0 = cx - w / 2, cy - h / 2 + lift
    liquid_glass(c, (x0, y0, x0 + w, y0 + h))
    v = w / 1500
    lay = Image.new('RGBA', (int(w) + 40, int(h) + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); o = 20
    lab, big = font('uim', 44 * v), font('uib', 170 * v)
    num, suf, dec = split_num(value); txt = f'{num * ease_out(prog):.{dec}f}{suf}'
    xx = o + 64 * v
    for chh in label.upper(): d.text((xx, o + 64 * v), chh, font=lab, fill=(255, 255, 255, 235)); xx += lab.getlength(chh) + 9 * v
    d.text((o + w - 70 * v - big.getlength(txt), o + 40 * v), txt, font=big, fill=(255, 255, 255, 255))
    gx0, gx1, gy0, gy1 = o + 64 * v, o + w - 64 * v, o + 290 * v, o + h - 80 * v
    for j in range(3): d.line([gx0, gy0 + (gy1 - gy0) * j / 2, gx1, gy0 + (gy1 - gy0) * j / 2], fill=(255, 255, 255, 70), width=max(1, int(3 * v)))
    halo = Image.new('RGBA', lay.size, (0, 0, 0, 0)); hd = ImageDraw.Draw(halo)
    xx = o + 64 * v
    for chh in label.upper(): hd.text((xx, o + 64 * v), chh, font=lab, fill=(0, 0, 0, 150)); xx += lab.getlength(chh) + 9 * v
    hd.text((o + w - 70 * v - big.getlength(txt), o + 40 * v), txt, font=big, fill=(0, 0, 0, 150))
    base = halo.filter(ImageFilter.GaussianBlur(10 * v))
    chart = Image.new('RGBA', lay.size, (0, 0, 0, 0)); cd = ImageDraw.Draw(chart)
    if kind == 'line':
        ys = [0.04, 0.07, 0.10, 0.16, 0.22, 0.35, 0.52, 0.74, 1.0]; n = max(0.02, (len(ys) - 1) * ease_out(prog)); pts = []
        for i in range(int(n) + 1):
            t = min(i, n); i0 = min(int(t), len(ys) - 2); f = t - i0; yv = ys[i0] + (ys[i0 + 1] - ys[i0]) * f
            pts.append((gx0 + (gx1 - gx0) * t / (len(ys) - 1), gy1 - (gy1 - gy0) * yv))
        if len(pts) > 1:
            cd.polygon(pts + [(pts[-1][0], gy1), (pts[0][0], gy1)], fill=GREEN + (70,))
            gl = Image.new('RGBA', lay.size, (0, 0, 0, 0)); ImageDraw.Draw(gl).line(pts, fill=GREEN + (255,), width=int(60 * v), joint='curve')
            chart.alpha_composite(gl.filter(ImageFilter.GaussianBlur(26 * v)))
            cd = ImageDraw.Draw(chart); cd.line(pts, fill=GREEN + (255,), width=max(2, int(20 * v)), joint='curve')
            ex, ey = pts[-1]
            cd.ellipse([ex - 30 * v, ey - 30 * v, ex + 30 * v, ey + 30 * v], fill=GREEN + (90,)); cd.ellipse([ex - 15 * v, ey - 15 * v, ex + 15 * v, ey + 15 * v], fill=(235, 255, 240, 255))
    else:
        vals = [1.0, 0.71, 0.63, 0.42, 0.25, 0.20, 0.19]; bw = (gx1 - gx0) / len(vals)
        for i, val in enumerate(vals):
            g = ease_out(clamp(prog * 1.6 - i * 0.1)); top = gy1 - (gy1 - gy0) * val * g; bx = gx0 + i * bw + bw * 0.16
            if i == 0:
                gl = Image.new('RGBA', lay.size, (0, 0, 0, 0)); ImageDraw.Draw(gl).rounded_rectangle([bx, top, bx + bw * 0.68, gy1], int(18 * v), fill=GREEN + (230,))
                chart.alpha_composite(gl.filter(ImageFilter.GaussianBlur(22 * v))); cd = ImageDraw.Draw(chart)
            cd.rounded_rectangle([bx, top, bx + bw * 0.68, gy1], int(18 * v), fill=GREEN + (230 if i == 0 else 120,))
    base.alpha_composite(chart); base.alpha_composite(lay)
    comp(c, base, x0 - o, y0 - o)


@effect('over-the-shoulder-zoom', 'the camera pushes into one top corner, a liquid glass graph pops beside your head, then the other corner with a second graph')
def fx_over_the_shoulder_zoom(c, e):
    p = clamp(c.lt / e.d); z0 = float(e.o.get('zoom', 2.0))
    lx, rx = c.fx - c.W * 0.17, c.fx + c.W * 0.19
    keys = [(0, 1.0, c.fx, c.fy), (0.30, 1.04, c.fx, c.fy), (0.46, z0, lx, c.fy), (0.66, z0 + 0.04, lx, c.fy), (0.76, 1.05, c.fx, c.fy), (0.87, z0, rx, c.fy), (1.0, z0 + 0.04, rx, c.fy)]
    for (pa, za, xa, ya), (pb, zb, xb, yb) in zip(keys, keys[1:]):
        if pa <= p <= pb: q = ease_inout((p - pa) / (pb - pa)); z, x, y = za + (zb - za) * q, xa + (xb - xa) * q, ya + (yb - ya) * q; break
    camera(c, z, x, y)
    k1 = clamp((p - 0.42) / 0.065) * (1 - clamp((p - 0.66) / 0.055)); k2 = clamp((p - 0.84) / 0.065)
    if k1 <= 0 and k2 <= 0: return
    me, m = c.img.copy(), c.m[..., None]
    a, b = (e.o.get('text') or 'Views · this reel|Top reels · total').split('|')[:2]
    va, vb = (str(e.o.get('to') or '197K|672K')).split('|')[:2]
    glass_graph(c, c.W * 0.43, c.H * 0.255, k1, clamp((p - 0.45) / 0.17), a, va, 'line')
    glass_graph(c, c.W * 0.57, c.H * 0.255, k2, clamp((p - 0.86) / 0.14), b, vb, 'bars')
    c.img = c.img * (1 - m) + me * m   # your head stays in front of the cards


def msg_bubble(c, y, title, body, a):
    """One creamy glass iMessage notification with a soft white halo, centred at height y."""
    u = c.W / 2160; w, h = int(1880 * u), int(330 * u); x0 = (c.W - w) // 2; y0 = int(y - h / 2)
    if a <= 0 or y0 + h < 0 or y0 > c.H: return
    s = 0.82 + 0.18 * ease_back(a); ww, hh = int(w * s), int(h * s); xs, ys = (c.W - ww) // 2, int(y - hh / 2)
    halo = Image.new('RGBA', (ww + int(240 * u), hh + int(240 * u)), (0, 0, 0, 0)); p = int(120 * u)
    ImageDraw.Draw(halo).rounded_rectangle([p - 30 * u, p - 30 * u, p + ww + 30 * u, p + hh + 30 * u], int(100 * u), fill=(255, 250, 240, int(215 * clamp(a * 2))))
    comp(c, halo.filter(ImageFilter.GaussianBlur(56 * u)), xs - p, ys - p)
    gx0, gy0, gx1, gy1 = max(0, xs), max(0, ys), min(c.W, xs + ww), min(c.H, ys + hh)
    if gx1 <= gx0 or gy1 <= gy0: return
    reg = cv2.GaussianBlur(c.img[gy0:gy1, gx0:gx1], (0, 0), 20 * u)
    yy = np.linspace(0, 1, gy1 - gy0, dtype=np.float32)[:, None, None]
    reg = reg * (1 - 0.78) + np.float32([252, 246, 238]) / 255 * 0.78 + (1 - yy) * 0.08
    mk = Image.new('L', (ww, hh), 0); ImageDraw.Draw(mk).rounded_rectangle([0, 0, ww - 1, hh - 1], int(70 * u * s), fill=255)
    mk = np.asarray(mk, np.float32)[gy0 - ys:gy1 - ys, gx0 - xs:gx1 - xs, None] / 255 * clamp(a * 2.5)
    dst = c.img[gy0:gy1, gx0:gx1]; dst[:] = dst * (1 - mk) + np.clip(reg, 0, 1) * mk
    lay = Image.new('RGBA', (ww, hh), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); v = s * u; al = int(255 * clamp(a * 2.5))
    d.rounded_rectangle([1, 1, ww - 2, hh - 2], int(70 * v), outline=(255, 255, 255, int(170 * clamp(a * 2.5))), width=max(1, int(3 * v)))
    ic = np.linspace(0, 1, int(160 * v), dtype=np.float32)[:, None]
    icon = np.dstack([110 - ic * 64, 232 - ic * 51, 120 - ic * 51, np.full_like(ic, 255)]).repeat(int(160 * v), 1).astype(np.uint8)
    icon = Image.fromarray(icon, 'RGBA'); im_ = Image.new('L', icon.size, 0); ImageDraw.Draw(im_).rounded_rectangle([0, 0, icon.width - 1, icon.height - 1], int(40 * v), fill=al); icon.putalpha(im_)
    ImageDraw.Draw(icon).ellipse([30 * v, 34 * v, 130 * v, 114 * v], fill=(255, 255, 255, al)); ImageDraw.Draw(icon).polygon([(44 * v, 102 * v), (36 * v, 130 * v), (72 * v, 110 * v)], fill=(255, 255, 255, al))
    lay.alpha_composite(icon, (int(56 * v), int(70 * v)))
    d.text((262 * v, 76 * v), title, font=font('uib', 72 * v), fill=(28, 28, 30, al)); d.text((262 * v, 170 * v), body, font=font('uim', 76 * v), fill=(44, 44, 46, al))
    comp(c, lay, xs, ys)


@effect('messages', 'iMessage notifications pop in one after another, creamy glass with a soft glow, stacking up above the bottom of the frame')
def fx_messages(c, e):
    msgs = (e.o.get('text') or 'how did you edit this??|wait, which app is this|send me the effects pls|EFFECTS').split('|')
    title = e.o.get('title', 'Messages'); n = len(msgs); u = c.W / 2160
    gap = min(0.4, e.d * 0.75 / max(1, n)); pops = [0.13 + i * gap for i in range(n)]
    u2 = c.W / 2160; stack = 165 * u2 + (n - 1) * 365 * u2 + 200 * u2
    bottom = c.H * float(e.o['y']) if e.o.get('y') is not None else min(c.H * 0.97, max(c.H * 0.61, c.fy + c.fw * 1.3 + stack)); out = fade(c, e, 0.2)
    for k in range(n):
        if c.lt < pops[k]: continue
        newer = sum(ease_out(clamp((c.lt - pops[j]) / 0.17)) for j in range(k + 1, n) if c.lt >= pops[j])
        msg_bubble(c, bottom - 165 * u - newer * 365 * u, title, msgs[k], clamp((c.lt - pops[k]) / 0.17) * out)


def views_icon(px):
    """The Instagram 'views' eye: an arc above a teardrop (traced from the IG app)."""
    paths = [[(325, 490), [(-43, -9, -73, -30, -97, -68), (-28, -46, -14, -53, 22, -10), (37, 45, 79, 62, 133, 55), (33, -4, 50, -14, 80, -48), (40, -44, 60, -46, 37, -3), (-29, 52, -112, 87, -175, 74)]],
             [(315, 405), [(-51, -50, -21, -115, 52, -115), (51, 0, 88, 65, 41, 72), (-14, 2, -29, 15, -38, 35), (-8, 18, -19, 33, -23, 33), (-4, 0, -19, -11, -32, -25)]]]
    k = px / 24 * 4; im = Image.new('L', (int(34 * k), int(24 * k)), 0); d = ImageDraw.Draw(im)
    tx = lambda x, y: ((0.1 * x - 19) * k, (80 - 0.1 * y - 29) * k)
    for (sx, sy), segs in paths:
        pts = [tx(sx, sy)]; cx, cy = sx, sy
        for s in segs:
            p0, p1, p2, p3 = (cx, cy), (cx + s[0], cy + s[1]), (cx + s[2], cy + s[3]), (cx + s[4], cy + s[5])
            for j in range(1, 13):
                t = j / 12; pts.append(tx(*[(1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * b + 3 * (1 - t) * t * t * cc + t ** 3 * dd for a, b, cc, dd in zip(p0, p1, p2, p3)]))
            cx, cy = p3
        d.polygon(pts, fill=255)
    im = im.resize((int(34 * px / 24), px), Image.LANCZOS); out = Image.new('RGBA', im.size, (255, 255, 255, 0)); out.putalpha(im); return out


def grid_tile(im, w, h, views, r):
    t = im.convert('RGB'); s = max(w / t.width, h / t.height); t = t.resize((int(t.width * s) + 1, int(t.height * s) + 1), Image.LANCZOS)
    t = t.crop(((t.width - w) // 2, (t.height - h) // 2, (t.width - w) // 2 + w, (t.height - h) // 2 + h)).convert('RGBA')
    mk = Image.new('L', (w, h), 0); ImageDraw.Draw(mk).rounded_rectangle([0, 0, w - 1, h - 1], r, fill=255)
    if views:
        u = w / 660; fd = Image.linear_gradient('L').resize((w, int(h * 0.28))).point(lambda v: int(v * 0.75))
        sh = Image.new('RGBA', fd.size, (0, 0, 0, 0)); sh.putalpha(fd); t.alpha_composite(sh, (0, h - fd.height))
        ic = views_icon(int(56 * u)); x, y = int(34 * u), int(h - 92 * u); t.alpha_composite(ic, (x, y + int(2 * u)))
        ImageDraw.Draw(t).text((x + ic.width + 14 * u, y - 6 * u), views, font=font('uib', 58 * u), fill=(255, 255, 255, 255))
    t.putalpha(mk); ImageDraw.Draw(t).rounded_rectangle([1, 1, w - 2, h - 2], r, outline=(255, 255, 255, 150), width=max(1, int(4 * w / 660)))
    return t


@effect('place-in-grid', 'you shrink into the centre tile of your 3x3 profile grid on frosted glass, then 8 of your reels pop in around you, one per frame, view counts on every tile')
def fx_place_in_grid(c, e):
    W, H = c.W, c.H; g, m = int(33 * W / 2160), int(68 * W / 2160)
    tw = (W - 2 * m - 2 * g) // 3; th = int(tw * 16 / 9); top = (H - (3 * th + 2 * g)) // 2; r = int(28 * W / 2160)
    rect = lambda i: (m + (i % 3) * (tw + g), top + (i // 3) * (th + g))
    views = (e.o.get('views') or '2.4M|847K|1.2M|312K|3.4M|596K|268K|1.8M|3.1M').split('|')
    tiles = cached(e, 'tiles', lambda: [grid_tile(vary(im, i) if e.o.get('images') is None else im, tw, th, views[i % len(views)], r) for i, im in enumerate((e.cards * 8)[:8])])
    me = c.img.copy(); p = ease_inout(clamp(c.lt / 0.45))
    fz = cv2.resize(cv2.GaussianBlur(cv2.resize(me, (W // 8, H // 8)), (0, 0), 14), (W, H), interpolation=cv2.INTER_CUBIC)
    lum = (fz @ np.float32([0.299, 0.587, 0.114]))[..., None]; fz = np.clip(lum + (fz - lum) * 1.25, 0, 1)
    c.img = fz * (1 - 0.37) + np.float32([255, 248, 238]) / 255 * 0.37
    for j, slot in enumerate((1, 5, 7, 3, 2, 8, 6, 0)):
        a = clamp((c.lt - 0.47 - j / 30) / 0.1)
        if a > 0: x, y = rect(slot); place(c, tiles[j], x + tw / 2, y + th / 2, 0.82 + 0.18 * ease_back(a), 0, clamp(a * 2))
    cx, cy = rect(4); w2, h2 = int(W + (tw - W) * p), int(H + (th - H) * p)
    mine = Image.fromarray((np.clip(me, 0, 1) * 255).astype(np.uint8))
    tile = grid_tile(mine, w2, h2, views[8 % len(views)] if p > 0.9 else None, int(r * p))
    comp(c, tile, cx * p, cy * p)
    if p > 0.95: d = Image.new('RGBA', (tw + 8, th + 8), (0, 0, 0, 0)); ImageDraw.Draw(d).rounded_rectangle([2, 2, tw + 5, th + 5], r + 2, outline=(217, 119, 87, 255), width=8); comp(c, d, cx - 4, cy - 4)





# ---------- pack 5: phrase pops starters (added 2 Nov 2026) ----------
INKY, TAPE, CRAYON, CREAMY = (23, 23, 27), (255, 225, 77), (200, 40, 56), (253, 246, 200)
def above_head(c, h): return max(c.H * 0.12 + h / 2, c.fy - c.fw * 1.75)


@effect('tape-label', 'a strip of yellow tape with your line lands on your chest')
def fx_tape_label(c, e):
    k = pop(c, 0.05, 0.25) * fade(c, e)
    if k <= 0: return
    def tape():
        S = int(c.W * 0.055); t = text_img(e.o.get('text', 'your own reels'), S, 'hand', INKY)
        w, h = int(t.width + S * 0.6), int(t.height + S * 0.2); o = max(4, S // 9)
        im = Image.new('RGBA', (w + o, h + o), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.rectangle([o, o, w + o - 1, h + o - 1], fill=(17, 17, 17, 255)); d.rectangle([0, 0, w - 1, h - 1], fill=TAPE + (255,))
        im.alpha_composite(t, ((w - t.width) // 2, (h - t.height) // 2)); return im
    im = cached(e, 'tape', tape)
    place(c, im, c.W / 2, clamp(c.fy + c.fw * 1.6, c.H * 0.45, c.H * 0.68), 0.85 + 0.15 * k, 0, clamp(k * 1.5), guard=True)


@effect('select-resize', 'a blue selection box grabs your number and a cursor drags it bigger')
def fx_select_resize(c, e):
    al = fade(c, e) * clamp(c.lt / 0.08)
    if al <= 0: return
    p = ease_inout((c.lt - 0.25) / 0.7); S = int(c.W * 0.2 * (0.55 + 0.45 * p)) // 4 * 4
    t = cached(e, ('t', S), lambda: text_img(e.o.get('text', '2X'), S, 'didone', CREAMY, shadow=8))
    bw, bh = t.width + c.W * 0.03, t.height; cx, cy = c.W / 2, above_head(c, bh)
    x0, y0 = cx - bw / 2, cy - bh / 2
    lay = Image.new('RGBA', (c.W, c.H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); B = BLUE + (255,); lw = max(2, c.W // 360)
    d.rectangle([x0, y0, x0 + bw, y0 + bh], fill=BLUE + (int(130 * (1 - 0.7 * clamp((c.lt - 0.9) / 0.3))),))
    for (ax, ay, bx, by) in ((x0, y0, x0 + bw, y0), (x0, y0 + bh, x0 + bw, y0 + bh), (x0, y0, x0, y0 + bh), (x0 + bw, y0, x0 + bw, y0 + bh)):
        n = max(1, int(math.hypot(bx - ax, by - ay) / (c.W * 0.018)))
        for j in range(0, n, 2): d.line([(ax + (bx - ax) * j / n, ay + (by - ay) * j / n), (ax + (bx - ax) * (j + 1) / n, ay + (by - ay) * (j + 1) / n)], fill=B, width=lw)
    hs = c.W * 0.009
    for qx, qy in ((x0, y0), (x0 + bw, y0), (x0, y0 + bh), (x0 + bw, y0 + bh)): d.rectangle([qx - hs, qy - hs, qx + hs, qy + hs], fill=(255, 255, 255, 255), outline=B, width=lw)
    comp(c, to_np(lay), 0, 0, al, behind=True); place(c, t, cx, cy, 1, 0, al, behind=True)
    cu = cached(e, 'cu', lambda: cursor(c.W * 0.045)); place(c, cu, x0 + bw + cu.width * 0.4, y0 + bh + cu.height * 0.4, 1, 0, al)


@effect('wave-trim', 'the silent parts of your voice are trimmed away on screen until only your words are left')
def fx_wave_trim(c, e):
    al = pop(c, 0, 0.2) * fade(c, e)
    if al <= 0: return
    p = ease_inout((c.lt - 0.25) / 0.5); pw, ph, ww = c.W * (0.84 - 0.4 * p), c.W * 0.2, c.W * 0.3
    hts = cached(e, 'h', lambda: np.random.default_rng(3).uniform(0.15, 1, 60))
    lay = Image.new('RGBA', (int(pw) + 2, int(ph) + 2), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rectangle([0, 0, pw, ph], fill=INKY + (240,)); cx, cy = pw / 2, ph / 2; st = ww / len(hts)
    for j, h in enumerate(hts):
        x = cx - ww / 2 + j * st; v = h * ph * 0.36 * (0.55 + 0.45 * math.sin(j * 0.33))
        d.rectangle([x, cy - v, x + st * 0.45, cy + v], fill=CREAMY + (255,))
    r, gap = c.W * 0.0045, c.W * 0.016
    for sd in (-1, 1):
        x = cx + sd * (ww / 2 + gap)
        while 0 < x < pw: d.ellipse([x - r, cy - r, x + r, cy + r], fill=RED + (255,)); x += sd * gap
    place(c, lay, c.W / 2, above_head(c, ph), 1, 0, al, behind=True)


@effect('huge-strike', 'one huge serif word fills the wall behind you, then a red line crosses it out')
def fx_huge_strike(c, e):
    al = fade(c, e)
    t = cached(e, 't', lambda: fit_text(e.o.get('text', '8 HOURS'), c.W * 0.9, 'didone', int(c.W * 0.28), fill=CREAMY, shadow=10))
    cw = int(t.width * ease_out(c.lt / 0.35)); cy = above_head(c, t.height)
    if cw > 2: place(c, t.crop((0, 0, cw, t.height)), c.W / 2 - (t.width - cw) / 2, cy, 1, 0, al, behind=True)
    at = float(e.o.get('at', 0.6)); k = ease_out((c.lt - at) / 0.18)
    if k > 0:
        lay = Image.new('RGBA', (c.W, c.H), (0, 0, 0, 0)); x0, x1 = c.W / 2 - t.width * 0.46, c.W / 2 + t.width * 0.46
        pts = [(x0 + (x1 - x0) * u, cy + t.height * 0.04 - u * t.height * 0.05 + math.sin(u * 19) * c.W * 0.002) for u in np.linspace(0, 1, 40)]
        hand_path(ImageDraw.Draw(lay), pts, RED + (255,), max(6, c.W // 80), k); comp(c, to_np(lay), 0, 0, al, behind=True)


@effect('crayon-write', 'a red crayon writes your word behind your head, then underlines it')
def fx_crayon_write(c, e):
    al = fade(c, e)
    t = cached(e, 't', lambda: fit_text(e.o.get('text', 'NOBODY'), c.W * 0.82, 'hand', int(c.W * 0.17), fill=CRAYON, shadow=4))
    p = ease_inout((c.lt - 0.05) / 0.8); cw = int(t.width * p); cy = above_head(c, t.height); x0 = c.W / 2 - t.width / 2
    if cw > 2: place(c, t.crop((0, 0, cw, t.height)), x0 + cw / 2, cy, 1, 0, al, behind=True)
    if c.lt > 0.9:
        lay = Image.new('RGBA', (c.W, c.H), (0, 0, 0, 0)); yy = cy + t.height * 0.42
        pts = [(x0 + t.width * (0.06 + 0.88 * u), yy - u * c.W * 0.006 + math.sin(u * 23) * c.W * 0.002) for u in np.linspace(0, 1, 40)]
        hand_path(ImageDraw.Draw(lay), pts, CRAYON + (255,), max(5, c.W // 95), ease_out((c.lt - 0.9) / 0.25)); comp(c, to_np(lay), 0, 0, al, behind=True)
    def mk():
        L = int(c.W * 0.22); T = int(L * 0.2); im = Image.new('RGBA', (L + T, T), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.polygon([(0, T / 2), (T, 0), (T, T)], fill=(224, 58, 68, 255)); d.rounded_rectangle([T * 0.9, 0, L + T - 1, T - 1], T // 5, fill=(224, 58, 68, 255))
        for xx in (T * 1.5, L + T * 0.4): d.rectangle([xx, 0, xx + T * 0.35, T - 1], fill=(168, 23, 40, 255))
        return shadowed(im.rotate(-38, Image.BICUBIC, expand=True), 6, 4, 100)
    cr = cached(e, 'cr', mk); away = ease_inout((c.lt - 1.1) / 0.3)
    if away < 1:
        tx, ty = x0 + cw + away * c.W * 0.6, cy + math.sin(c.lt * 30) * t.height * 0.12 + away * c.H * 0.2
        place(c, cr, tx + cr.width * 0.47, ty + cr.height * 0.45, 1, 0, al)


@effect('fan-build', 'your reel covers deal into a fan behind your head, one card at a time')
def fx_fan_build(c, e):
    n = int(e.o.get('count', 13)); al = fade(c, e); cw = int(c.W * 0.15)
    cards = cached(e, 'cards', lambda: [card(vary(e.cards[i % len(e.cards)], i) if e.o.get('images') is None else e.cards[i % len(e.cards)], cw, 0.05) for i in range(n)])
    px, py, R = c.fx, c.fy + c.fw * 0.1, c.fw * 2.15
    for i in range(n):
        t0 = 0.055 * i
        if c.lt < t0: break
        q = ease_out((c.lt - t0) / 0.3); a = -95 + (-62 + 124 * i / max(1, n - 1) + 95) * q; r = math.radians(a)
        place(c, cards[i], px + R * math.sin(r), py - R * math.cos(r), 1, -a, al, behind=True)


# ---------- Adam Digital additions: signature effects ----------
import logos


def head_top(e): return e.top if e.top is not None else e.med[1] - e.med[2] * 0.85


@effect('pop-word', 'a huge bold word pops in behind your head, in a brand colour, yellow or white')
def fx_pop_word(c, e):
    word = str(e.o.get('text', 'AI')); u = c.W / 1080
    col = rgb(e.o.get('color'), None) or logos.brand_color(e.o.get('brand')) or (255, 211, 26)
    def mk():
        S = int((440 if e.o.get('size') == 'big' else 245) * u); sp = -6 * u
        while S > 40 and font('pop', S).getlength(word) + sp * (len(word) - 1) > 1010 * u: S = int(S * 0.94)
        room = max(c.H * 0.05, head_top(e) - c.H * 0.03)   # space above your head
        for _ in range(2):
            im = tracked(word, S, 'pop', col, sp); bb = im.getbbox(); gh = (bb[3] - bb[1]) if bb else im.height
            if gh * 0.65 <= room: break
            S = max(40, int(S * room / (gh * 0.65)))
        return shadowed(im.crop(bb) if bb else im, blur=int(26 * u), dy=int(10 * u), alpha=95), gh
    im, gh = cached(e, 'w', mk)
    al = clamp(c.lt / 0.06) * fade(c, e, 0.18)
    if al <= 0: return
    cy = max(head_top(e) - gh * 0.15, c.H * 0.03 + gh / 2)   # your head covers the bottom third of the word
    place(c, im, c.W / 2 * 0.6 + c.fx * 0.4, cy, 1.35 - 0.35 * ease_back(c.lt / 0.22), 0, al, behind=True)


_warned = set()
def warn_once(msg):
    if msg not in _warned: _warned.add(msg); print('Note:', msg, flush=True)


@effect('logo-link', 'two real brand logos pop in beside your face, joined by a dashed line that runs behind your head')
def fx_logo_link(c, e):
    u = c.W / 1080; T = int(144 * u)
    names = [n.strip() for n in str(e.o.get('text', 'claude|notion')).split('|') if n.strip()][:2] or ['claude']
    labels = [s.strip() for s in str(e.o['label']).split('|')] if e.o.get('label') else [logos.title(n) for n in names]
    custom = [s.strip() for s in str(e.o.get('logo', '')).split('|')]
    def tile(i):
        im = rrect(T, T, T * 0.25, (255, 255, 255, 255))
        src = custom[i] if i < len(custom) and custom[i] else names[i]
        lg = logos.logo_image(src, int(88 * u))
        if lg is None:
            warn_once(f"no bundled logo for '{names[i]}'. Pass logo=path/to/logo.png to show the real one.")
            lg = fit_text(names[i], T * 0.8, 'popx', int(T * 0.26), fill=INK)
        im.alpha_composite(lg, ((T - lg.width) // 2, (T - lg.height) // 2))
        im = shadowed(im, int(16 * u), int(6 * u), 90)
        lab = text_img(labels[i] if i < len(labels) else names[i], 30 * u, 'popb', (255, 255, 255), shadow=int(7 * u))
        out = Image.new('RGBA', (max(im.width, lab.width), im.height + int(lab.height * 0.62)), (0, 0, 0, 0))
        out.alpha_composite(im, ((out.width - im.width) // 2, 0)); out.alpha_composite(lab, ((out.width - lab.width) // 2, im.height - int(lab.height * 0.38)))
        return out, (out.width - im.width) // 2 + im.width / 2, im.height / 2
    tiles = cached(e, 'tiles', lambda: [tile(i) for i in range(len(names))])
    fx_, fy_, fw_ = e.med; y = fy_ + c.H * 0.035; lo, hi = T / 2 + c.W * 0.03, c.W - T / 2 - c.W * 0.03
    xs = [clamp(fx_ - c.W * 0.344, lo, hi), clamp(fx_ + c.W * 0.344, lo, hi)] if len(names) == 2 else [clamp(fx_ + c.W * 0.344, lo, hi)]
    out = fade(c, e); tb = min(0.35, e.d * 0.3); starts = [0.0, tb]
    if len(names) == 2 and c.lt > tb + 0.1:   # the dashed link, drawn left to right behind your head
        q = ease_out((c.lt - tb - 0.1) / 0.4); x0, x1 = xs[0] + T * 0.55, xs[1] - T * 0.55; xe = x0 + (x1 - x0) * q
        lay = Image.new('RGBA', (c.W, int(30 * u)), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); my = lay.height / 2
        dash, gap = 22 * u, 16 * u; x = x0 - ((c.lt * 60 * u) % (dash + gap))
        while x < xe:
            a, b = max(x, x0), min(x + dash, xe)
            if b > a: d.line([(a, my), (b, my)], fill=(255, 255, 255, 235), width=max(2, int(6 * u)))
            x += dash + gap
        cols = [logos.brand_color(n) or (255, 211, 26) for n in names]
        for j in range(3):
            p = (c.lt * 0.55 + j / 3) % 1; dx = x0 + (x1 - x0) * p
            if dx <= xe: d.ellipse([dx - 7 * u, my - 7 * u, dx + 7 * u, my + 7 * u], fill=cols[j % 2] + (255,))
        comp(c, to_np(lay), 0, y - lay.height / 2, out, behind=True)
    for i, (im, ax, ay) in enumerate(tiles):
        k = ease_back((c.lt - starts[i]) / 0.3) if c.lt > starts[i] else 0
        if k <= 0: continue
        place(c, im, xs[i] - ax + im.width / 2, y - ay + im.height / 2, 0.4 + 0.6 * k, 0, clamp((c.lt - starts[i]) / 0.1) * out, guard=True)


@effect('card-drop', 'you slide down and a floating card with your screenshot pops in above you')
def fx_card_drop(c, e):
    u = c.W / 1080; cw, ch = int(960 * u), int(700 * c.H / 1920); top = int(150 * c.H / 1920)
    want = clamp(top + ch + 40 * u - head_top(e), c.H * 0.2, c.H * 0.42)   # slide far enough that the card never covers your face
    k = min(ease_inout(c.lt / 0.3), ease_inout((e.d - c.lt) / 0.3)); dy = want * k
    if dy > 1:
        small = cv2.resize(c.img, (c.W // 8, c.H // 8), interpolation=cv2.INTER_AREA)
        bg = cv2.resize(cv2.GaussianBlur(small, (0, 0), 5), (c.W, c.H), interpolation=cv2.INTER_LINEAR) * 0.55
        M = np.float32([[1, 0, 0], [0, 1, dy]])
        c.img = cv2.warpAffine(c.img, M, (c.W, c.H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        c.m = cv2.warpAffine(c.m, M, (c.W, c.H), flags=cv2.INTER_LINEAR); n = int(math.ceil(dy))
        c.img[:n] = bg[:n]; c.fy += dy
    al = clamp(c.lt / 0.1) * clamp((e.d - c.lt - 0.08) / 0.2)
    if al <= 0: return
    def mk():
        im = Image.new('RGBA', (cw, ch), (255, 255, 255, 255)); path = e.o.get('image')
        if path and os.path.exists(str(path)):
            src = Image.open(str(path)).convert('RGB')
            s = max(cw / src.width, ch / src.height) if e.o.get('fit') == 'cover' else min(cw / src.width, ch / src.height)
            src = src.resize((max(1, int(src.width * s)), max(1, int(src.height * s))), Image.LANCZOS)
            im.paste(src, ((cw - src.width) // 2, (ch - src.height) // 2))
        else:
            if path: warn_once(f"card-drop image not found: {path}")
            t = fit_text(str(e.o.get('text', 'Your screenshot here')), cw * 0.84, 'popx', int(70 * u), fill=INK)
            im.alpha_composite(t, ((cw - t.width) // 2, (ch - t.height) // 2))
        m = Image.new('L', (cw, ch), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, cw - 1, ch - 1], int(30 * u), fill=255); im.putalpha(m)
        return shadowed(im, int(60 * u), int(22 * u), 115)
    p = ease_back(c.lt / 0.32); o = clamp((e.d - c.lt) / 0.2)
    place(c, cached(e, 'card', mk), c.W / 2, top + ch / 2 + (1 - clamp(p)) * 50 * u, (0.88 + 0.12 * p) * (0.94 + 0.06 * o), 0, al)
    c.cardbot = top + ch


_dotf, _paper = {}, {}
def dot_field(W, H, cell):
    k = (W, H, round(cell, 3))
    if k not in _dotf:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        _dotf[k] = np.sqrt(((xx % cell) - cell / 2) ** 2 + ((yy % cell) - cell / 2) ** 2)
    return _dotf[k]


def paper_bg(W, H):
    if (W, H) not in _paper:
        u = W / 1080; d = dot_field(W, H, 6 * u)
        dots = (np.clip((1.05 * u - d) / max(0.6 * u, 0.5) + 0.5, 0, 1) * 0.12)[..., None]
        _paper[(W, H)] = np.float32([241, 240, 235]) / 255 * (1 - dots) + np.float32([60, 55, 45]) / 255 * dots
    return _paper[(W, H)]


@effect('halftone-paper', 'a cream paper page: you cut out bottom-right with a halftone shadow, your words building at the top with red serif keywords')
def fx_halftone_paper(c, e):
    W, H, u = c.W, c.H, c.W / 1080
    r_in, r_out = ease_out(c.lt / 0.35), ease_out((e.d - c.lt) / 0.25); k = min(r_in, r_out)
    if k <= 0.01: return
    cell = 44 * u; wipe = np.clip((cell * 0.75 * k - dot_field(W, H, cell)) / 1.5 + 0.5, 0, 1)
    fx_, fy_, fw_ = e.med; s = float(e.o.get('scale', 0.62)); xt = W * float(e.o.get('x', 0.68))
    M = np.float32([[s, 0, xt - s * fx_], [0, s, H - s * H]])
    pim = cv2.warpAffine(c.img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    pm = np.clip((cv2.warpAffine(c.m, M, (W, H), flags=cv2.INTER_LINEAR) - 0.25) / 0.5, 0, 1)
    off = max(1, int(22 * u)); sh = np.zeros_like(pm); sh[off:, off:] = pm[:-off, :-off]
    gw = max(1, int(W / (12 * u))); hc = W / gw; gh = max(1, int(H / hc))
    rf = cv2.resize(cv2.resize(sh, (gw, gh), interpolation=cv2.INTER_AREA), (W, H), interpolation=cv2.INTER_NEAREST)
    dots = np.clip((hc * 0.62 * np.sqrt(rf) - dot_field(W, H, hc)) + 0.5, 0, 1) * (rf > 0.02)
    a = (dots * 0.88)[..., None]; scene = paper_bg(W, H) * (1 - a) + np.float32([20, 20, 20]) / 255 * a
    scene = scene * (1 - pm[..., None]) + pim * pm[..., None]
    c.img = c.img * (1 - wipe[..., None]) + scene * wipe[..., None]; c.m = c.m * (1 - wipe) + pm * wipe
    if k > 0.5: c.fx, c.fy, c.fw = s * c.fx + xt - s * fx_, s * c.fy + H - s * H, s * c.fw
    # the words, building at the top
    def blocks():
        if e.o.get('text'):
            ws = str(e.o['text']).split(); t0 = e.start + 0.25
            return cap_blocks([{'w': w, 's': t0 + i * 0.12, 'e': t0 + i * 0.12 + 0.1} for i, w in enumerate(ws)], 'paper', key_set(e), 3, one=True)
        return cap_blocks(e.words, 'paper', key_set(e), 3)
    bl = cached(e, 'blocks', blocks); cur = None
    for j, (b, bs, be) in enumerate(bl):
        if bs <= c.t: cur = j
    if cur is None: return
    lay = cached(e, ('lay', cur), lambda: paper_layout(bl[cur][0], W, u))
    for (g, ink_, x, y, ws, key) in lay:
        q = clamp((c.t - (ws - (0.11 if key else 0.05))) / 0.17)
        if q <= 0: continue
        q2 = ease_out(q); al = (0.35 + 0.65 * q2) * k; yy = y + (1 - q2) * 16 * u
        comp(c, g, x, yy, al * (1 - q2)); comp(c, ink_, x, yy, al * q2)


def paper_layout(block, W, u):
    x0, y0, maxw, lh = 72 * u, 150 * u, W - 144 * u, 104 * u
    items, x, y = [], x0, y0
    fn, fk = font('uim', 82 * u), font('serif', 98 * u); sp = fn.getlength(' ')
    for w in block:
        f = fk if w['k'] else fn; wd = f.getlength(w['w'])
        if x > x0 and x + wd > x0 + maxw: x, y = x0, y + lh
        cols = ((242, 182, 178), (217, 58, 62)) if w['k'] else ((196, 193, 186), (20, 20, 20))
        ims = []
        for col in cols:
            im = Image.new('RGBA', (int(wd + 20 * u), int(lh * 1.5)), (0, 0, 0, 0))
            ImageDraw.Draw(im).text((4 * u, lh * 1.05), w['w'], font=f, fill=col + (255,), anchor='ls'); ims.append(to_np(im))
        items.append((ims[0], ims[1], x - 4 * u, y - lh * 0.2, w['s'], w['k'])); x += wd + sp
    return items


# ---------- Adam Digital additions: captions ----------
STOP = set("a an the and or but so to of in on at for with by from as is are was were be been it its it's this that these those i i'm "
           "i'll i've you you're your we our they their he she his her my me us them do does did not no yes just like can will "
           "would could should has have had than then there here what when where who why how all any some more most very really "
           "also only even about into over up out if".split())
CAP = {'clean': (3, 22, 0.3), 'bold': (1, 40, 0.3), 'pill': (3, 16, 0.3), 'grey': (6, 32, 0.5), 'paper': (8, 46, 0.6)}  # words, characters, pause


def nword(w): return re.sub(r"[^\w%$+#/'-]", '', w).lower().strip("'")


def key_set(e):
    k = e.o.get('keywords')
    return {nword(x) for part in str(k).split('|') for x in part.split() if nword(x)} if k else None


def is_keyword(w, mid, keys):
    n = nword(w)
    if not n: return False
    if keys is not None: return n in keys
    raw = re.sub(r"[^\w%$+#/'-]", '', w)
    return any(ch.isdigit() for ch in raw) or (len(raw) >= 2 and raw.isupper()) or (mid and raw[:1].isupper() and n not in STOP)


ZH_CAP = {'clean': 9, 'bold': 4, 'pill': 11, 'grey': 16, 'paper': 22}  # 中文：每段最多幾個字
ZH_PUNCT = '，。！？、；：,.!?;:…「」『』（）()'


def joinw(ws):
    """Join words with a space only between Latin words: 中文字之間不加空格。"""
    out = ''
    for w in ws:
        w = str(w)
        if out and w and not ((has_cjk(out[-1]) and has_cjk(w[0])) or out[-1] in ZH_PUNCT or w[0] in ZH_PUNCT): out += ' '
        out += w
    return out


def gap_after(a, b):
    """True when a space belongs between two caption words (中英之間留空格，中文字之間不留)."""
    return not (has_cjk(str(a)[-1:]) and has_cjk(str(b)[:1]))


def cap_blocks(words, style, keys, kmax=1, one=False):
    """Group words into caption blocks: [(words, start, end)]; each word gets 'k' = keyword.
    Chinese is grouped by characters (whisper gives one or two characters per 'word')."""
    mw, mc, gap = CAP[style]; blocks, cur, sent = [], [], True
    for w in words:
        t = str(w['w']).strip()
        if not t: continue
        zh = has_cjk(t) or (cur and has_cjk(cur[-1]['w']))
        if zh:
            n = sum(1 if has_cjk(ch) else 0.55 for ch in re.sub(r'\s', '', joinw(x['w'] for x in cur) + t))
            full = n > ZH_CAP[style] if not one else False
        else:
            full = not one and (len(cur) >= mw or len(' '.join(x['w'] for x in cur) + ' ' + t) > mc)
        if cur and (full or (not one and (w['s'] - cur[-1]['e'] > gap or cur[-1]['w'][-1] in '.,!?;:，。！？；：、'))):
            blocks.append(cur); cur = []
        cur.append(dict(w, w=t, mid=not sent)); sent = t[-1] in '.!?。！？'
    if cur: blocks.append(cur)
    out = []
    for i, b in enumerate(blocks):
        n = 0
        for x in b: x['k'] = n < kmax and is_keyword(x['w'], x['mid'], keys); n += x['k']
        nxt = blocks[i + 1][0]['s'] if i + 1 < len(blocks) else None
        out.append((b, b[0]['s'] - 0.04, nxt - 0.04 if nxt is not None and nxt - b[-1]['e'] < 0.7 else b[-1]['e'] + 0.3))
    return out


def soft_shadow(im, blur, alpha, dy=0):
    a = im.split()[3].point(lambda v: v * alpha // 255); sh = Image.new('RGBA', im.size, (0, 0, 0, 255)); sh.putalpha(a)
    out = Image.new('RGBA', im.size, (0, 0, 0, 0)); out.paste(sh, (0, dy), sh)
    return out.filter(ImageFilter.GaussianBlur(blur))


def cap_word_imgs(block, u, style):
    """One image per word on a shared baseline, plus each word's x offset and the line width."""
    if style == 'clean': fs = lambda k: font('didoneib', 84 * u * fit) if k else font('montb', 62 * u * fit); space, maxw = 22 * u, 960 * u
    else: fs = lambda k: font('popx', (96 if k else 84) * u * fit); space, maxw = 26 * u, 960 * u
    fit = 1.0
    txt = [w['w'].rstrip('.,;:，。、；：！？') or w['w'] for w in block]  # aitjb: keep brand names as written (Claude Code, not claude code)
    sp = [space if i + 1 < len(txt) and gap_after(txt[i], txt[i + 1]) else (space * 0.15 if i + 1 < len(txt) else 0) for i in range(len(txt))]
    width = lambda: sum(fs(w['k']).getlength(t) for w, t in zip(block, txt)) + sum(sp[:-1])
    total = width()
    if total > maxw: fit = maxw / total * 0.98; total = width()
    asc = max(fs(k).getmetrics()[0] for k in (False, True)); desc = max(fs(k).getmetrics()[1] for k in (False, True))
    pad = int(40 * u); hgt = asc + desc + 2 * pad; out, x = [], 0.0
    for w, t in zip(block, txt):
        f = fs(w['k']); wd = f.getlength(t); im = Image.new('RGBA', (int(wd) + 2 * pad, hgt), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        if style == 'clean':
            d.text((pad, pad + asc), t, font=f, fill=((255, 226, 122) if w['k'] else (255, 255, 255)) + (255,), anchor='ls')
            im = Image.alpha_composite(Image.alpha_composite(soft_shadow(im, 28 * u, 153), soft_shadow(im, 8 * u, 128)), im)
        else:
            if w['k']: d.text((pad + 4 * u, pad + asc + 6 * u), t, font=f, fill=(17, 17, 20, 255), anchor='ls')
            d.text((pad, pad + asc), t, font=f, fill=((255, 211, 26) if w['k'] else (255, 255, 255)) + (255,), anchor='ls')
            im = Image.alpha_composite(soft_shadow(im, 14 * u, 140, int(4 * u)), im)
        out.append((to_np(im) if style == 'clean' else im, x - pad, w['s'])); x += wd + sp[len(out) - 1]
    return out, total, hgt


def cap_pill(text, u, style):
    if style == 'pill': f, bg, r, h, padx = font('ui7', 64 * u), (22, 22, 28, 158), 20 * u, 88 * u, 22 * u
    else: f, bg, r, h, padx = font('ui7', 46 * u), (58, 58, 62, 225), 14 * u, None, 20 * u
    while f.getlength(text) > 900 * u and f.size > 12: f = font('ui7', int(f.size * 0.92))
    asc, desc = f.getmetrics(); h = h or asc + desc + 14 * u; w = f.getlength(text) + 2 * padx; pad = int(16 * u)
    im = Image.new('RGBA', (int(w) + 2 * pad, int(h) + 2 * pad), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([pad, pad, pad + w, pad + h], r, fill=bg)
    txt = Image.new('RGBA', im.size, (0, 0, 0, 0)); ImageDraw.Draw(txt).text((pad + w / 2, pad + h / 2), text, font=f, fill=(255, 255, 255, 255), anchor='mm')
    im = Image.alpha_composite(im, Image.alpha_composite(soft_shadow(txt, 5 * u, 110, int(2 * u)), txt))
    return Image.alpha_composite(soft_shadow(im, 6 * u, 90, int(3 * u)), im)


CAP_HIDE = {'press-front', 'banknote', 'paper-tear', 'letter-dive', 'impact-frame', 'cover-story', 'split-graph', 'phone-mockup', 'halftone-paper', 'checklist', 'liquid-glass-graph', 'tier-list', 'messages', 'tape-label', 'phone-fan', 'broll-split',
            'split-headline', 'reel-frame', 'place-in-grid', 'headline-box', 'cover-star', 'red-collage', 'over-the-shoulder-zoom',
            'glass-widgets', 'timeline', 'profile-wall', 'headline-wall', 'pastel-word', 'check-pills'}  # these own the lower screen


@effect('captions', 'word-by-word captions in Adam Digital styles: clean (default), bold, pill or grey')
def fx_captions(c, e):
    hide = cached(e, 'hide', lambda: [tuple(float(x) for x in h.split('-')[:2]) for h in str(e.o.get('hide', '')).split('|') if '-' in h])
    if c.act & CAP_HIDE or any(a <= c.t < b for a, b in hide): return
    style = e.o.get('style', 'clean'); style = style if style in ('clean', 'bold', 'pill', 'grey') else 'clean'; u = c.W / 1080
    bl = cached(e, 'blocks', lambda: cap_blocks(e.words, style, key_set(e), 0 if style == 'grey' else 1))
    j = e.state.get('j', 0)
    while j + 1 < len(bl) and bl[j + 1][1] <= c.t: j += 1
    e.state['j'] = j
    if not bl or not (bl[j][1] <= c.t < bl[j][2]): return
    b = bl[j][0]
    fx_, fy_, fw_ = e.med; chin = fy_ + fw_ * 0.75
    if e.o.get('y') is not None: yc = float(e.o['y']) * c.H
    elif style == 'clean': yc = clamp(fy_ + fw_ * 1.5, c.H * 0.58, c.H * 0.8)
    else: yc = c.H * {'bold': 0.77, 'pill': 0.766, 'grey': 0.693}[style]
    if style in ('clean', 'bold'):
        words, total, hgt = cached(e, ('w', j), lambda: cap_word_imgs(b, u, style))
        yc = max(yc, chin + hgt * 0.35) if e.o.get('y') is None else yc
        if c.cardbot: yc = c.cardbot + hgt * 0.42
        for n, (im, xo, ws) in enumerate(words):
            dt = c.t - ws + 0.06
            if dt < 0 and n: continue
            al = 1.0 if n == 0 else clamp(dt / 0.08)
            if style == 'clean':
                p = 1.0 if n == 0 else ease_back(dt / 0.18); comp(c, im, c.W / 2 - total / 2 + xo, yc - hgt / 2 + (1 - p) * 14 * u, al)
            else:
                p = ease_back(max(dt, 0) / 0.12); place(c, im, c.W / 2 - total / 2 + xo + im.width / 2, yc, 0.86 + 0.14 * p, 0, max(al, 0.6))
    else:
        im = cached(e, ('p', j), lambda: cap_pill(joinw(w['w'] for w in b).rstrip('.,;:，。、；：！？') if style == 'pill' or has_cjk(joinw(w['w'] for w in b)) else joinw(w['w'] for w in b), u, style))
        yc = max(yc, chin + im.height * 0.5) if e.o.get('y') is None else yc
        if c.cardbot: yc = c.cardbot + im.height * 0.55
        sc = 0.9 + 0.1 * ease_out((c.t - bl[j][1]) / 0.09) if style == 'pill' else 1.0
        place(c, im, c.W / 2, yc, sc)


# ---------- aitjb pack: 21 new effects by @ai_tjb (Olivia), 繁體中文 first ----------
# Everything below is drawn in code: no images or clips from anyone else are bundled.

def cut_rgba(c, img=None, m=None):
    """The person as an RGBA float layer (the room is transparent)."""
    img = c.img if img is None else img; m = c.m if m is None else m
    return np.concatenate([img, m[..., None]], -1).astype(np.float32)


def warp_rgba(L, M, W, H):
    return cv2.warpAffine(L, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))


def over(dst, L, alpha=1.0):
    a = L[..., 3:4] * alpha
    return dst * (1 - a) + L[..., :3] * a


def person_box(c, thr=0.5):
    ys, xs = np.nonzero(c.m > thr)
    if len(xs) < 50: return (c.W * 0.2, c.H * 0.2, c.W * 0.8, c.H)
    return (float(np.percentile(xs, 1)), float(np.percentile(ys, 0.5)), float(np.percentile(xs, 99)), float(ys.max()))


def clean_plate(c, e):
    """The room without you. With plate=<image of the same shot with nobody in it> (e.g. the empty chair), that image is used;
    otherwise it is filled in once from the first frame of the effect (soft, so it reads as an empty set)."""
    pl = e.o.get('plate')
    if pl and os.path.exists(str(pl)):
        return cached(e, 'plate', lambda: np.asarray(Image.open(str(pl)).convert('RGB').resize((c.W, c.H), Image.LANCZOS), np.float32) / 255)
    def mk():
        # fill each row of the hole from the wall on its left and right (smooth, so no outline of you is left behind),
        # then blend it in with a wide soft edge
        s = 4; w, h = c.W // s, c.H // s
        small = cv2.resize(c.img, (w, h), interpolation=cv2.INTER_AREA)
        hole = cv2.dilate((cv2.resize(c.m, (w, h)) > 0.05).astype(np.uint8), np.ones((13, 13), np.uint8)).astype(bool)
        fill = small.copy(); xs = np.arange(w, dtype=np.float32)
        for y in range(h):
            row = hole[y]
            if not row.any(): continue
            good = ~row
            if good.sum() < 2: fill[y] = fill[y - 1] if y else small[y]; continue
            for ch in range(3): fill[y, row, ch] = np.interp(xs[row], xs[good], small[y, good, ch])
        fill = cv2.GaussianBlur(fill, (0, 0), 2.5)
        fill = small * (~hole[..., None]) + cv2.GaussianBlur(fill, (0, 0), 1.5) * hole[..., None]
        big = cv2.resize(fill.astype(np.float32), (c.W, c.H), interpolation=cv2.INTER_CUBIC)
        soft = cv2.GaussianBlur(cv2.resize(hole.astype(np.float32), (c.W, c.H)), (0, 0), 14)[..., None]
        return c.img * (1 - soft) + big * soft
    return cached(e, 'plate', mk)


def opt_lines(e, key, default):
    v = e.o.get(key, default)
    return [s for s in str(v).split('|')] if v is not None else []


def stop_t(c, fps=8):
    """Time snapped to a stop-motion beat (8 frames a second)."""
    return math.floor(c.lt * fps) / fps


def glyph_atlas(chars, size, kind='mono'):
    f = font(kind, size); cw = int(f.getlength('M') + 1); ch = int(size * 1.25)
    out = np.zeros((len(chars), ch, cw), np.float32)
    for i, s in enumerate(chars):
        im = Image.new('L', (cw, ch), 0); ImageDraw.Draw(im).text((cw / 2, ch / 2), s, font=f, fill=255, anchor='mm')
        out[i] = np.asarray(im, np.float32) / 255
    return out


def halftone(gray, cell, ink_scale=1.0):
    """Newspaper halftone: one dot per cell, bigger where it's darker. gray is 0..1 (1 = white)."""
    H, W = gray.shape; gh, gw = H // cell, W // cell
    small = cv2.resize(gray[:gh * cell, :gw * cell], (gw, gh), interpolation=cv2.INTER_AREA)
    lv = 12; yy, xx = np.mgrid[0:cell, 0:cell].astype(np.float32) - (cell - 1) / 2; rr = np.sqrt(xx * xx + yy * yy)
    disks = np.stack([np.clip((cell * 0.72 * math.sqrt(k / (lv - 1)) * ink_scale - rr) + 0.5, 0, 1) for k in range(lv)])
    idx = np.clip(((1 - small) * (lv - 1) + 0.5).astype(int), 0, lv - 1)
    ink = disks[idx].transpose(0, 2, 1, 3).reshape(gh * cell, gw * cell)
    out = np.zeros((H, W), np.float32); out[:gh * cell, :gw * cell] = ink
    return out


ZH_FILLER = ('人工智慧正在改變每一個產業的工作方式，從寫作、設計到影片剪輯，創作者只要一句話就能完成過去需要一整天的工作。'
             '專家指出，真正的差距不在工具，而在於是否懂得把工具接進自己的流程。本報記者實地走訪多位創作者，'
             '發現他們每天花在剪輯上的時間平均減少了七成，省下的時間全都拿去想內容。')


def news_page(W, H, head, sub, photo_box, date):
    """A 繁中 newspaper front page as a PIL image, with an empty photo box for the live video."""
    u = W / 1080; ink = (24, 22, 20)
    pg = Image.fromarray((paper_bg(W, H) * 255).astype(np.uint8)).convert('RGBA')
    pg = Image.alpha_composite(pg, Image.new('RGBA', (W, H), (236, 228, 210, 120)))
    d = ImageDraw.Draw(pg); mx = int(46 * u)
    mast = fit_text('AI 日報', W - 2 * mx, 'tcserif', int(210 * u), fill=ink)
    pg.alpha_composite(mast, ((W - mast.width) // 2, int(10 * u)))
    y = int(10 * u) + mast.height - int(24 * u)
    d.line([(mx, y), (W - mx, y)], fill=ink + (255,), width=max(2, int(5 * u)))
    d.text((mx, y + 10 * u), date, font=font('tcm', 26 * u), fill=ink + (255,))
    d.text((W - mx, y + 10 * u), '第 1 版 · 每份 NT$10', font=font('tcm', 26 * u), fill=ink + (255,), anchor='ra')
    y += int(50 * u); d.line([(mx, y), (W - mx, y)], fill=ink + (255,), width=max(1, int(2 * u)))
    hl = fit_text(head, W - 2 * mx, 'tcserif', int(170 * u), fill=ink)
    pg.alpha_composite(hl, ((W - hl.width) // 2, y + int(6 * u))); y += hl.height
    if sub:
        sb = fit_text(sub, W - 2 * mx, 'tcm', int(52 * u), fill=ink); pg.alpha_composite(sb, ((W - sb.width) // 2, y - int(14 * u))); y += sb.height
    x0, y0, x1, y1 = photo_box
    d.rectangle([x0 - 3 * u, y0 - 3 * u, x1 + 3 * u, y1 + 3 * u], outline=ink + (255,), width=max(1, int(3 * u)))
    f = font('tcserif', 30 * u); lh = int(46 * u); col_w = (W - 2 * mx - 2 * int(28 * u)) / 3; txt = ZH_FILLER * 6; k = 0
    for ci in range(3):
        cx0 = mx + ci * (col_w + 28 * u); yy = y1 + int(56 * u)
        if ci == 0: d.text((cx0, y1 + 10 * u), '▲ 本報資料照片', font=font('tcm', 24 * u), fill=(90, 84, 76, 255))
        while yy < H - mx:
            n = max(1, int(col_w / (30 * u)))
            d.text((cx0, yy), txt[k:k + n], font=f, fill=ink + (235,)); k += n; yy += lh
        if ci < 2: d.line([(cx0 + col_w + 14 * u, y1 + 50 * u), (cx0 + col_w + 14 * u, H - mx)], fill=ink + (160,), width=1)
    return pg


def news_box(c, u):
    """The photo box on the front page, kept inside the frame for vertical and landscape video."""
    h = min((c.W - 92 * u) * 0.78, c.H * 0.5); w = min(c.W - 92 * u, h / 0.78)
    x0 = int((c.W - w) / 2); y0 = int(c.H * 0.36)
    return (x0, y0, int(x0 + w), int(min(c.H - 4, y0 + h)))


def roc_today():
    import datetime as _dt
    t = _dt.date.today(); wd = '一二三四五六日'[t.weekday()]
    return f'中華民國 {t.year - 1911} 年 {t.month} 月 {t.day} 日 星期{wd}'


def news_photo(c, x0, y0, x1, y1, cell=None):
    """The live video inside a newspaper photo box, black and white with a halftone screen."""
    w, h = int(x1 - x0), int(y1 - y0)
    s = max(w / c.W, h / c.H); src = cv2.resize(c.img, (int(c.W * s) + 1, int(c.H * s) + 1), interpolation=cv2.INTER_AREA)
    cy = int(clamp(c.fy * s - h * 0.38, 0, src.shape[0] - h)); cx = int(clamp(c.fx * s - w / 2, 0, src.shape[1] - w))
    crop = src[cy:cy + h, cx:cx + w]
    g = np.clip((crop @ np.float32([0.299, 0.587, 0.114]) - 0.5) * 1.35 + 0.52, 0, 1)
    ink = halftone(g, cell or max(4, int(c.W / 150)))
    paper = np.float32([236, 230, 214]) / 255
    return paper * (1 - ink[..., None] * 0.92) + np.float32([20, 18, 16]) / 255 * ink[..., None] * 0.92


LIME, PINK = (205, 245, 28), (255, 46, 166)  # @ai_tjb 品牌色：萊姆綠 #CDF51C × 電光粉 #FF2EA6


# 1 ---------------------------------------------------------------- vol.15
@effect('split-graph', '彈跳長條圖：螢光色長條圖在你頭頂上方彈跳長高')
def fx_split_graph(c, e):
    u = c.W / 1080; al = fade(c, e)
    labels = opt_lines(e, 'text', '1月|2月|3月|4月|5月'); vals = [float(v) for v in opt_lines(e, 'to', '18|32|27|56|88')][:len(labels)]
    cols = [LIME, PINK, (255, 255, 255), LIME, PINK, (255, 255, 255)]
    n = len(vals); top = head_top(e); base = clamp(top + c.fw * 0.35, c.H * 0.3, c.H * 0.55); ch = base - c.H * 0.11
    vmax = max(vals) or 1; bw = c.W * 0.8 / n
    dark = clamp(c.lt / 0.25) * 0.35 * al; c.img = c.img * (1 - dark * (1 - c.m[..., None]))
    lay = Image.new('RGBA', (c.W, c.H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); glow = Image.new('RGBA', (c.W, c.H), (0, 0, 0, 0)); g = ImageDraw.Draw(glow)
    for i, v in enumerate(vals):
        k = ease_back((c.lt - 0.12 - 0.11 * i) / 0.45) if c.lt > 0.12 + 0.11 * i else 0
        bounce = 1 + 0.03 * math.sin((c.lt - 0.6 - 0.11 * i) * 9) * math.exp(-max(0, c.lt - 0.6 - 0.11 * i) * 4) if k >= 1 else 1
        h = ch * v / vmax * k * bounce; x0 = c.W * 0.1 + i * bw + bw * 0.16; x1 = x0 + bw * 0.68; col = cols[i % len(cols)]
        if h > 2:
            d.rounded_rectangle([x0, base - h, x1, base], int(bw * 0.12), fill=col + (255,))
            g.rounded_rectangle([x0, base - h, x1, base], int(bw * 0.12), fill=col + (255,))
            num = text_img(f'{v * min(1, k):.0f}', 44 * u, 'uib', col, shadow=4)
            lay.alpha_composite(num, (int((x0 + x1) / 2 - num.width / 2), int(base - h - num.height + 8 * u)))
        lb = text_img(labels[i], 34 * u, 'uim', (255, 255, 255), shadow=4)
        lay.alpha_composite(lb, (int((x0 + x1) / 2 - lb.width / 2), int(base + 4 * u)))
    d.line([(c.W * 0.08, base), (c.W * 0.92, base)], fill=(255, 255, 255, 200), width=max(2, int(3 * u)))
    glow = glow.filter(ImageFilter.GaussianBlur(26 * u))
    comp(c, glow, 0, 0, 0.9 * al, behind=True); comp(c, lay, 0, 0, al, behind=True)
    t = e.o.get('title')
    if t: place(c, cached(e, 'tt', lambda: text_img(t, 54 * u, 'uib', (255, 255, 255), shadow=6)), c.W / 2, c.H * 0.075, alpha=al * clamp(c.lt / 0.2), behind=True)


# 2 ---------------------------------------------------------------- vol.10
def spark(d, x, y, r, col):
    """A small orange spark (a generic AI mark, drawn as lines)."""
    for a in range(8):
        t = a * math.pi / 4; d.line([(x, y), (x + r * math.cos(t), y + r * math.sin(t))], fill=col, width=max(2, int(r / 4)))


def chat_ui(c, e, w, h, typed, attach_k, att):
    """A light chat app panel (generic, not a copy of any real app)."""
    u = c.W / 1080; im = Image.new('RGBA', (int(w), int(h)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], int(46 * u), fill=(250, 249, 245, 255))
    d.text((w / 2, 70 * u), e.o.get('title', 'Claude'), font=font('uib', 40 * u), fill=(30, 30, 30, 255), anchor='mm')
    for j in range(3): d.line([(46 * u, (58 + j * 12) * u), (78 * u, (58 + j * 12) * u)], fill=(90, 90, 90, 255), width=max(2, int(4 * u)))
    bub = e.o.get('ask', '幫我把這支影片加上特效')
    bf = font('uim', 36 * u); bwid = bf.getlength(bub) + 60 * u
    d.rounded_rectangle([w - 50 * u - bwid, 150 * u, w - 50 * u, 240 * u], int(30 * u), fill=(234, 231, 222, 255))
    d.text((w - 50 * u - bwid / 2, 195 * u), bub, font=bf, fill=(30, 30, 30, 255), anchor='mm')
    spark(d, 78 * u, 300 * u, 20 * u, (217, 119, 87, 255))
    d.text((115 * u, 300 * u), e.o.get('reply', '好的，馬上處理。'), font=font('uim', 36 * u), fill=(40, 40, 40, 255), anchor='lm')
    bx0, by0, bx1, by1 = 40 * u, h - 230 * u, w - 40 * u, h - 40 * u
    d.rounded_rectangle([bx0, by0, bx1, by1], int(36 * u), fill=(255, 255, 255, 255), outline=(220, 218, 210, 255), width=max(2, int(2 * u)))
    tx = bx0 + 40 * u
    if attach_k > 0.99 and att is not None:
        tx = bx0 + 40 * u + att.width + 20 * u
    d.text((tx, by0 + 62 * u), typed or '回覆 Claude…', font=font('uim', 36 * u), fill=(40, 40, 40, 255) if typed else (160, 160, 160, 255), anchor='lm')
    d.ellipse([bx1 - 100 * u, by1 - 100 * u, bx1 - 30 * u, by1 - 30 * u], fill=(217, 119, 87, 255))
    d.text((bx1 - 65 * u, by1 - 66 * u), '↑', font=font('uib', 40 * u), fill=(255, 255, 255, 255), anchor='mm')
    return im, (bx0 + 40 * u, by0 + 30 * u)


@effect('ui-world', '聊天畫面降落：白色聊天視窗從上方降下，一張圖飛進輸入框')
def fx_ui_world(c, e):
    u = c.W / 1080; al = fade(c, e); k = ease_out(c.lt / 0.45)
    w, h = c.W * 0.9, c.H * 0.44  # it sits behind you, so your head can cover the bottom of it
    att = cached(e, 'att', lambda: card((e.cards or [Image.new('RGB', (9, 16), (90, 90, 90))])[0], int(110 * u)))
    ak = ease_inout((c.lt - 0.6) / 0.45)
    txt = e.o.get('text', '/effects 全部套上'); n = int(clamp((c.lt - 1.1) / 0.8) * len(txt))
    panel, slot = chat_ui(c, e, w, h, txt[:n], ak, att)
    if ak >= 0.99: panel.alpha_composite(att, (int(slot[0] - 10 * u), int(slot[1] - 30 * u)))
    py = -h + (h + c.H * 0.03) * k
    sp = int(30 * u) * 2 + int(16 * u)
    comp(c, shadowed(panel, int(30 * u), int(16 * u), 110), (c.W - w) / 2 - sp, py - sp, al, behind=True)
    if 0 < ak < 0.99:
        sx, sy = c.fx + c.fw * 1.6, c.fy + c.fw * 1.8; tx_, ty_ = (c.W - w) / 2 + slot[0] + att.width / 2, py + slot[1] + att.height / 2
        x = sx + (tx_ - sx) * ak; y = sy + (ty_ - sy) * ak - math.sin(ak * math.pi) * c.H * 0.08
        place(c, att, x, y, 2.4 - 1.4 * ak, (1 - ak) * 25, al)


# 3
@effect('phone-mockup', '手機模型：一支大手機從側邊飛進來，螢幕上的按鈕被按下')
def fx_phone_mockup(c, e):
    u = c.W / 1080; al = fade(c, e); k = ease_out(c.lt / 0.5)
    side = -1 if c.fx > c.W * 0.5 else 1; pw = c.W * 0.38; ph = pw * 2.05
    btn = e.o.get('text', '開始剪輯'); at = float(e.o.get('at', 1.1))
    pressed = c.lt >= at; pk = ease_back((c.lt - at) / 0.25) if pressed else 0
    def phone(pr):
        im = Image.new('RGBA', (int(pw), int(ph)), (0, 0, 0, 0)); d = ImageDraw.Draw(im); r = int(pw * 0.14)
        d.rounded_rectangle([0, 0, pw - 1, ph - 1], r, fill=(18, 18, 20, 255))
        d.rounded_rectangle([pw * 0.035, pw * 0.035, pw * 0.965, ph - pw * 0.035], int(r * 0.85), fill=(246, 244, 239, 255))
        d.rounded_rectangle([pw * 0.36, pw * 0.07, pw * 0.64, pw * 0.14], int(pw * 0.04), fill=(18, 18, 20, 255))
        d.text((pw / 2, ph * 0.2), e.o.get('title', 'AI 剪輯'), font=font('uib', pw * 0.11), fill=(25, 25, 25, 255), anchor='mm')
        d.text((pw / 2, ph * 0.29), e.o.get('sub', '一鍵加特效'), font=font('uim', pw * 0.065), fill=(120, 120, 120, 255), anchor='mm')
        for j in range(3):
            y = ph * (0.38 + 0.09 * j); d.rounded_rectangle([pw * 0.12, y, pw * 0.88, y + ph * 0.065], int(pw * 0.04), fill=(232, 229, 220, 255))
        bw_, bh_ = pw * 0.7 * (0.94 if pr else 1), ph * 0.085 * (0.94 if pr else 1); by = ph * 0.78
        col = (52, 199, 89) if pr else (217, 119, 87)
        d.rounded_rectangle([pw / 2 - bw_ / 2, by - bh_ / 2, pw / 2 + bw_ / 2, by + bh_ / 2], int(bh_ / 2), fill=col + (255,))
        d.text((pw / 2, by), ('✓ ' if pr else '') + btn, font=font('uib', pw * 0.07), fill=(255, 255, 255, 255), anchor='mm')
        return shadowed(im, int(26 * u), int(18 * u), 140)
    ph_im = cached(e, ('p', pressed and pk > 0.5), lambda: phone(pressed and pk > 0.5))
    tx = c.fx + side * c.fw * 2.0; tx = clamp(tx, pw * 0.55, c.W - pw * 0.55); ty = clamp(c.fy + c.fw * 1.2, ph * 0.5, c.H - ph * 0.45)
    x = tx + side * (1 - k) * c.W * 0.9; rot = -side * 8 * (1 - k) + side * 4
    place(c, ph_im, x, ty, 1.0, rot, al, guard=True)
    cur = cached(e, 'cur', lambda: cursor(64 * u))
    ck = ease_inout((c.lt - 0.55) / 0.5)
    if c.lt > 0.55:
        bx, by = tx, ty - ph * 0.5 + ph * 0.78
        cx, cy = bx + c.W * 0.3 * (1 - ck), by + c.H * 0.15 * (1 - ck)
        place(c, cur, cx + cur.width * 0.4, cy + cur.height * 0.4, 0.9 if pressed and c.lt - at < 0.15 else 1.0, 0, al)


# 4
@effect('glass-type', '透明玻璃字：一排玻璃立體字站在你身後，牆面透過字看得到，一道光劃過')
def fx_glass_type(c, e):
    u = c.W / 1080; al = fade(c, e); k = ease_out(c.lt / 0.5)
    txt = e.o.get('text', 'AI 創作')
    def mk():
        im = fit_text(txt, c.W * 0.94, 'tc' if has_cjk(txt) else 'bold', int(c.W * 0.4), fill=(255, 255, 255))
        a = np.asarray(im.split()[3], np.float32) / 255
        return a
    a = cached(e, 'a', mk); h, w = a.shape
    cx = c.W / 2; cy = clamp(head_top(e) + c.fw * 0.1, h * 0.55, c.H * 0.45); x0, y0 = int(cx - w / 2), int(cy - h / 2 + (1 - k) * c.H * 0.08)
    xs = np.clip(np.arange(x0, x0 + w), 0, c.W - 1); ys = np.clip(np.arange(y0, y0 + h), 0, c.H - 1)
    bg = c.img[np.ix_(ys, xs)]
    blur = cv2.GaussianBlur(a, (0, 0), 9 * u); gy, gx = np.gradient(blur)
    gy = cv2.GaussianBlur(gy, (0, 0), 2); gx = cv2.GaussianBlur(gx, (0, 0), 2)
    off = 260 * u; mx_, my_ = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    ref = cv2.remap(np.ascontiguousarray(bg), mx_ + gx * off, my_ + gy * off, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    ref = cv2.GaussianBlur(ref, (0, 0), 1.5) * 1.06 + 0.04
    light = np.clip(-(gx * 0.6 + gy * 0.8) * 60, 0, 1)[..., None]
    edge = np.clip(np.sqrt(gx ** 2 + gy ** 2) * 25, 0, 1)[..., None]
    sweep = (c.lt - 0.5) / 0.7; band = np.exp(-((mx_ + my_ * 0.5) / (w + h * 0.5) - sweep) ** 2 / 0.004)[..., None] if 0 < sweep < 1.3 else 0
    glass_px = np.clip(ref + light * 0.45 + edge * 0.18 + band * 0.55, 0, 1)
    L = np.concatenate([glass_px, (a * (0.97))[..., None]], -1).astype(np.float32)
    sh = np.zeros((h, w, 4), np.float32); sh[..., 3] = cv2.GaussianBlur(a, (0, 0), 18 * u) * 0.35
    comp(c, sh, x0 + 14 * u, y0 + 30 * u, al * k, behind=True); comp(c, L, x0, y0, al * k, behind=True)


# 5
@effect('chart-grow', '發光折線：一條發光的線往右上長，最後跳出大數字')
def fx_chart_grow(c, e):
    u = c.W / 1080; al = fade(c, e); col = rgb(e.o.get('color'), LIME)
    dark = clamp(c.lt / 0.25) * 0.5 * al; m = c.m[..., None]; c.img = c.img * (1 - dark * (1 - m))
    x0, x1 = c.W * 0.07, c.W * 0.93; yb = clamp(head_top(e) + c.fw * 0.4, c.H * 0.32, c.H * 0.5); yt = c.H * 0.1
    rnd = random.Random(3); n = 9; pts = []
    for i in range(n):
        f = i / (n - 1); y = yb - (yb - yt) * (f ** 1.6) + (rnd.uniform(-1, 1) * (yb - yt) * 0.07 if 0 < i < n - 1 else 0)
        pts.append((x0 + (x1 - x0) * f, y))
    dense = []
    for i in range(n - 1):
        for s in np.linspace(0, 1, 16, endpoint=False): dense.append((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * s, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * s))
    dense.append(pts[-1]); p = ease_inout((c.lt - 0.15) / 1.0); m_ = max(2, int(len(dense) * p))
    lay = Image.new('RGBA', (c.W, c.H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for gx in range(5): d.line([(x0, yt + (yb - yt) * gx / 4), (x1, yt + (yb - yt) * gx / 4)], fill=(255, 255, 255, 40), width=1)
    area = dense[:m_] + [(dense[m_ - 1][0], yb), (x0, yb)]
    fill = Image.new('RGBA', (c.W, c.H), (0, 0, 0, 0)); ImageDraw.Draw(fill).polygon(area, fill=col + (70,))
    d.line(dense[:m_], fill=col + (255,), width=max(4, int(9 * u)), joint='curve')
    glow = lay.filter(ImageFilter.GaussianBlur(22 * u))
    comp(c, fill, 0, 0, al, behind=True); comp(c, glow, 0, 0, al, behind=True); comp(c, glow, 0, 0, al * 0.7, behind=True); comp(c, lay, 0, 0, al, behind=True)
    hx, hy = dense[m_ - 1]; dot = Image.new('RGBA', (int(40 * u),) * 2, (0, 0, 0, 0)); ImageDraw.Draw(dot).ellipse([0, 0, 40 * u - 1, 40 * u - 1], fill=(255, 255, 255, 255))
    place(c, dot, hx, hy, 1, 0, al, behind=True)
    to = str(e.o.get('to', '+320%')); pre = re.match(r'\s*([^\d.]*)', to).group(1); num, suf, dec = split_num(to[len(pre):]); kk = ease_out((c.lt - 0.15) / 1.0)
    val = f'{pre}{num * kk:,.{dec}f}{suf}'
    if c.lt > 0.9:
        b = ease_back((c.lt - 0.9) / 0.35)
        big = text_img(val, 150 * u, 'uib', (255, 255, 255), glow=(col, 20 * u), shadow=6)
        place(c, big, clamp(x1 - big.width * 0.45, big.width / 2, c.W - big.width / 2), yt + big.height * 0.35, 0.6 + 0.4 * b, 0, al)
    lab = e.o.get('text')
    if lab:
        li = cached(e, 'lab', lambda: fit_text(lab, c.W * 0.8, 'uim', int(44 * u), fill=(255, 255, 255), shadow=4))
        place(c, li, x0 + li.width / 2, yb + 40 * u, alpha=al, behind=True)


# 6
def torn_paper(w, h, color, seed, edge=0.04):
    rnd = random.Random(seed); im = Image.new('RGBA', (int(w), int(h)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    e_ = max(3, int(min(w, h) * edge)); pts = []
    for x in range(0, int(w), 8): pts.append((x, rnd.randint(0, e_)))
    for y in range(0, int(h), 8): pts.append((w - rnd.randint(0, e_), y))
    for x in range(int(w), 0, -8): pts.append((x, h - rnd.randint(0, e_)))
    for y in range(int(h), 0, -8): pts.append((rnd.randint(0, e_), y))
    d.polygon(pts, fill=tuple(color) + (255,))
    a = np.asarray(im, np.float32); noise = np.random.default_rng(seed).normal(0, 7, a.shape[:2])[..., None]
    a[..., :3] = np.clip(a[..., :3] + noise, 0, 255)
    return Image.fromarray(a.astype(np.uint8))


def sticker(L, rad):
    """A white die-cut sticker border around a cut-out layer."""
    a = (L[..., 3] > 0.5).astype(np.uint8); k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * rad + 1, 2 * rad + 1))
    border = cv2.dilate(a, k).astype(np.float32); border = cv2.GaussianBlur(border, (0, 0), 1.2)
    out = np.zeros_like(L); out[..., :3] = 1.0; out[..., 3] = border
    out[..., :3] = out[..., :3] * (1 - L[..., 3:4]) + L[..., :3] * L[..., 3:4]
    return out


def ransom(text, size, seed):
    """Cut-out letters: each one on its own scrap of paper, mixed fonts and colours."""
    rnd = random.Random(seed); pieces = []
    pal = [((250, 250, 245), (20, 20, 20)), ((20, 20, 20), (250, 250, 245)), ((230, 40, 40), (255, 255, 255)),
           ((255, 214, 10), (20, 20, 20)), ((30, 80, 200), (255, 255, 255)), ((240, 230, 210), (200, 30, 30))]
    kinds = ['tc', 'tcserif', 'tchand'] if has_cjk(text) else ['bold', 'serif', 'anton', 'didoneb', 'mono']
    for ch in text:
        if ch == ' ': pieces.append(None); continue
        bg, fg = rnd.choice(pal); s = size * rnd.uniform(0.85, 1.15)
        g = text_img(ch, s, rnd.choice(kinds), fg)
        p = torn_paper(g.width * 1.05, g.height * 0.95, bg, rnd.randint(0, 9999), 0.06); p.alpha_composite(g, (int((p.width - g.width) / 2), int((p.height - g.height) / 2)))
        pieces.append(shadowed(p.rotate(rnd.uniform(-9, 9), Image.BICUBIC, expand=True), 6, 4, 120))
    W = sum((p.width * 0.92 if p else size * 0.4) for p in pieces); H = max((p.height for p in pieces if p), default=10)
    out = Image.new('RGBA', (int(W) + 20, int(H * 1.25)), (0, 0, 0, 0)); x = 10
    for p in pieces:
        if p is None: x += size * 0.4; continue
        out.alpha_composite(p, (int(x), int(rnd.uniform(0, H * 0.2)))); x += p.width * 0.92
    return out


@effect('paper-cut', '剪紙拼貼：紙片層層疊在一起，用定格動畫的節奏動起來')
def fx_paper_cut(c, e):
    u = c.W / 1080; al = fade(c, e); st = stop_t(c); jit = random.Random(int(st * 8) + 1)
    def bg():
        base = torn_paper(c.W, c.H, (233, 224, 205), 11, 0.0)
        d = ImageDraw.Draw(base); rnd = random.Random(5)
        for j in range(60):  # pen hatching scribbles
            x = rnd.uniform(0, c.W); y = rnd.uniform(c.H * 0.2, c.H * 0.95); L = rnd.uniform(40, 140) * u
            d.line([(x, y), (x + L, y - L * 0.2)], fill=(40, 70, 170, 120), width=max(2, int(4 * u)))
        return to_np(base)[..., :3]
    k = ramp(c, e, 0.12, 0); plate = cached(e, 'bg', bg)
    keep = c.img.copy()
    c.img = c.img * (1 - k) + plate * k
    scraps = cached(e, 'scr', lambda: [(torn_paper(c.W * w_, c.H * h_, col, j * 7), x_, y_, r_) for j, (w_, h_, col, x_, y_, r_) in enumerate([
        (0.62, 0.12, (255, 214, 10), 0.72, 0.62, -6), (0.5, 0.1, (238, 70, 60), 0.22, 0.8, 8), (0.58, 0.16, (60, 110, 220), 0.8, 0.9, 4),
        (0.4, 0.07, (255, 160, 190), 0.15, 0.55, -10)])])
    for j, (im, x_, y_, r_) in enumerate(scraps):
        kj = clamp((st - 0.125 * j) / 0.25)
        if kj > 0: place(c, im, c.W * x_ + jit.uniform(-4, 4) * u, c.H * y_ + (1 - kj) * c.H * 0.3, 1, r_ + jit.uniform(-1.5, 1.5), k * al, behind=True)
    L = cut_rgba(c, keep); L = sticker(L, int(12 * u))
    dx, dy = jit.uniform(-5, 5) * u, jit.uniform(-5, 5) * u
    M = np.float32([[1, 0, dx], [0, 1, dy]]); L = warp_rgba(L, M, c.W, c.H)
    sh = np.zeros_like(L); sh[..., 3] = cv2.GaussianBlur(L[..., 3], (0, 0), 10 * u) * 0.5
    sh = warp_rgba(sh, np.float32([[1, 0, 10 * u], [0, 1, 14 * u]]), c.W, c.H)
    c.img = over(c.img, sh, k); c.img = over(c.img, L, k)
    c.m = np.maximum(c.m, L[..., 3] * k)
    txt = e.o.get('text', 'AI 剪輯 全自動')
    rs = cached(e, ('r', int(st * 8) % 3), lambda: ransom(txt, 120 * u * (0.9 if len(txt) > 6 else 1.1), int(st * 8) % 3 + 2))
    if st > 0.25:
        sc = min(1.0, (c.W * 0.92) / rs.width)
        place(c, rs, c.W / 2 + dx, c.H * 0.1 + rs.height * sc / 2 + dy, sc, jit.uniform(-1.5, 1.5), al, guard=True)


# 7
@effect('doodle-boil', '蠟筆塗鴉：蠟筆線條圍著你，線條一直抖動')
def fx_doodle_boil(c, e):
    u = c.W / 1080; al = fade(c, e); st = math.floor(c.lt * 10) / 10; rnd = random.Random(int(st * 10))
    col = rgb(e.o.get('color'), PINK); col2 = rgb(e.o.get('color2'), LIME)
    m8 = (c.m > 0.5).astype(np.uint8)
    lay = Image.new('RGBA', (c.W, c.H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); reveal = ease_out(c.lt / 0.5)
    for off, cc in ((int(26 * u), col), (int(52 * u), col2)):
        dil = cv2.dilate(m8, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * off + 1,) * 2))
        cs, _ = cv2.findContours(dil, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if not cs: continue
        cnt = max(cs, key=cv2.contourArea)[:, 0, :]; step = max(1, len(cnt) // 220); pts = cnt[::step]
        pts = [p for p in pts if p[1] < c.H - 6]; n = int(len(pts) * reveal)
        for stroke in range(3):
            path = [(x + rnd.uniform(-4, 4) * u, y + rnd.uniform(-4, 4) * u) for x, y in pts[:n]]
            if len(path) > 1: d.line(path, fill=cc + (200,), width=max(3, int(rnd.uniform(5, 9) * u)), joint='curve')
    for j, (sx, sy) in enumerate(((c.fx - c.fw * 2.0, c.fy - c.fw * 1.4), (c.fx + c.fw * 1.9, c.fy - c.fw * 1.0), (c.fx + c.fw * 2.1, c.fy + c.fw * 1.0), (c.fx - c.fw * 2.1, c.fy + c.fw * 0.6))):
        if c.lt < 0.3 + 0.12 * j: continue
        s = c.fw * 0.3; cc = (col, col2)[j % 2]
        if j % 2 == 0:  # star
            ps = [(sx + s * (1 if q % 2 == 0 else 0.42) * math.cos(q * math.pi / 5 - math.pi / 2) + rnd.uniform(-3, 3) * u,
                   sy + s * (1 if q % 2 == 0 else 0.42) * math.sin(q * math.pi / 5 - math.pi / 2) + rnd.uniform(-3, 3) * u) for q in range(11)]
            d.line(ps, fill=cc + (230,), width=max(3, int(7 * u)), joint='curve')
        else:  # zigzag
            ps = [(sx - s + q * s / 3 + rnd.uniform(-3, 3) * u, sy + (s * 0.35 if q % 2 else -s * 0.35) + rnd.uniform(-3, 3) * u) for q in range(7)]
            d.line(ps, fill=cc + (230,), width=max(3, int(7 * u)), joint='curve')
    grain = (np.random.default_rng(int(st * 10)).random((c.H, c.W)) > 0.25).astype(np.float32)
    L = to_np(lay); L[..., 3] *= grain
    comp(c, L, 0, 0, al, behind=True)
    t = e.o.get('text')
    if t and c.lt > 0.5:
        lab = cached(e, ('t', int(st * 10) % 2), lambda: fit_text(t, c.W * 0.86, 'tchand' if has_cjk(t) else 'hand', int(90 * u), fill=col2, shadow=5))
        place(c, lab, c.W / 2 + rnd.uniform(-3, 3) * u, max(c.H * 0.08, c.fy - c.fw * 2.4), 1, rnd.uniform(-3, 3), al, guard=True)


# 8
@effect('cover-story', '雜誌封面：大大的刊名像雜誌一樣從下方浮上來，整個畫面變成封面')
def fx_cover_story(c, e):
    u = c.W / 1080; al = fade(c, e); k = ease_out(c.lt / 0.6)
    c.img = c.img * (1 - 0.5 * k) + grade(c.img, 'warm') * 0.5 * k
    col = rgb(e.o.get('color'), (255, 255, 255)); title = e.o.get('text', 'AI 生活')
    mast = cached(e, 'm', lambda: fit_text(title, c.W * 0.94, 'tcserif' if has_cjk(title) else 'didoneb', int(c.W * 0.38), fill=col, shadow=10))
    top = head_top(e); my = clamp(top + mast.height * 0.12, mast.height * 0.5 + c.H * 0.03, c.H * 0.4)
    ymast = my + (1 - k) * c.H * 0.7
    place(c, mast, c.W / 2, ymast, 1, 0, al * clamp(c.lt / 0.15), behind=True)
    iss = cached(e, 'i', lambda: text_img(e.o.get('issue', '2026 年 11 月號 · NO.37'), 30 * u, 'tcm', col, shadow=4))
    place(c, iss, c.W / 2, max(iss.height, ymast - mast.height * 0.5 - 4 * u), alpha=al * k, behind=True)
    lines = opt_lines(e, 'lines', '一個人的|AI 工作室|37 個特效 一鍵完成')
    y = max(c.H * 0.58, c.fy + c.fw * 1.4)
    for j, ln in enumerate(lines):
        big = j == 1
        im = cached(e, ('l', j), lambda: text_img(ln, (96 if big else 52) * u, 'tc' if big else 'tcm', LIME if big else (255, 255, 255), shadow=6))
        kj = ease_out((c.lt - 0.35 - 0.1 * j) / 0.3)
        comp(c, im, c.W * 0.05 - (1 - kj) * 80 * u, y, al * kj, guard=True); y += im.height * 0.86
    pr = cached(e, 'pr', lambda: text_img(e.o.get('price', 'NT$199'), 34 * u, 'uib', (255, 255, 255), shadow=4))
    comp(c, pr, c.W * 0.95 - pr.width, c.H * 0.93 - pr.height, al * k, guard=True)
    lay = Image.new('RGBA', (c.W, c.H), (0, 0, 0, 0)); ImageDraw.Draw(lay).rectangle([18 * u, 18 * u, c.W - 18 * u, c.H - 18 * u], outline=(255, 255, 255, 230), width=max(2, int(4 * u)))
    comp(c, lay, 0, 0, al * k)


# 9
@effect('frame-break', '衝出手機：影片縮進手機螢幕，你的肩膀以上衝出畫面')
def fx_frame_break(c, e):
    u = c.W / 1080; al = fade(c, e, 0.25); k = ease_inout(c.lt / 0.5); lk = ease_inout((c.lt - 0.45) / 0.4)
    s = 1 - 0.34 * k; sw = c.W * s; cx = c.W / 2
    sy0 = c.H * (0.5 - 0.5 * s) + c.H * 0.14 * k  # screen top: it drops a little so your head has room above it
    # content: at first the whole frame fills the screen; then it slides up so the screen's top edge sits at your shoulders
    fy_full = sy0 + c.fy * s; fy_pop = sy0 - c.fw * s * 1.15
    ty = (sy0 - 0) * 1 + (fy_pop - fy_full) * lk
    M = np.float32([[s, 0, cx - c.W / 2 * s + (c.W / 2 - c.fx) * s * 0.0], [0, s, ty]])
    bot = min(c.H * 0.97, M[1, 2] + c.H * s); sh_ = bot - sy0
    full = np.concatenate([c.img, np.ones_like(c.m)[..., None]], -1)
    content = warp_rgba(full, M, c.W, c.H); person = warp_rgba(cut_rgba(c), M, c.W, c.H)
    bgc = np.float32(rgb(e.o.get('color'), (24, 22, 30))) / 255
    res = cv2.GaussianBlur(c.img, (0, 0), 30 * u) * 0.3 + bgc * 0.7
    yy, xx = np.mgrid[0:c.H, 0:c.W]; sx0 = cx - sw / 2
    inside = cv2.GaussianBlur(((xx >= sx0) & (xx < sx0 + sw) & (yy >= sy0) & (yy < sy0 + sh_)).astype(np.float32), (0, 0), 1.0)
    bz = int(20 * u); r = int(60 * u * s)
    phone = Image.new('RGBA', (c.W, c.H), (0, 0, 0, 0))
    ImageDraw.Draw(phone).rounded_rectangle([sx0 - bz, sy0 - bz, sx0 + sw + bz, sy0 + sh_ + bz], r + bz, fill=(12, 12, 14, 255))
    blur, dy = int(30 * u), int(20 * u); pad = blur * 2 + dy
    tmp = Ctx(); tmp.W, tmp.H, tmp.img, tmp.m, tmp.fx, tmp.fy, tmp.fw = c.W, c.H, res, np.zeros((c.H, c.W), np.float32), c.fx, c.fy, c.fw
    comp(tmp, to_np(shadowed(phone, blur, dy, 160)), -pad, -pad); res = tmp.img
    ci = content.copy(); ci[..., 3] *= inside; res = over(res, ci)
    above = np.clip((sy0 + 2 - yy) / 3, 0, 1).astype(np.float32)
    pop_ = person.copy(); pop_[..., 3] *= above * clamp(lk * 1.5)
    shd = np.zeros_like(pop_); shd[..., 3] = cv2.GaussianBlur(pop_[..., 3], (0, 0), 16 * u) * 0.55
    res = over(res, warp_rgba(shd, np.float32([[1, 0, 0], [0, 1, 10 * u]]), c.W, c.H)); res = over(res, pop_)
    c.img = c.img * (1 - al) + res * al
    c.m = np.clip(person[..., 3] * np.maximum(inside, above), 0, 1) * al + c.m * (1 - al)
    c.fx = c.fx * s + M[0, 2]; c.fy = c.fy * s + M[1, 2]; c.fw = c.fw * s


# 10 --------------------------------------------------------------- vol.003
@effect('clone-row', '分身列隊：你身後左右各排出 3 個分身，最後全部被吸回你身上')
def fx_clone_row(c, e):
    u = c.W / 1080; n = int(e.o.get('count', 3)); L = cut_rgba(c)
    kin = ease_out(c.lt / 0.45); kout = ease_inout((c.lt - (e.d - 0.5)) / 0.45) if c.lt > e.d - 0.5 else 0
    spread = kin * (1 - kout); gap = float(e.o.get('gap', 0.23)) * c.W
    for j in range(n, 0, -1):
        sc = 0.9 ** j; dim = 1 - 0.12 * j
        for side in (-1, 1):
            dx = side * gap * j * spread; cx, cy = c.fx, c.H
            M = np.float32([[sc, 0, (1 - sc) * cx + dx], [0, sc, (1 - sc) * cy]])
            cl = warp_rgba(L, M, c.W, c.H); cl[..., :3] *= dim
            comp(c, cl, 0, 0, clamp(spread * 1.6) * (0.6 + 0.4 * (1 - kout)), behind=True)
    if 0 < kout < 1:
        flash = math.exp(-((kout - 0.95) / 0.08) ** 2) * 0.35
        c.img = np.clip(c.img + flash * c.m[..., None], 0, 1)


# 11
@effect('code-body', '程式碼身體：一道光由上往下掃過，你的身體變成綠色程式碼')
def fx_code_body(c, e):
    u = c.W / 1080; al = fade(c, e, 0.3); cell = max(8, int(float(e.o.get('cell', 15)) * u))
    chars = str(e.o.get('text', '01{}<>/=;AIclaude') )
    atlas = cached(e, 'atlas', lambda: glyph_atlas(list(dict.fromkeys(chars)) or list('01'), cell * 1.0))
    na, gh, gw = atlas.shape; rows, cols = c.H // gh + 1, c.W // gw + 1
    rng = np.random.default_rng(int(c.lt * 12))
    idx = cached(e, 'idx', lambda: np.random.default_rng(1).integers(0, na, (rows, cols)))
    flip = rng.random((rows, cols)) < 0.06; idx[flip] = rng.integers(0, na, flip.sum())
    lum = cv2.resize(c.img @ np.float32([0.299, 0.587, 0.114]), (cols, rows), interpolation=cv2.INTER_AREA)
    pm = cv2.resize(c.m, (cols, rows), interpolation=cv2.INTER_AREA)
    rain = cached(e, 'rain', lambda: np.random.default_rng(2).random(cols) * rows)
    head = (rain + c.lt * 18) % (rows * 1.4); ry = np.arange(rows)[:, None]
    trail = np.clip(1 - (head[None, :] - ry) / 14, 0, 1) * ((head[None, :] - ry) >= 0) * 0.28
    bright = np.clip(pm * (0.25 + lum * 1.25), 0, 1) + trail * (1 - pm)
    tiles = atlas[idx] * bright[..., None, None]
    code = tiles.transpose(0, 2, 1, 3).reshape(rows * gh, cols * gw)[:c.H, :c.W]
    green = np.float32(rgb(e.o.get('color'), (40, 255, 110))) / 255
    code_img = code[..., None] * green + (code[..., None] ** 3) * 0.6
    code_img = code_img + cv2.GaussianBlur(code_img, (0, 0), 4 * u) * 0.6 + np.float32([0, 0.03, 0.015])
    sweep = ease_inout(c.lt / 0.8) * (c.H * 1.08) - c.H * 0.04
    yy = np.arange(c.H, dtype=np.float32)[:, None, None]
    done = np.clip((sweep - yy) / (8 * u), 0, 1)
    line = np.exp(-((yy - sweep) / (6 * u)) ** 2) * (1.0 if sweep < c.H else 0)
    out = c.img * (1 - done) + np.clip(code_img, 0, 1) * done
    out = out + line * (green * 0.6 + 0.6) + np.exp(-np.abs(yy - sweep) / (40 * u)) * green * 0.25 * (sweep < c.H)
    c.img = c.img * (1 - al) + np.clip(out, 0, 1) * al


# 12
@effect('letter-dive', '文字俯衝：奶油色紙上一個字一個字打出來，鏡頭再飛進字裡面變回影片')
def fx_letter_dive(c, e):
    u = c.W / 1080; txt = e.o.get('text', '剪輯')
    kind = 'tcserif' if has_cjk(txt) else 'didoneb'
    def mk():
        im = fit_text(txt, c.W * 0.86, kind, int(c.W * 0.42), fill=(255, 255, 255))
        a = (np.asarray(im.split()[3], np.float32) / 255)
        dt = cv2.distanceTransform((a > 0.5).astype(np.uint8), cv2.DIST_L2, 5)
        py, px = np.unravel_index(np.argmax(dt), dt.shape)  # the thickest stroke: we fly into it
        return a, (px, py)
    a, (px, py) = cached(e, 'a', mk); h, w = a.shape
    tdur = min(e.d * 0.5, 0.18 * len(txt) + 0.2); zstart = tdur + 0.15
    paper = cached(e, 'paper', lambda: np.float32([242, 234, 216]) / 255 * (1 - 0.06 * cached(e, 'grain', lambda: np.random.default_rng(4).random((c.H, c.W), np.float32))[..., None]))
    x0, y0 = c.W / 2 - w / 2, c.H * 0.45 - h / 2
    if c.lt < zstart:
        reveal = clamp(c.lt / tdur); cut = int(w * reveal + 1)
        aa = a.copy(); aa[:, cut:] = 0
        ink = np.float32([30, 28, 26]) / 255; res = paper.copy()
        L = np.concatenate([np.broadcast_to(ink, (h, w, 3)), aa[..., None]], -1).astype(np.float32)
        tmp = Ctx(); tmp.W, tmp.H, tmp.img, tmp.m = c.W, c.H, res, np.zeros((c.H, c.W), np.float32); tmp.fx = tmp.fy = 0; tmp.fw = 1
        comp(tmp, L, x0, y0); c.img = tmp.img; c.m = c.m * 0; return
    q = clamp((c.lt - zstart) / max(0.3, e.d - zstart - 0.1)); z = math.exp(q * q * math.log(60))
    tx, ty = x0 + px, y0 + py
    cx = tx + (c.W / 2 - tx) * clamp((z - 1) / 4); cy = ty + (c.H / 2 - ty) * clamp((z - 1) / 4)
    M = np.float32([[z, 0, cx - px * z], [0, z, cy - py * z]])
    win = cv2.warpAffine(a, M, (c.W, c.H), flags=cv2.INTER_LINEAR, borderValue=0)
    vid = c.img
    c.img = paper * (1 - win[..., None]) + vid * win[..., None]
    if z > 40: c.img = c.img * 0 + vid


# 13
@effect('blade-slice', '斬擊切片：一道白光斜斜劃過，畫面從嘴巴高度錯開再合回來')
def fx_blade_slice(c, e):
    u = c.W / 1080; ang = math.radians(float(e.o.get('angle', -14)))
    py = c.fy + c.fw * 0.3; px = c.fx; nx, ny = -math.sin(ang), math.cos(ang); dx_, dy_ = math.cos(ang), math.sin(ang)
    yy, xx = np.mgrid[0:c.H, 0:c.W].astype(np.float32); side = (xx - px) * nx + (yy - py) * ny
    t0 = 0.12; flash = clamp((c.lt - 0) / t0)
    off = 0.0
    if c.lt > t0:
        q = (c.lt - t0) / max(0.2, e.d - t0 - 0.1)
        off = (math.sin(clamp(q) * math.pi) ** 0.6) * float(e.o.get('shift', 0.07)) * c.W
    upper = side < 0
    mapx = (xx + np.where(upper, off * dx_, -off * dx_ * 0.4)).astype(np.float32); mapy = (yy + np.where(upper, off * dy_, -off * dy_ * 0.4)).astype(np.float32)
    img = cv2.remap(c.img, mapx, mapy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    c.m = cv2.remap(c.m, mapx, mapy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    gapw = 2.5 * u + off * 0.04; gap = np.clip(1 - np.abs(side) / max(1, gapw), 0, 1)[..., None] * clamp(off / (4 * u))
    img = img * (1 - gap)
    along = (xx - px) * dx_ + (yy - py) * dy_; head = -c.W * 0.7 + flash * c.W * 1.6
    streak = np.exp(-(side / (5 * u)) ** 2) * np.clip(1 - np.abs(along - head) / (c.W * 0.55), 0, 1) * (1 if c.lt < t0 + 0.12 else 0)
    glow = np.exp(-(np.abs(side) / (40 * u))) * streak.max(initial=0) * np.exp(-max(0, c.lt - t0) * 10) * 0.6
    c.img = np.clip(img + (streak[..., None] * 1.4 + glow[..., None]), 0, 1)
    if 0 < c.lt - t0 < 0.08: c.img = np.clip(c.img + 0.25, 0, 1)


# 14
@effect('press-front', '報紙頭版：整個畫面變成報紙頭版，你在網點黑白照片裡說話')
def fx_press_front(c, e):
    u = c.W / 1080; al = fade(c, e); k = ease_out(c.lt / 0.35)
    head = e.o.get('text', 'AI 取代剪輯師？'); sub = e.o.get('sub', '創作者：一句話就能剪好一支影片')
    date = e.o.get('date') or roc_today()
    bx = news_box(c, u)
    def mk():
        pg = news_page(c.W, c.H, head, sub, bx, date); return to_np(pg)[..., :3]
    pg = cached(e, 'pg', mk)
    pg = pg.copy(); pg[bx[1]:bx[3], bx[0]:bx[2]] = news_photo(c, *bx)
    s = 1.25 - 0.25 * k; rot = 3 * (1 - k)
    M = cv2.getRotationMatrix2D((c.W / 2, c.H / 2), rot, s)
    L = warp_rgba(np.concatenate([pg, np.ones((c.H, c.W, 1), np.float32)], -1), M, c.W, c.H)
    c.img = over(c.img, L, al * clamp(c.lt / 0.08)); c.m = c.m * 0


# 15
@effect('head-stack', '頭頂疊標籤：白色標籤一張張掉下來，疊在你頭上和肩膀旁，最後崩塌')
def fx_head_stack(c, e):
    u = c.W / 1080; tags = opt_lines(e, 'text', 'ChatGPT|Claude|Gemini|Notion|n8n|Canva|Kling')
    top = head_top(e); every = float(e.o.get('every', 0.22)); fall = 0.32
    collapse = c.lt > e.d - 0.55; ck = clamp((c.lt - (e.d - 0.55)) / 0.5)
    rnd = random.Random(9); stack_y = top; sh_y = c.fy + c.fw * 1.55; slots = []
    for j, t in enumerate(tags):
        im = cached(e, ('t', j), lambda: shadowed(rrect(font('uib', 40 * u).getlength(t) + 70 * u, 84 * u, 8 * u, (255, 255, 255, 255)), int(8 * u), int(6 * u), 120))
        lb = cached(e, ('l', j), lambda: text_img(t, 40 * u, 'uib', (25, 25, 25)))
        where = 'head' if j % 3 != 2 else ('L' if (j // 3) % 2 == 0 else 'R')
        h_ = 84 * u * 0.92
        if where == 'head': x = c.fx + rnd.uniform(-0.25, 0.25) * c.fw; y = stack_y - h_ / 2; stack_y -= h_
        else:
            x = c.fx + (-1 if where == 'L' else 1) * c.fw * 1.75; y = sh_y - h_ / 2; sh_y -= h_ * 0.0
        slots.append((im, lb, x, y, rnd.uniform(-7, 7), j * every))
    for j, (im, lb, x, y, r, t0) in enumerate(slots):
        if c.lt < t0: continue
        f = clamp((c.lt - t0) / fall); yy = -im.height + (y + im.height) * f ** 2
        if f >= 1: yy = y + math.sin((c.lt - t0 - fall) * 30) * 6 * u * math.exp(-(c.lt - t0 - fall) * 9)
        rot = r
        if collapse:
            yy += (ck ** 2) * c.H * (0.9 + 0.15 * j); rot = r + ck * (60 if j % 2 else -60); x = x + ck * (j % 3 - 1) * c.W * 0.2
        place(c, im, x, yy, 1, rot, guard=True); place(c, lb, x, yy - 2 * u, 1, rot, guard=True)


# 16
def engrave(gray, period):
    """Banknote line engraving: wavy lines that get thicker where the picture is darker."""
    H, W = gray.shape; yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    phase = (yy + np.sin(xx / (period * 3.0)) * period * 0.6) / period
    tri = np.abs((phase % 1.0) - 0.5) * 2
    dark = 1 - gray; return np.clip((dark * 1.05 - tri) * 3 + 0.5, 0, 1)


@effect('banknote', '紙鈔：把你變成一張紙鈔風格的鈔票（虛構設計，不是真鈔）')
def fx_banknote(c, e):
    u = c.W / 1080; al = fade(c, e); k = ease_out(c.lt / 0.4)
    nw = int(c.W * 0.88); nh = int(nw * 0.5); ink = np.float32(rgb(e.o.get('color'), (34, 92, 70))) / 255
    def base():
        im = Image.new('RGBA', (nw, nh), (226, 222, 196, 255)); d = ImageDraw.Draw(im)
        for i in range(0, nw, max(4, int(11 * u))):  # guilloche wave pattern
            pts = [(i + 18 * u * math.sin(y / (24 * u) + i / 37), y) for y in range(0, nh, 6)]
            d.line(pts, fill=tuple(int(v * 255) for v in ink) + (26,), width=1)
        for r_ in range(6):
            d.rounded_rectangle([10 * u + r_ * 5 * u, 10 * u + r_ * 5 * u, nw - 10 * u - r_ * 5 * u, nh - 10 * u - r_ * 5 * u], int(26 * u),
                                outline=tuple(int(v * 255) for v in ink) + (200 if r_ in (0, 3) else 90,), width=max(1, int((3 if r_ in (0, 3) else 1) * u)))
        col = tuple(int(v * 255) for v in ink) + (255,)
        val = e.o.get('value', '1000'); name = e.o.get('text', 'AITJB 創作券')
        d.text((50 * u, 40 * u), val, font=font('tcserif', 78 * u), fill=col); d.text((nw - 50 * u, nh - 40 * u), val, font=font('tcserif', 78 * u), fill=col, anchor='rd')
        fs_ = 60 * u
        while font('tcserif', fs_).getlength(name) > nw * 0.46 and fs_ > 12: fs_ *= 0.92
        d.text((nw * 0.3, nh * 0.32), name, font=font('tcserif', fs_), fill=col, anchor='mm')
        d.text((nw * 0.3, nh * 0.5), e.o.get('words', '壹仟點 · AI 學習基金'), font=font('tcm', 34 * u), fill=col, anchor='mm')
        d.text((nw * 0.3, nh * 0.64), e.o.get('serial', 'AJ 037 2026 TW'), font=font('mono', 30 * u), fill=(170, 40, 40, 255), anchor='mm')
        d.text((nw * 0.3, nh * 0.8), '本券為娛樂設計，非法定貨幣', font=font('tcm', 22 * u), fill=col, anchor='mm')
        d.ellipse([nw * 0.56, nh * 0.1, nw * 0.93, nh * 0.9], outline=col, width=max(2, int(4 * u)))
        return to_np(im)
    B = cached(e, 'b', base).copy()
    ox0, oy0, ox1, oy1 = int(nw * 0.565), int(nh * 0.11), int(nw * 0.925), int(nh * 0.89); pw, ph_ = ox1 - ox0, oy1 - oy0
    s = (ph_ * 1.05) / (c.fw * 2.6); src = cv2.resize(c.img, (int(c.W * s), int(c.H * s)), interpolation=cv2.INTER_AREA)
    cx, cy = int(c.fx * s - pw / 2), int(c.fy * s - ph_ * 0.45)
    pad = np.pad(src, ((ph_, ph_), (pw, pw), (0, 0)), mode='edge'); crop = pad[cy + ph_:cy + 2 * ph_, cx + pw:cx + 2 * pw]
    g = np.clip((crop @ np.float32([0.299, 0.587, 0.114]) - 0.5) * 1.4 + 0.55, 0, 1)
    lines = engrave(g, max(3.0, 6 * u))
    yy, xx = np.mgrid[0:ph_, 0:pw]; oval = (((xx - pw / 2) / (pw / 2)) ** 2 + ((yy - ph_ / 2) / (ph_ / 2)) ** 2 < 0.96).astype(np.float32)
    a = (lines * oval)[..., None]; B[oy0:oy1, ox0:ox1, :3] = B[oy0:oy1, ox0:ox1, :3] * (1 - a * 0.95) + ink * a * 0.95
    bg = cv2.GaussianBlur(c.img, (0, 0), 24 * u) * 0.45
    res = c.img * (1 - k) + bg * k
    rot = float(e.o.get('rot', -4)) * k + (1 - k) * 25
    M = cv2.getRotationMatrix2D((nw / 2, nh / 2), rot, 0.7 + 0.3 * k); M[0, 2] += c.W / 2 - nw / 2; M[1, 2] += c.H * 0.5 - nh / 2 + (1 - k) * c.H * 0.4
    L = warp_rgba(B, M, c.W, c.H); sh = np.zeros_like(L); sh[..., 3] = cv2.GaussianBlur(L[..., 3], (0, 0), 20 * u) * 0.6
    res = over(res, warp_rgba(sh, np.float32([[1, 0, 0], [0, 1, 18 * u]]), c.W, c.H)); res = over(res, L)
    c.img = c.img * (1 - al) + res * al; c.m = c.m * (1 - k)


# 17
@effect('live-cursor', '即時游標：一個掛著 Claude 名牌的游標出現，連框抓住你拖到旁邊再放回來')
def fx_live_cursor(c, e):
    u = c.W / 1080; al = fade(c, e); name = e.o.get('text', 'Claude'); col = rgb(e.o.get('color'), (217, 119, 87))
    box = cached(e, 'box', lambda: person_box(c)); bx0, by0, bx1, by1 = box; by1 = min(by1, c.H - 6 * u)
    side = -1 if c.fx > c.W / 2 else 1; dist = float(e.o.get('dist', 0.22)) * c.W * side
    t1, t2 = 0.55, e.d - 0.6
    mv = ease_inout((c.lt - t1) / 0.45) * (1 - ease_inout((c.lt - t2) / 0.45)) if c.lt > t1 else 0
    dx = dist * mv
    if abs(dx) > 0.5:
        L = cut_rgba(c); plate = clean_plate(c, e)
        c.img = over(plate, warp_rgba(L, np.float32([[1, 0, dx], [0, 1, 0]]), c.W, c.H))
        c.m = cv2.warpAffine(c.m, np.float32([[1, 0, dx], [0, 1, 0]]), (c.W, c.H))
        c.fx += dx
    fk = ease_out((c.lt - 0.1) / 0.3)
    lay = Image.new('RGBA', (c.W, c.H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    x0, x1 = max(8 * u, bx0 + dx - 20 * u), min(c.W - 8 * u, bx1 + dx + 20 * u); y0 = max(40 * u, by0 - 20 * u)
    if fk > 0:
        d.rectangle([x0, y0, x1, by1], outline=col + (int(255 * fk),), width=max(2, int(4 * u)))
        hs = 18 * u
        for hx, hy in ((x0, y0), (x1, y0), (x0, by1), (x1, by1), ((x0 + x1) / 2, y0), (x0, (y0 + by1) / 2), (x1, (y0 + by1) / 2)):
            d.rectangle([hx - hs / 2, hy - hs / 2, hx + hs / 2, hy + hs / 2], fill=(255, 255, 255, int(255 * fk)), outline=col + (int(255 * fk),), width=max(2, int(3 * u)))
        sz = text_img(f'{int(x1 - x0)} × {int(by1 - y0)}', 26 * u, 'mono', (255, 255, 255))
        d.rounded_rectangle([(x0 + x1) / 2 - sz.width / 2, y0 - sz.height - 14 * u, (x0 + x1) / 2 + sz.width / 2, y0 - 14 * u], int(4 * u), fill=col + (int(255 * fk),))
        lay.alpha_composite(sz, (int((x0 + x1) / 2 - sz.width / 2), int(y0 - sz.height - 14 * u)))
    comp(c, lay, 0, 0, al, guard=True)
    def cur_tag():
        cu = cursor(70 * u); d2 = ImageDraw.Draw(cu)
        tg = text_img(name, 34 * u, 'uib', (255, 255, 255)); pill = rrect(tg.width + 20 * u, tg.height * 0.8, 6 * u, col + (255,))
        pill.alpha_composite(tg, (int(10 * u), int(-tg.height * 0.1)))
        out = Image.new('RGBA', (int(cu.width + pill.width + 10 * u), int(cu.height + pill.height)), (0, 0, 0, 0))
        out.alpha_composite(cu, (0, 0)); out.alpha_composite(pill, (int(cu.width * 0.6), int(cu.height * 0.7))); return out
    ct = cached(e, 'ct', cur_tag)
    gx, gy = clamp(x1 if side > 0 else x0, c.W * 0.1, c.W * 0.78), clamp((y0 + by1) / 2, c.H * 0.2, c.H * 0.8)
    if c.lt < t1:
        ak = ease_out(clamp(c.lt / t1)); cx = gx + (c.W * 0.5 * side) * (1 - ak); cy = gy + c.H * 0.25 * (1 - ak)
    else: cx, cy = gx, gy
    place(c, ct, cx + ct.width / 2 - 6 * u, cy + ct.height / 2 - 6 * u, 1, 0, al * clamp(c.lt / 0.15))


# 18
@effect('paper-tear', '撕報紙：報紙頭版從中間撕開往左右飛走，露出你的影片')
def fx_paper_tear(c, e):
    u = c.W / 1080; head = e.o.get('text', '本週 AI 大事'); sub = e.o.get('sub', '一次看懂，三分鐘')
    bx = news_box(c, u)
    def mk():
        pg = to_np(news_page(c.W, c.H, head, sub, bx, e.o.get('date') or roc_today()))
        pg[bx[1]:bx[3], bx[0]:bx[2], :3] = news_photo(c, *bx)
        rnd = random.Random(4); ys = np.arange(0, c.H + 24, 24); xs = c.W / 2 + np.array([rnd.uniform(-1, 1) * 34 * u for _ in ys])
        tear = np.interp(np.arange(c.H), ys, xs).astype(np.float32)
        return pg, tear
    pg, tear = cached(e, 'pg', mk)
    t0 = float(e.o.get('at', 0.35)); k = clamp((c.lt - t0) / 0.55) ** 1.6
    xx = np.arange(c.W, dtype=np.float32)[None, :]
    left = (xx < tear[:, None]).astype(np.float32)
    edgeL = np.clip(1 - (tear[:, None] - xx) / (7 * u), 0, 1) * left; edgeR = np.clip(1 - (xx - tear[:, None]) / (7 * u), 0, 1) * (1 - left)
    P = pg.copy(); P[..., :3] = P[..., :3] * (1 - (edgeL + edgeR)[..., None]) + (edgeL + edgeR)[..., None] * 0.98
    LL = P.copy(); LL[..., 3] *= left; RR = P.copy(); RR[..., 3] *= 1 - left
    ML = cv2.getRotationMatrix2D((0, c.H * 0.6), 8 * k, 1); ML[0, 2] -= c.W * 0.75 * k
    MR = cv2.getRotationMatrix2D((c.W, c.H * 0.6), -8 * k, 1); MR[0, 2] += c.W * 0.75 * k
    res = c.img.copy()
    for L, M in ((LL, ML), (RR, MR)):
        W_ = warp_rgba(L, M, c.W, c.H); sh = np.zeros_like(W_); sh[..., 3] = cv2.GaussianBlur(W_[..., 3], (0, 0), 16 * u) * 0.55 * clamp(k * 4)
        res = over(res, sh); res = over(res, W_)
    c.img = res
    if k < 1: c.m = c.m * (1 - np.maximum(warp_rgba(LL, ML, c.W, c.H)[..., 3], warp_rgba(RR, MR, c.W, c.H)[..., 3]))


# 19
@effect('impact-frame', '漫畫衝擊格：變成黑白漫畫格，集中線加大字，黑白一直反轉')
def fx_impact_frame(c, e):
    u = c.W / 1080; al = fade(c, e, 0.12); word = e.o.get('text', '衝擊！'); rate = float(e.o.get('rate', 8))
    g = c.img @ np.float32([0.299, 0.587, 0.114])
    edges = cv2.Canny((g * 255).astype(np.uint8), 40, 110).astype(np.float32) / 255
    edges = cv2.dilate(edges, np.ones((2, 2), np.uint8))
    tone = halftone(np.clip(g * 1.25, 0, 1), max(4, int(7 * u)), 0.8)
    ink = np.clip(np.maximum(edges, (g < 0.18).astype(np.float32)) + tone * 0.55 * (g < 0.55), 0, 1)
    yy, xx = np.mgrid[0:c.H, 0:c.W].astype(np.float32); ang = np.arctan2(yy - c.fy, xx - c.fx); rr = np.hypot(xx - c.fx, yy - c.fy)
    rays = cached(e, 'rays', lambda: np.random.default_rng(3).random(720))
    ai = ((ang + math.pi) / (2 * math.pi) * 720).astype(int) % 720
    speed = ((rays[ai] > 0.55) & (rr > c.fw * (1.5 + rays[ai] * 0.8))).astype(np.float32) * (1 - c.m)
    speed *= np.clip((rr - c.fw * 1.4) / (c.fw * 2.0), 0, 1)
    inv = int(c.lt * rate) % 2 == 1
    ink_all = np.clip(ink * np.maximum(c.m, 0.6) + speed, 0, 1)
    person_pic = 1 - np.clip(ink, 0, 1); bg_pic = 1 - speed
    if inv: bg_pic = speed  # black room, white speed lines
    m_ = np.clip(c.m * 1.3, 0, 1); pic = person_pic * m_ + bg_pic * (1 - m_)
    out = np.repeat(pic[..., None], 3, 2)
    b = int(26 * u); out[:b] = 0 if not inv else 1; out[-b:] = 0 if not inv else 1; out[:, :b] = 0 if not inv else 1; out[:, -b:] = 0 if not inv else 1
    c.img = c.img * (1 - al) + out * al
    fg, bgc = ((0, 0, 0), (255, 255, 255)) if not inv else ((255, 255, 255), (0, 0, 0))
    big = cached(e, ('w', inv), lambda: fit_text(word, c.W * 0.86, 'tc' if has_cjk(word) else 'bold', int(c.W * 0.28), fill=fg, stroke=int(14 * u), stroke_fill=bgc))
    s = 1.3 - 0.3 * ease_out(c.lt / 0.15)
    place(c, big, c.W / 2, max(big.height * 0.55, c.fy - c.fw * 2.0), s, 6, al, guard=True)


# 20
@effect('blow-away', '隨風消散：身體從左邊開始化成沙粒往左飄走，最後只剩空的畫面')
def fx_blow_away(c, e):
    u = c.W / 1080; plate = clean_plate(c, e)
    box = cached(e, 'box', lambda: person_box(c)); bx0, _, bx1, _ = box
    span = float(e.o.get('span', 0.75)) * e.d; wind = -1 if str(e.o.get('dir', 'left')) == 'left' else 1
    front_x = lambda t: (bx0 - 40 * u) + (bx1 - bx0 + 80 * u) * clamp(t / span) if wind < 0 else (bx1 + 40 * u) - (bx1 - bx0 + 80 * u) * clamp(t / span)
    noise = cached(e, 'noise', lambda: (lambda n: (n - n.mean()) / (n.std() + 1e-6) * 45 * u)(cv2.GaussianBlur(np.random.default_rng(6).random((c.H, c.W)).astype(np.float32), (0, 0), 14 * u)))
    xx = np.arange(c.W, dtype=np.float32)[None, :]
    fxp = front_x(c.lt)
    keep = np.clip(((xx - fxp) + noise) / (8 * u), 0, 1) if wind < 0 else np.clip(((fxp - xx) + noise) / (8 * u), 0, 1)
    pm = c.m * keep
    k_ = max(3, int(12 * u)) | 1  # reach a little past your outline, so the soft edge of the cut-out doesn't stay behind
    m_wide = cv2.GaussianBlur(cv2.dilate(c.m, np.ones((k_, k_), np.uint8)), (0, 0), 3 * u)
    gone = np.clip(m_wide * (1 - keep), 0, 1)
    def seeds():
        step = max(2, int(3 * u)); ys, xs = np.nonzero(c.m[::step, ::step] > 0.5); ys, xs = ys * step, xs * step
        jitter = np.random.default_rng(7).random((2, len(xs))).astype(np.float32)
        return xs.astype(np.float32) + jitter[0] * step, ys.astype(np.float32) + jitter[1] * step, np.random.default_rng(8).random(len(xs)).astype(np.float32)
    sx, sy, sr = cached(e, 'seeds', seeds)
    xi, yi = np.clip(sx.astype(int), 0, c.W - 1), np.clip(sy.astype(int), 0, c.H - 1)
    nz = noise[yi, xi]  # each grain leaves exactly when the ragged edge passes it, so no holes open up
    rel = ((sx + nz - (bx0 - 40 * u)) / (bx1 - bx0 + 80 * u)) if wind < 0 else (((bx1 + 40 * u) - sx + nz) / (bx1 - bx0 + 80 * u))
    t_rel = np.clip(rel, 0, 1) * span
    age = c.lt - t_rel
    live = age > 0
    if c.lt < e.d - 0.05:
        a_ = age[live]; r_ = sr[live]
        px = sx[live] + wind * (a_ * 260 + a_ * a_ * 1300) * (0.6 + 0.8 * r_) * u + np.sin(a_ * 7 + r_ * 20) * 12 * u
        py = sy[live] - (a_ * (110 + 220 * r_) + a_ * a_ * 120) * u + np.sin(a_ * 5 + r_ * 9) * 9 * u
        colr = c.img[yi[live], xi[live]]; alpha = np.clip(1 - a_ / (0.6 + r_ * 0.6), 0, 1)
        ok = (px >= 0) & (px < c.W - 1) & (py >= 0) & (py < c.H - 1)
        acc = np.zeros((c.H, c.W, 3), np.float32); aa = np.zeros((c.H, c.W), np.float32)
        pxi, pyi = px[ok].astype(int), py[ok].astype(int)
        np.add.at(acc, (pyi, pxi), colr[ok] * alpha[ok, None]); np.add.at(aa, (pyi, pxi), alpha[ok])
        acc = cv2.GaussianBlur(acc, (0, 0), 1.2 * max(1, u)) * 4; aa = np.clip(cv2.GaussianBlur(aa, (0, 0), 1.2 * max(1, u)) * 4, 0, 1)
    else:
        acc = np.zeros((c.H, c.W, 3), np.float32); aa = np.zeros((c.H, c.W), np.float32)
    base = c.img * (1 - gone[..., None]) + plate * gone[..., None]
    base = base * (1 - aa[..., None]) + np.clip(acc / np.maximum(aa[..., None], 1e-3), 0, 1) * aa[..., None]
    c.img = base; c.m = pm


# 21
@effect('sketch-words', '鉛筆手寫字：背景變成奶油色紙，你身後一行行出現鉛筆手寫字')
def fx_sketch_words(c, e):
    u = c.W / 1080; al = fade(c, e); k = ease_out(c.lt / 0.25)
    paper = cached(e, 'paper', lambda: paper_bg(c.W, c.H) * np.float32([1.0, 0.98, 0.93]))
    m = c.m[..., None]; c.img = c.img * (1 - k * (1 - m)) + paper * k * (1 - m)
    lines = opt_lines(e, 'text', '想法|→ 腳本|→ 拍攝|→ AI 剪輯|✓ 發布')
    ink = (70, 70, 78); y = c.H * 0.08; per = max(0.3, (e.d - 0.6) / max(1, len(lines)))
    for j, ln in enumerate(lines):
        im = cached(e, ('l', j), lambda: fit_text(ln, c.W * 0.84, 'tchand' if has_cjk(ln) else 'hand', int(min(92 * u, (max(head_top(e), c.H * 0.3) - c.H * 0.06) / max(1, len(lines)) / 1.05)), fill=ink))
        a = np.asarray(im, np.float32) / 255; g = cached(e, ('g', j), lambda: (np.random.default_rng(j).random(a.shape[:2]) > 0.18).astype(np.float32))
        a[..., 3] *= g * 0.9
        rv = clamp((c.lt - 0.3 - per * j) / (per * 0.85))
        if rv <= 0: y += im.height * 0.9; continue
        cut = int(a.shape[1] * rv); a[:, cut:, 3] = 0
        x = c.W * (0.07 + 0.05 * (j % 2))
        comp(c, a, x, y, al * k, behind=True)
        y += im.height * 0.9


# ---------- video in/out + tracking ----------
def probe(path):
    j = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=r_frame_rate:format=duration',
                                   '-of', 'json', path], capture_output=True, text=True, check=True).stdout)
    fr = j['streams'][0]['r_frame_rate']; num, den = fr.split('/'); fps = float(num) / float(den or 1)
    png = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-frames:v', '1', '-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True, check=True).stdout
    h, w = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR).shape[:2]
    return (fr if fps <= 30.5 else '30'), min(fps, 30.0), float(j['format']['duration']), w, h


def read_frames(path, W, H, fr):
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', path, '-vf', f'fps={fr},scale={W}:{H}:flags=bicubic,format=rgb24', '-f', 'rawvideo', '-'],
                         stdout=subprocess.PIPE, bufsize=10 ** 8)
    n = W * H * 3
    try:
        while True:
            b = p.stdout.read(n)
            if len(b) < n: break
            yield np.frombuffer(b, np.uint8).reshape(H, W, 3)
    finally:
        if p.poll() is None: p.kill()
        p.stdout.close(); p.wait()


def guided(I, p, r=8, eps=2e-3):
    box = lambda x: cv2.boxFilter(x, -1, (2 * r + 1, 2 * r + 1))
    mI, mp_ = box(I), box(p); a = (box(I * p) - mI * mp_) / (box(I * I) - mI * mI + eps); b = mp_ - a * mI
    return np.clip(box(a) * I + box(b), 0, 1)


class Tracker:
    def __init__(self, aw, ah):
        import mediapipe as mp
        from mediapipe.tasks.python import vision
        from mediapipe.tasks.python.core.base_options import BaseOptions
        self.mp = mp
        self.seg = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
            base_options=BaseOptions(model_asset_path=os.path.join(ROOT, 'models', 'selfie_segmenter.tflite')),
            running_mode=vision.RunningMode.VIDEO, output_confidence_masks=True, output_category_mask=False))
        self.fd = cv2.FaceDetectorYN.create(os.path.join(ROOT, 'models', 'yunet.onnx'), '', (aw, ah), 0.6, 0.3, 20)
        self.prev = None

    def __call__(self, rgb, ms):
        img = self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
        ms_ = self.seg.segment_for_video(img, ms).confidence_masks
        m = ms_[-1].numpy_view().astype(np.float32); m = m.reshape(m.shape[0], m.shape[1])
        if m.shape[:2] != rgb.shape[:2]: m = cv2.resize(m, (rgb.shape[1], rgb.shape[0]))
        m = guided(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255, m)
        m = np.clip((m - 0.5) * 1.6 + 0.5, 0, 1)
        if self.prev is not None: m = 0.65 * m + 0.35 * self.prev
        self.prev = m
        _, f = self.fd.detect(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        face = None
        if f is not None and len(f):
            r = max(f, key=lambda r: r[2] * r[3] * r[-1]); face = (r[0] + r[2] / 2, r[1] + r[3] / 2, r[2])
        else:
            rows = np.where((m > 0.5).sum(1) > m.shape[1] * 0.01)[0]
            if len(rows):
                top = rows[0]; band = m[top:top + max(4, int(m.shape[0] * 0.06))] > 0.5; xs = np.where(band.any(0))[0]
                fw = max(8.0, (xs.max() - xs.min()) * 0.8); face = (float(xs.mean()), top + fw * 0.7, fw)
        return (m * 255).astype(np.uint8), face


def smooth(vals, fps, tau=0.18):
    idx = [i for i, v in enumerate(vals) if v is not None]
    if not idx: return None
    arr = np.array([vals[i] if vals[i] is not None else (np.nan,) * 3 for i in range(len(vals))], np.float64)
    for k in range(3):
        col = arr[:, k]; good = ~np.isnan(col); col[~good] = np.interp(np.where(~good)[0], np.where(good)[0], col[good]); arr[:, k] = col
    a = 1 - math.exp(-1 / (fps * tau))  # forward then backward pass, so the smoothing has no lag
    for i in range(1, len(arr)): arr[i] = arr[i - 1] + a * (arr[i] - arr[i - 1])
    for i in range(len(arr) - 2, -1, -1): arr[i] = arr[i + 1] + a * (arr[i] - arr[i + 1])
    return arr


class Ctx: pass


# aitjb：沿用引擎的效果時，預設文字改成繁體中文 (使用者給的文字永遠優先)
ZH_DEFAULTS = {
    'led-sign': {'text': 'AI 創作'},
    'red-collage': {'text': 'AI', 'lines': '一支影片|37 個特效|不用剪輯軟體'},
    'checklist': {'title': 'Claude 正在剪你的影片', 'text': '找到你的臉::每一格|把你從背景去背::AI 遮罩|把字放到你身後::景深|加上音效::自動'},
    'apple-toggles': {'text': '一支影片|輸入 /effects|不用剪輯軟體'},
    'timeline': {'text': '自動剪輯', 'sub': 'Claude 幫你剪'},
    'glass-widgets': {'sub': '個特效|一支影片', 'text': '37'},
    'liquid-glass-graph': {'text': '完播率'},
    'over-the-shoulder-zoom': {'text': '這支觀看數|熱門 reels 總數'},
    'messages': {'title': '訊息', 'text': '這支怎麼剪的？？|等等 這是什麼 app|拜託分享特效|特效'},
    'headline-wall': {'text': 'Claude Code 新手必學的 5 個指令::12.4 萬次觀看|一句話做出動態網頁::8.6 萬次觀看|AI 幫你剪片 全自動::6.1 萬次觀看',
                      'label': '7 支 reels 的觀看數', 'total': '26.7萬'},
    'check-pills': {'text': '開場鉤子|字幕|剪接|B-roll', 'board': 'Reels · 37 個特效'},
    'spotlight': {}, 'match-cut': {}, 'orbit': {}, 'carousel-spin': {}, 'rabbit-hole': {},
}


class Fx:
    def __init__(self, d, fps):
        self.name = d['fx']; self.start = float(d.get('start', 0)); self.end = float(d.get('end', 1e9)); self.d = max(0.05, self.end - self.start)
        self.o = {k: v for k, v in d.items() if k not in ('fx', 'start', 'end')}; self.state = {}; self.cards = []
        if self.o.get('lang', 'zh') != 'en':
            for k, v in ZH_DEFAULTS.get(self.name, {}).items(): self.o.setdefault(k, v)
        self.words = []; self.med = None; self.top = None


def load_cards(folder, thumbs):
    out = []
    if folder and os.path.isdir(folder):
        for n in sorted(os.listdir(folder)):
            p = os.path.join(folder, n); ext = n.lower().rsplit('.', 1)[-1]
            if ext in ('jpg', 'jpeg', 'png', 'webp'): out.append(Image.open(p).convert('RGB'))
            elif ext in ('mp4', 'mov', 'm4v', 'webm'):
                cap = cv2.VideoCapture(p); cap.set(cv2.CAP_PROP_POS_MSEC, 1000); ok, fr = cap.read(); cap.release()
                if ok: out.append(Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)))
    return out or thumbs


WORD_FX = ('captions', 'halftone-paper')  # effects that need to know when each word is said


def has_audio(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a', '-show_entries', 'stream=index', '-of', 'csv=p=0', path],
                       capture_output=True, text=True)
    return bool(r.stdout.strip())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('args', nargs='*', help='[effect] input.mp4 output.mp4')
    ap.add_argument('--plan'); ap.add_argument('--start', type=float); ap.add_argument('--end', type=float)
    ap.add_argument('--text'); ap.add_argument('--images'); ap.add_argument('--opt', action='append', default=[], help='key=value')
    ap.add_argument('--still', help='comma-separated seconds: save PNG check frames instead of a video')
    ap.add_argument('--width', type=int, default=1080, help='short side of the output (1080 default, 2160 for 4K)')
    ap.add_argument('--words', help='a words.json from words.py (default: <video>.words.json, made if missing)')
    ap.add_argument('--no-sfx', action='store_true', help='no sound effects')
    ap.add_argument('--sfx-volume', type=float, default=0.0, help='sound effects louder/quieter in dB (e.g. -4)')
    ap.add_argument('--profile', nargs='*', metavar='NAME HANDLE', help='save your name and handle, or show them')
    ap.add_argument('--list', action='store_true')
    a = ap.parse_args()
    if a.list:
        for i, (k, (_, d)) in enumerate(EFFECTS.items()): print(f'{i + 1:2d}. {k:22s} {d}')
        return
    if a.profile is not None:
        if len(a.profile) == 2:
            h = a.profile[1].strip(); json.dump({'name': a.profile[0].strip(), 'handle': h if h.startswith('@') else '@' + h}, open(PROFILE_PATH, 'w'), indent=1)
        p = load_profile(); print(f"Profile: {p['name']} ({p['handle']})" + ('' if os.path.exists(PROFILE_PATH) else '  [not set yet]'))
        return
    sfx_on, sfx_db = not a.no_sfx, a.sfx_volume
    if a.plan:
        src, dst = a.args[0], a.args[1]; plan = json.load(open(a.plan))
        if isinstance(plan, dict):
            sfx_on = sfx_on and plan.get('sfx', True) is not False; sfx_db = float(plan.get('sfx_volume', sfx_db)); plan = plan.get('effects', [])
    else:
        name, src, dst = a.args[0], a.args[1], a.args[2]
        d = {'fx': name, 'start': a.start or 0.0, 'end': a.end if a.end is not None else 1e9}
        if a.text: d['text'] = a.text
        if a.images: d['images'] = a.images
        for kv in a.opt: k, v = kv.split('=', 1); d[k] = v
        plan = [d]
    for d in plan:
        k_ = d['fx'].lower().lstrip('/').strip(); d['fx'] = ALIASES.get(k_, ALIASES.get(k_.replace(' ', ''), k_.replace('_', '-')))
        if d['fx'] in LOOK_NAMES: d['fx'], look = LOOK_NAMES[d['fx']]; d.setdefault('look', look)
        if d['fx'] not in EFFECTS: sys.exit(f"Unknown effect '{d['fx']}'. Run --list to see all {len(EFFECTS)}.")
    fr, fps, dur, sw, sh = probe(src)
    for d in plan: d['start'] = max(0.0, float(d.get('start', 0))); d['end'] = min(float(d.get('end', 1e9)), dur)
    if sw <= sh: W = a.width; H = int(round(a.width * sh / sw / 2)) * 2
    else: H = a.width; W = int(round(a.width * sw / sh / 2)) * 2
    aw = 540 if sw <= sh else int(round(540 * sw / sh / 2)) * 2; ah = int(round(aw * sh / sw / 2)) * 2
    fxs = [Fx(d, fps) for d in plan]
    if any(f.name in WORD_FX for f in fxs) and (a.words or has_audio(src)):
        import words as words_mod
        allw = json.load(open(a.words)) if a.words else words_mod.load_or_make(src)
        for f in fxs: f.words = [w for w in allw if f.start - 0.05 <= w['s'] < f.end]
    inwin = lambda t: any(f.start - 0.5 <= t < f.end + 0.5 for f in fxs)
    print(f'Pass 1: tracking you ({len(fxs)} effect{"s" * (len(fxs) > 1)})...', flush=True)
    trk = Tracker(aw, ah); masks, faces, thumbs = {}, [], []
    n_thumb = 10; thumb_at = {int(dur * fps * (j + 0.5) / n_thumb) for j in range(n_thumb)}
    for i, fr_ in enumerate(read_frames(src, aw, ah, fr)):
        t = i / fps
        if i in thumb_at: thumbs.append(Image.fromarray(fr_.copy()))
        if inwin(t):
            m, f = trk(fr_, int(t * 1000)); masks[i] = m; faces.append(f)
        else:
            faces.append(None); trk.prev = None
    try: trk.seg.close()
    except Exception: pass
    sm = smooth(faces, fps)
    if sm is None: sm = np.tile([aw / 2, ah * 0.33, aw * 0.15], (len(faces), 1))
    sc = W / aw
    for f in fxs:
        if f.name in CARD_FX: f.cards = load_cards(f.o.get('images'), thumbs)
        rows = sm[max(0, int(f.start * fps)):max(int(f.start * fps) + 1, min(len(sm), int(f.end * fps)))]
        f.med = tuple(float(v) * sc for v in np.median(rows if len(rows) else sm, axis=0))
        tops = []
        for i in range(max(0, int(f.start * fps)), min(len(sm), int(f.end * fps) + 1), 3):
            m = masks.get(i)
            if m is None: continue
            fx_, fy_, fw_ = sm[i]; band = m[:, max(0, int(fx_ - fw_ * 0.35)):int(fx_ + fw_ * 0.35) + 1]
            r = np.nonzero((band > 128).mean(1) > 0.25)[0]
            if len(r) and r[0] < fy_: tops.append(r[0])
        if tops: f.top = float(np.median(tops)) * sc
    stills = sorted({int(round(float(s) * fps)) for s in a.still.split(',')}) if a.still else None
    enc = None
    if not stills:
        cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(fr), '-i', '-', '-i', src]
        import sfx
        evs = [ev for f in fxs for ev in sfx.events(f.name, f.start, f.end, f.o)] if sfx_on else []
        if evs:
            sfx_path = os.path.splitext(dst)[0] + '.sfx.wav'; sfx.write(sfx_path, sfx.track(evs, dur, sfx_db)); cmd += ['-i', sfx_path]
            print(f'Adding {len(evs)} sound effects.', flush=True)
            if has_audio(src):
                cmd += ['-filter_complex', '[1:a:0]aresample=48000,aformat=channel_layouts=stereo[v0];[v0][2:a]amix=inputs=2:duration=first:normalize=0,'
                        'alimiter=limit=0.97:level=disabled[a]', '-map', '0:v', '-map', '[a]']
            else: cmd += ['-map', '0:v', '-map', '2:a']
        else: cmd += ['-map', '0:v', '-map', '1:a:0?']
        enc = subprocess.Popen(cmd + ['-c:v', 'libx264', '-crf', '17', '-preset', 'medium', '-pix_fmt', 'yuv420p',
                                      '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', dst], stdin=subprocess.PIPE)
    print('Pass 2: adding the effects...', flush=True)
    for i, frame in enumerate(read_frames(src, W, H, fr)):
        t = i / fps
        act = sorted([f for f in fxs if f.start <= t < f.end], key=lambda f: f.name == 'captions')  # captions always on top
        if stills is not None and i not in stills:
            if i > stills[-1]: break
            continue
        if act:
            c = Ctx(); c.W, c.H, c.t, c.fps = W, H, t, fps; c.act = {f.name for f in act}; c.cardbot = None
            c.img = frame.astype(np.float32) / 255.0
            m = masks.get(i)
            c.m = cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR).astype(np.float32) / 255.0 if m is not None else np.zeros((H, W), np.float32)
            fx_, fy_, fw_ = sm[min(i, len(sm) - 1)]; c.fx, c.fy, c.fw = fx_ * sc, fy_ * sc, max(fw_ * sc, W * 0.05)
            for f in act:
                c.lt = t - f.start; EFFECTS[f.name][0](c, f)
            frame = (np.clip(c.img, 0, 1) * 255 + 0.5).astype(np.uint8)
        if stills is not None:
            out = dst if len(stills) == 1 else dst.replace('.png', f'_{t:.2f}.png')
            cv2.imwrite(out, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)); print('saved', out)
        else:
            enc.stdin.write(frame.tobytes())
            if i % int(fps * 5) == 0: print(f'  {t:5.1f}s / {dur:.1f}s', flush=True)
    if enc:
        enc.stdin.close(); enc.wait()
        sp = os.path.splitext(dst)[0] + '.sfx.wav'
        if os.path.exists(sp): os.remove(sp)
        print('Done:', dst)


if __name__ == '__main__':
    main()
