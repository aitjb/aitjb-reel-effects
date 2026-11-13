#!/usr/bin/env python3
"""Make assets/preview.jpg: one still of every aitjb effect on your own clip, in a labelled grid.

usage: python preview.py your_clip.mp4 [--at 1.2] [--out assets/preview.jpg]
The clip should be a vertical talking-head video at least 2.5 seconds long.
"""
import argparse, os, subprocess, sys, tempfile
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
MENU = [('split-graph', '彈跳長條圖'), ('orbit', '繞頭轉圈'), ('timeline', '剪輯時間軸'), ('apple-toggles', '設定開關'),
        ('glass-widgets', '透明面板'), ('check-pills', '勾選按鈕'), ('rabbit-hole', '隧道'), ('red-collage', '紅色拼貼'),
        ('carousel-spin', '旋轉木馬'), ('liquid-glass-graph', '玻璃圖表'), ('checklist', '待辦清單'), ('led-sign', 'LED 看板'),
        ('match-cut', '新聞切換'), ('over-the-shoulder-zoom', '肩後拉近'), ('spotlight', '發光字'), ('ui-world', '聊天畫面'),
        ('phone-mockup', '手機模型'), ('glass-type', '玻璃字'), ('chart-grow', '發光折線'), ('paper-cut', '剪紙拼貼'),
        ('messages', '訊息通知'), ('doodle-boil', '蠟筆塗鴉'), ('headline-wall', '標題牆'), ('cover-story', '雜誌封面'),
        ('frame-break', '衝出手機'), ('clone-row', '分身列隊'), ('code-body', '程式碼身體'), ('letter-dive', '文字俯衝'),
        ('blade-slice', '斬擊切片'), ('press-front', '報紙頭版'), ('head-stack', '頭頂疊標籤'), ('banknote', '紙鈔'),
        ('live-cursor', '即時游標'), ('paper-tear', '撕報紙'), ('impact-frame', '漫畫衝擊格'), ('blow-away', '隨風消散'),
        ('sketch-words', '鉛筆手寫字')]
# a moment inside each effect that shows it best (seconds from the effect start)
SHOW = {'letter-dive': 0.55, 'paper-tear': 0.6, 'blow-away': 0.9, 'clone-row': 0.9, 'code-body': 0.9, 'blade-slice': 0.35,
        'frame-break': 1.3, 'head-stack': 1.4, 'sketch-words': 1.8, 'ui-world': 1.5, 'chart-grow': 1.4, 'phone-mockup': 1.4}
EXTRA = {'spotlight': ['--text', '發光字']}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('clip'); ap.add_argument('--out', default=os.path.join(ROOT, 'assets', 'preview.jpg'))
    ap.add_argument('--start', type=float, default=0.0); ap.add_argument('--cols', type=int, default=8)
    a = ap.parse_args(); py = sys.executable; tmp = tempfile.mkdtemp(); tiles = []
    for i, (fx, zh) in enumerate(MENU):
        t = a.start + SHOW.get(fx, 1.2); out = os.path.join(tmp, f'{i:02d}.png')
        cmd = [py, os.path.join(ROOT, 'scripts', 'fx.py'), fx, a.clip, out, '--start', str(a.start), '--end', str(a.start + 2.4),
               '--width', '540', '--still', f'{t:.2f}', '--no-sfx'] + EXTRA.get(fx, [])
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode or not os.path.exists(out): print('skipped', fx, r.stderr[-300:]); continue
        print(f'{i + 1:2d}/{len(MENU)} {fx}', flush=True); tiles.append((Image.open(out).convert('RGB'), i + 1, zh))
    import fx as F
    tw = 270; th = int(tw * tiles[0][0].height / tiles[0][0].width); lab = 46; gap = 8; cols = a.cols; rows = -(-len(tiles) // cols)
    head = 150; W = cols * tw + (cols + 1) * gap; H = head + rows * (th + lab) + (rows + 1) * gap
    sheet = Image.new('RGB', (W, H), (16, 16, 18)); d = ImageDraw.Draw(sheet)
    d.text((gap * 3, 30), 'aitjb 影片特效包', font=F.font('tc', 64), fill=F.LIME)
    d.text((gap * 3, 104), f'{len(tiles)} 個口播特效 · 繁中字幕 · 音效 · 剪停頓   by @ai_tjb', font=F.font('tcm', 30), fill=(235, 235, 235))
    for k, (im, n, zh) in enumerate(tiles):
        r_, c_ = divmod(k, cols); x = gap + c_ * (tw + gap); y = head + gap + r_ * (th + lab + gap)
        sheet.paste(im.resize((tw, th), Image.LANCZOS), (x, y))
        d.text((x + 6, y + th + 8), f'{n:02d}', font=F.font('mono', 26), fill=F.LIME)
        d.text((x + 50, y + th + 6), zh, font=F.font('tcm', 28), fill=(240, 240, 240))
    sheet.save(a.out, quality=88); print('saved', a.out)


if __name__ == '__main__':
    main()
