---
name: effects
description: aitjb 版影片特效包：37 個口播影片特效、逐字字幕(繁體中文)、音效與自動剪停頓。效果會追蹤講者的臉，可以放在頭後面。Use when the user types /effects, names one of the effects (in English or 中文, e.g. 分身列隊, 報紙頭版, glass-widgets, paper_cut), or asks to add captions, an effect, zoom, sticker, animation or sound effects to a talking-head video, cut the pauses, or edit a talking-head reel.
---

# aitjb 影片特效包：37 個特效、繁中字幕、音效、剪停頓

使用者通常不是工程師。回覆要短、要親切，事情你自己做完，不要叫他們自己跑指令。所有回覆用繁體中文、台灣用語。

下面的路徑都相對於這個 skill 的資料夾(也就是這份 SKILL.md 所在的資料夾)，下指令時用它的絕對路徑。Windows 的 Python 在 `.venv\Scripts\python.exe`，不是 `.venv/bin/python`。

## 1. 第一次使用：安裝(只要一次)
執行 `bash scripts/setup.sh`，看到 `READY` 就好了(第一次大約 1 到 3 分鐘)。
- 出現 `NEED_FFMPEG`：幫他們裝。Mac：`brew install ffmpeg`(沒有 `brew` 就請他們先到 brew.sh 裝 Homebrew)。Windows：`winget install ffmpeg`。
- 出現 `NEED_PYTHON`：裝 Python 3.12(Mac：`brew install python@3.12`，Windows：`winget install Python.Python.3.12`)，再跑一次 setup。
- 接著執行 `.venv/bin/python scripts/fx.py --profile`。如果顯示 `not set yet`，問一次他們的名字和 IG 帳號，然後存起來：`.venv/bin/python scripts/fx.py --profile "名字" "@帳號"`。有個人資料卡的效果會用到。

## 2. 弄清楚他們要什麼
- 影片：使用者把檔案拖進對話，或給路徑。直式手機影片效果最好，頭頂要留一點空間。
- 單一效果：`/effects 分身列隊 從 3 到 6 秒` 或 `/effects clone-row from 3 to 6`，只做這一個。
- 字幕：「加字幕」或 `/effects captions`，整支影片跑 `captions`，預設樣式 `clean`，除非他們選 `bold`、`pill` 或 `grey`。
- 剪停頓：「剪掉停頓」「跳剪」「把空白剪掉」→ 第 3 步。
- 整支剪：「幫我剪」「做成 reel」`/effects full edit` → 下面的整支剪流程。
- 中文名、英文名、底線寫法(`paper_cut`)都可以，照下面的表對應。不確定就把清單給他們看。

## 3. 剪停頓(他們要求或整支剪時才做)
`.venv/bin/python scripts/trim.py <影片> <影片名>_trim.mp4`，之後都用剪好的檔案。它會在句子之間留一口氣的空檔，保持原本語速(他們要更快才加 `--speed 1.1`)。告訴他們省了多少秒。
這步要最先做：如果他們給的秒數是原始影片的，除非他們要求，不要剪，因為剪完之後所有時間都會跑掉。

## 4. 找字(時間點和字幕)
`.venv/bin/python scripts/words.py <影片>` 會印出每個字和它的時間，存成 `<影片>.words.json`。
- 中文口白會自動轉成台灣繁體。語言偵測錯了，可以設 `WHISPER_LANG=zh` 再跑一次。
- 用在「講到 X 的時候」「當我說⋯⋯」。
- `captions` 和 `halftone-paper` 需要它(檔案不存在時 fx.py 會自己跑)。
- 讀一遍逐字稿，在 `.words.json` 裡修正聽錯的品牌名和數字(「克勞德扣」→「Claude Code」)，每個字保持一筆。
- 每個效果短一點最好看：1.5 到 4 秒。

## 5. 寫計畫、檢查、輸出
1. 在影片旁邊寫計畫 `<影片名>_effects.json`：
   ```json
   {"effects": [
     {"fx": "press-front", "start": 0.0, "end": 2.2, "text": "AI 取代剪輯師？"},
     {"fx": "split-graph", "start": 4.0, "end": 6.5, "text": "1月|2月|3月", "to": "12|30|58"},
     {"fx": "captions", "style": "clean", "keywords": "Claude|特效"}
   ]}
   ```
   `captions` 不用寫 start 和 end，會跑整支。
