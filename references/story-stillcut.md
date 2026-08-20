# 說書靜幀片（聊齋／3～10 分鐘）

90 秒是一個 bit。3～10 分鐘是說書：鉤子還在，但中間要有張力曲線，時長跟旁白走。

已驗證成品：《畫皮》10 分 53 秒，36 切，角色卡鎖臉，Telegram 交付。

## 何時走這條路

- 主人說聊齋、說書、大約 N 分鐘、不用硬切
- 要多切畫面、角色一致、情緒高低聽得出來
- 不要用 H3 20-step 去扛 10 分鐘（太慢）

本機根目錄：`E:\MoneyPrinterTurbo`

- 稿：`docs/liaozhai_huapi.json`、`docs/liaozhai_sketches.json`
- 產線：`scripts/make_liaozhai.py`、`scripts/make_huapi.py`、`scripts/assemble_huapi.py`
- Token Plan：`docs/token-plan.md`（新加坡 OpenAI 相容，`qwen3.8-max` + `qwen-image-3.0-pro`）
- `config.toml` 已 gitignore，不要提交 Key

## 說書結構（不是硬切 10 分鐘）

| 段 | 作用 | 畫皮例 |
|---|---|---|
| 鉤子 | 生活化問句，8 秒內進場 | 漂亮到不正常、好到不敢問第二句 |
| 日常 | 聽眾認得自己 | 日子過得很平順，所以開始找刺激 |
| 誤導 | 對方太懂事、太好看 | 她安靜得不像客人 |
| 警告 | 有人提醒，主角當笑話 | 道士講得很明白，他用嘲笑蓋住害怕 |
| 證實 | 窗縫／掀皮，預期翻轉 | 燈下那張皮 |
| 後果 | 代價比鬼臉貴 | 妻子去贖 |
| callback | 回收鉤子，接到現在 | 這張皮下面還有沒有別的東西 |

一次一個前提。10 分鐘仍然只有一個觀察，不要中途換題。

## 用詞（已踩過的坑）

不要把形容詞縮成單詞標籤。聽的人要聽到完整說法。

| 弱 | 改 |
|---|---|
| 日子過得平 | 日子過得很平順 |
| 臉色很白 | 臉色很白皙 |
| 聲音很輕 | 聲音很輕柔 |
| 她很安靜 | 安靜得不像客人 |
| 他們酸 | 酸得沒必要 |
| 講得很白 | 講得很明白 |
| 寫得很乾 | 寫得很乾脆 |
| 比兇還難擋 | 比兇狠還難擋 |
| 說她好冷 | 冷得受不了 |
| 腿是軟的 | 腿軟得站不穩 |

## 產線順序

1. 寫 `beats[]`：每句 `text` + `emotion` + `shot`。漢字量約 250／分鐘（含停頓）。10 分鐘約 2400～2600 字。
2. 角色卡：每人一張灰底半身，再當 i2i 參考。參考圖先縮到 512，避免 Timeout。
3. TTS：`zh-TW-YunJheNeural`，依情緒改 rate／pitch。驚／痛／難過要聽得出來。
4. 停頓依情緒：shock 0.72s、tense 0.62s、warm 0.42s。不要平均切畫面。
5. 組裝：每張靜幀時長 = 對應 beats 的語音總和。Ken Burns。字幕 Microsoft YaHei。
6. Telegram：壓到約 40MB 再 `sendVideo`。`hermes send MEDIA:` 在 CLI 常失敗，改 curl Bot API。檔案先拷到 `%LOCALAPPDATA%/hermes/audio_cache/`。

```bash
cd /e/MoneyPrinterTurbo
python scripts/make_huapi.py --stage tts
python scripts/make_huapi.py --stage id
python scripts/make_huapi.py --stage images --from-shot 1 --to-shot 18
# 可並行另一路 19–36
python scripts/assemble_huapi.py
```

圖已存在就跳過。API 逾時就單張重跑，不要整批重來。

## 畫面

- 每則至少 12～14 切；10 分鐘約 32～36 切
- 主角鎖臉優先，配角（妻子）也要角色卡，否則會漂
- 字幕黑底不要蓋滿臉；FontSize 16、MarginV 80 是目前可用值

## 交付

- 成片絕對路徑 + ffprobe 時長
- Telegram 是否送出
- 用詞修正表（若這輪有改旁白）
- 已知落差（哪一鏡漂了、字幕是否擋臉）