2. 先檢查畫面(很快)：`.venv/bin/python scripts/fx.py --plan <plan.json> <影片> <資料夾>/check.png --still 1.2,5.0`，取每個效果的中間秒數。自己看這些 PNG。有問題就改文字、時間或選項(蓋到臉、被邊緣切到、看不清楚、兩個東西搶同一個位置)。
3. 輸出：`.venv/bin/python scripts/fx.py --plan <plan.json> <影片> <影片名>_effects.mp4`。會保留原聲，效果出現時加上輕微音效(`--no-sfx` 不要音效，`--sfx-volume -4` 小聲一點，或在計畫裡寫 `"sfx": false`)。預設 1080p，要 4K 加 `--width 2160`(比較慢)。
4. 告訴他們檔案在哪裡。用一句話提醒：發布前先自己看一遍，你只是打草稿，他們才是拍板的人。

單一效果不用寫計畫：`.venv/bin/python scripts/fx.py clone-row <影片> <輸出.mp4> --start 3 --end 6 --text "..." --opt key=value`。

## 整支剪流程(aitjb 節奏)
1. 剪停頓(第 3 步)。抓字(第 4 步)並修正品牌名。
2. 開字幕，樣式 `clean`；`keywords` 放產品名、數字、和畫面上正在示範的動作。
3. 每 2 到 4 秒一個效果，每個 1.5 到 4 秒，對準講出來的那個字：
   - 開場鉤子(前 2 秒)：`press-front`、`impact-frame` 或 `blade-slice`。
   - 講「它做了什麼」：`ui-world`、`phone-mockup`、`live-cursor`。清單：`checklist`、`apple-toggles`、`sketch-words`。數字：`split-graph`、`chart-grow`、`liquid-glass-graph`。
   - 重點句：`glass-type`、`red-collage`、`led-sign`、`spotlight`。
   - 換話題：`paper-tear`、`letter-dive`、`rabbit-hole`、`frame-break`。
   - 收尾：`blow-away` 或 `clone-row`。
4. 不要同時疊兩個大效果。下半部有卡片時，字幕會自己讓開。
5. 音效保持開啟：輕的 pop 和 tick，不要每個轉場都 whoosh。
6. 提到品牌時，品牌官方 logo 要出現在畫面上(引擎內建 `logo-link`，見最下面)。

## aitjb 的 37 個效果

### 來自 vol.15
| # | `fx` 名稱 | 中文名 | 效果 | 選項(都可省略) |
|---|---|---|---|---|
| 1 | `split-graph` | 彈跳長條圖 | 螢光長條圖在頭頂上方彈跳長高 | `text`(標籤，用 `\|` 分隔)、`to`(數字，用 `\|`)、`title` |
| 2 | `orbit` | 繞頭轉圈 | 你的照片或影片繞著頭轉 | `images`(資料夾)、`count`、`speed`、`size` |
| 3 | `timeline` | 剪輯時間軸 | 暗紅底片調加上剪輯時間軸和播放頭 | `text`(標題)、`sub`、`tc` |
| 4 | `apple-toggles` | 設定開關 | iPhone 設定開關一行一行打開 | `text`(每行用 `\|`)、`ticks`(秒數用 `\|`)、`color` |
| 5 | `glass-widgets` | 透明面板 | 毛玻璃小工具一片片浮在臉旁邊 | `text`(大數字)、`sub`、`name`、`handle`、`look=simple` |
| 6 | `check-pills` | 勾選按鈕 | 方格紙房間，游標一顆顆按下藍色按鈕 | `text`(按鈕用 `\|`)、`images`、`board` |
| 7 | `rabbit-hole` | 隧道 | 畫面像隧道一樣轉進去 | `ratio`、`speed`、`spin` |
| 8 | `red-collage` | 紅色拼貼 | 黑白的你，身後一個大紅字，三行字砸進來 | `text`(紅字)、`lines`(用 `\|`)、`tag` |
| 9 | `carousel-spin` | 旋轉木馬 | 照片像旋轉木馬一樣轉，然後停住 | `images`、`count`、`size`、`turns` |
| 10 | `liquid-glass-graph` | 玻璃圖表 | 液態玻璃卡片裡，折線往上長、數字往上跳 | `text`(標籤)、`from`、`to`(例 `59%`)、`color`、`look=bento` |
| 11 | `checklist` | 待辦清單 | 下巴下方的任務清單一項項打勾 | `text`(`項目::註記\|...`)、`title` |
| 12 | `led-sign` | LED 看板 | 燈暗下來，身後的 LED 看板打出字 | `text`(每行用 `\|`)、`color`、`push` |
| 13 | `match-cut` | 新聞切換 | 新聞頁面一直換，紅框裡的字留在原位 | `text`(關鍵字，預設 Claude)、`color` |
| 14 | `over-the-shoulder-zoom` | 肩後拉近 | 鏡頭推到一角出現圖表，再推到另一角出現第二張 | `text`(兩個標籤用 `\|`)、`to`(兩個數字用 `\|`)、`zoom` |
| 15 | `spotlight` | 發光字 | 房間變暗，你身後的字發光 | `text`、`color`、`push`；`glitter-spotlight` 是金色版 |

### 來自 vol.10(和上面重複的 `orbit`、`carousel-spin` 不再列)
| # | `fx` 名稱 | 中文名 | 效果 | 選項 |
|---|---|---|---|---|
| 16 | `ui-world` | 聊天畫面 | 白色聊天視窗從上方降下，一張圖飛進輸入框 | `text`(打的字)、`ask`、`reply`、`title`、`images` |
| 17 | `phone-mockup` | 手機模型 | 大手機從側邊飛進來，按鈕被按下 | `text`(按鈕)、`title`、`sub`、`at`(第幾秒按下) |
| 18 | `glass-type` | 玻璃字 | 透明玻璃立體字站在身後，光線劃過 | `text` |
| 19 | `chart-grow` | 發光折線 | 發光的線往右上長，最後跳出大數字 | `to`(例 `+320%`)、`text`(標籤)、`color` |
| 20 | `paper-cut` | 剪紙拼貼 | 紙片疊在一起、你變成貼紙，用定格動畫的節奏動 | `text`(剪報字) |
| 21 | `messages` | 訊息通知 | iPhone 訊息通知從下面一則則疊上來 | `text`(每則用 `\|`)、`title`、`y` |
| 22 | `doodle-boil` | 蠟筆塗鴉 | 蠟筆線條圍著你，一直抖動 | `text`(上方的字)、`color`、`color2` |
| 23 | `headline-wall` | 標題牆 | 標題卡依序貼在你身後，最後跳出總數 | `text`(`標題::註記\|...`)、`total`、`label` |
| 24 | `cover-story` | 雜誌封面 | 大刊名從下方浮上來，畫面變成雜誌封面 | `text`(刊名)、`issue`、`lines`(用 `\|`)、`price`、`color` |
| 25 | `frame-break` | 衝出手機 | 影片縮進手機螢幕，肩膀以上衝出畫面 | `color`(背景色) |

### 來自 vol.003
| # | `fx` 名稱 | 中文名 | 效果 | 選項 |
|---|---|---|---|---|
| 26 | `clone-row` | 分身列隊 | 身後左右各排出 3 個分身，最後被吸回你身上 | `count`(每邊幾個，預設 3)、`gap` |
| 27 | `code-body` | 程式碼身體 | 一道光由上往下掃，身體變成綠色程式碼 | `text`(用哪些字元)、`color`、`cell` |
| 28 | `letter-dive` | 文字俯衝 | 奶油色紙上一個字一個字打出來，鏡頭飛進字裡變回影片 | `text`(預設「剪輯。」) |
| 29 | `blade-slice` | 斬擊切片 | 白光斜斜劃過，畫面從嘴巴高度錯開再合回來 | `angle`、`shift` |
| 30 | `press-front` | 報紙頭版 | 整個畫面變成報紙頭版，你在網點黑白照片裡說話 | `text`(頭條)、`sub`、`date` |
| 31 | `head-stack` | 頭頂疊標籤 | 白色標籤掉下來疊在頭上和肩膀旁，最後崩塌 | `text`(標籤用 `\|`)、`every` |
| 32 | `banknote` | 紙鈔 | 你變成紙鈔風格的鈔票(虛構設計，不是真鈔) | `text`(券名)、`value`、`words`、`serial`、`color` |
| 33 | `live-cursor` | 即時游標 | 掛 Claude 名牌的游標出現，連框把你拖到旁邊再放回來 | `text`(名牌)、`color`、`dist`、`plate`(沒有人的同一張畫面) |
| 34 | `paper-tear` | 撕報紙 | 報紙頭版從中間撕開往左右飛走，露出你 | `text`(頭條)、`sub`、`at` |
| 35 | `impact-frame` | 漫畫衝擊格 | 黑白漫畫格加集中線和大字，背景黑白一直反轉 | `text`(預設「衝擊！」)、`rate` |
| 36 | `blow-away` | 隨風消散 | 身體從左邊化成沙粒往左飄走，最後只剩空椅子 | `dir`(`left` 或 `right`)、`span`、`plate`(沒有人的同一張畫面，例如空椅子) |
| 37 | `sketch-words` | 鉛筆手寫字 | 背景變成奶油色紙，身後一行行出現鉛筆手寫字 | `text`(每行用 `\|`) |

### 字幕和其他
| `fx` 名稱 | 效果 | 選項 |
|---|---|---|
| `captions` | 逐字字幕，中文自動按字數斷句、中英之間留空格。`clean`：白字、關鍵字用金色襯線。`bold`：一次一小段大字、黃色關鍵字。`pill`：深色底條。`grey`：灰色小字幕 | `style`、`keywords`(用 `\|`)、`hide`(`3.5-6\|20-22`)、`y`(0 到 1) |

引擎裡還有其他效果可以用(例如 `pop-word`、`logo-link` 真品牌 logo、`card-drop`、`halftone-paper`、`reject-stamp`、`lean-in`)，不在 aitjb 的 37 個清單裡，但使用者點名時照樣能用。執行 `.venv/bin/python scripts/fx.py --list` 看全部。

## 繁體中文
- 畫面上的字只要有中文，就會自動換成對應的繁中字體：粗黑體 → 思源黑體 Black、襯線 → 思源宋體、手寫 → 霞鶩文楷。不用另外設定。
- 引擎原本的效果，預設文字已改成繁中；使用者給的文字永遠優先。要英文預設可以加 `"lang": "en"`。
- 文字用台灣用語(影片、軟體、剪輯、品質)，不要用大陸用語(視頻、軟件、剪接師)。

## aitjb 品牌設定
- 預設色：萊姆綠 `#CDF51C` × 電光粉 `#FF2E93`(新效果的圖表、塗鴉、封面重點字)。要換色就用 `color`。
- 不要膠囊形標籤、不要畫出來的底線和分隔線(`check-pills` 的藍色按鈕是效果本身，例外)。
- 手寫字體只用在 `sketch-words`。

## 規則
- 不要蓋到臉。東西要嘛在頭後面，要嘛自己避開臉；檢查畫面時如果字還是壓到臉，就移動它(`x`、`y`)或縮短文字。
- 效果照列出的順序跑。重疊時把鏡頭類效果(`lean-in`、`spotlight`、`blade-slice`、`frame-break`)放前面。字幕永遠最後畫、在最上層。
- 縮放不超過 2 倍，畫質才不會糊。
- 圖表、計數器、頭條要用使用者真實的數字。不知道就問，不要自己編。
- `blow-away`、`live-cursor` 會把你從畫面拿掉。使用者有給「同一個畫面但沒有人」的圖(例如空椅子)，就用 `plate=圖檔路徑`；沒有的話，空出來的背景是用演算法補的，會偏模糊，背景越單純越好。
- `banknote` 只做虛構的紙鈔風設計，不要照著任何真實貨幣畫。
- 音效是用程式產生的(沒有音檔)。不會加背景音樂。
- 這些都是草稿。如果使用者拿去比對他們看過的 reel，老實說手工調整的節奏和音效設計可以做得更細。
