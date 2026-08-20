---
name: minimax-h3-comedy-sketch
description: Use when making comedy/story voice sketches with hook, punch, still-cut.
version: 1.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [minimax-h3, comedy, sketch, punchline, hook, t8-speech, comfyui, liaozhai, storytelling]
    related_skills: [minimax-h3-speech, asr, ffmpeg-editing, comfyui, story-voice-video-pipeline]
    category: media
---

# MiniMax H3 笑話語音小品

Use when 主人要「笑話小品」「語音段子」「90 秒小品」「聊齋說書」「用 MiniMax H3 / ComfyUI 講笑話」，或要把笑點拆成鉤子／鋪墊／包袱再出聲。

兩條已驗證的路：

1. **H3 T8 語音小品**：分段人聲 + FFmpeg 組裝。人聲可懂優先於畫面。
2. **說書靜幀片**：Token Plan 出圖 + 情緒 TTS + 時長跟旁白走。見 `references/story-stillcut.md`。

不是 Turbo 720p 口型片。

## When to Use

- 指定時長（例如 1 分 30 秒）的語音小品／廣播短劇
- 3～10 分鐘說書小品（聊齋、生活荒謬），時長跟旁白，不要硬切
- 要先拆笑點／張力再生成，不要直接讓模型「自己搞笑」
- 引擎是本機 Comfy `E:\minimax-h3\ComfyUI` 的 MiniMax H3 T8，或 `E:\MoneyPrinterTurbo` 靜幀產線

不要用 H3 這條路：要 720p 說話頭、要 Turbo 4-step、或只要純文字段子。畫面走 `minimax-h3-speech` 的 Ref2VA；人聲走這裡。說書＋多切靜幀走路徑 2。

## Host map

- Comfy: `E:\minimax-h3\ComfyUI`，預設 `http://127.0.0.1:8188`
- 啟動：`E:\minimax-h3\.venv\Scripts\python.exe E:\minimax-h3\ComfyUI\main.py --listen 127.0.0.1 --port 8188 --fp16-vae --cache-none --fast-disk --disable-xformers --use-sage-attention --lowvram`
- T8 合約：`custom_nodes/comfyui-minimax-h3-audio-T8/speech.py` → `build_speech_prompt()`
- 驗證過的圖：`MiniMaxH3AudioConditioningT8` + `dual_clock_euler` / `native_flow` / 20 steps / 64×64
- Runner：`scripts/run_comedy_sketch.py`
- 範例小品：`templates/人工服務.json`

## 流程（不要跳）

### 0. Comfy 活著再寫稿

```bash
curl -s http://127.0.0.1:8188/system_stats
```

沒回應就先啟動上列 main.py，等到 log 出現 `http://127.0.0.1:8188`。

### 1. 先拆笑點，再寫台詞

完整結構與社群例子見 `references/joke-structure.md`。紙面上必須填這張表，才能進 T8：

| 欄位 | 作用 | 90 秒預算 |
|---|---|---|
| 前提 premise | 一個觀察，不是一個笑 | 寫在 metadata，不要唸出來 |
| 鉤子 hook | 前 8 秒抓住聽眾；具體、自信 | 0:00–0:08 |
| 鋪墊 setup | 安裝預期；鋪墊裡不要搶笑 | 0:08–0:35 |
| 三的法則 | 前兩項正常、第三項翻轉 | 0:35–1:00 |
| 包袱 punch | 推翻預期；好笑的詞放句末 | 1:00–1:18 |
| tag | 騎在笑聲上的第二擊；可省略 | 1:18–1:24 |
| callback | 回收開頭鉤子 | 1:24–1:30 |

硬規則：

1. **鋪墊裡零笑話。** 提前洩壓，後面的包袱會啞。
2. **一次一個前提。** 90 秒不要換題。
3. **三的法則每段最多一次。** 用第二次，觀眾會預判翻轉。
4. **好笑的詞靠句末。** 「差別在哪」弱；「本系統不支援道歉功能」才是落點。
5. **硬 tag 比沒 tag 更糟。** 包袱乾淨就進 callback。
6. **良性違規。** 違反常理，但聽眾心理安全（客服荒謬可以；傷害弱勢不行）。
7. **鉤子要生活化。** 「欸你有沒有遇過那種人」比「本篇講述……」強。不要講義腔。
8. **不要只用單詞。** 「很平」改「很平順」；「臉色很白」改「臉色很白皙」；「講得很白」改「講得很明白」。聽的人要聽到完整說法。
9. **時長跟旁白走。** 主人說「大約 N 分鐘、不用硬切」＝旁白多長片子就多長。不要 pad 或砍包袱去湊整點。

### 2. 依 T8 切段（一人一段）

H3 單段對齊 124–362 幀 @ 24 fps ≈ **5.2–15.1 秒**。超過就再切。

- 一個 clip 只有 **一個 speaker**、一個 `<d>[Chinese] …</d>`
- 口語、短句。單段漢字 roughly ≤ 40 字
- 方向／情緒寫在 prompt 的 acting 欄，**不要寫進對白**
- 兩人小品用左右聲道在組裝時再分，不在同一 T8 pass 搶聲

預估秒數：`ceil(字數 / 4.5) + 3` 秒 rec room，再夾進 6–15 秒。

### 3. 用官方 T8 契約出聲

只准這條圖（已在 runner 寫死）：

- UNET `minimax_h3_fl2va_pruned_int8_convrot` + Qwen CLIP + video/audio VAE
- `MiniMaxH3AudioConditioningT8`：`T2VA`、`audio_mode=native`、`audio_denoise_strength=1.0`、64×64
- `MiniMaxH3DualClockSamplerT8`：20 steps、`dual_clock_euler`、`native_flow`、shift 12/3
- `MiniMaxH3SpeechDecodeT8` → `SaveAudio`
- `overall_soundscape` 只准 room tone；`non_diegetic_music: N/A`

禁止：`MiniMaxH3TurboSampler`、任何 `ref2v`/`fl2v` turbo LoRA、720p 畫布、雨聲古琴與對白同 pass。

```bash
python C:/Users/steven/AppData/Local/hermes/skills/media/minimax-h3-comedy-sketch/scripts/run_comedy_sketch.py \
  --sketch C:/Users/steven/AppData/Local/hermes/skills/media/minimax-h3-comedy-sketch/templates/人工服務.json \
  --from-segment 1
```

預設輸出：`E:\h3cspeed\output\<sketch_id>\`

3070 Ti 8GB：一段 20-step 約 5–6 分鐘。8 段小品約 40–50 分鐘。一次一段，`--resume` 可續跑。

### 4. QA 再組裝

每段都要過 `minimax-h3-speech` 的表：

1. `ffmpeg -af volumedetect`：mean 不該 ≤ -50 dB，peak 不該 0.0 dB
2. ASR（`asr` skill，`-l zh`）對 `<d>` 原文。近音（取消→取削）= 音素糊，重跑該段，不要先怪 mux
3. 全部過關才組裝（先剪頭尾氣口、段間預設 0.92 秒、loudnorm）：

```bash
python C:/Users/steven/AppData/Local/hermes/skills/media/minimax-h3-comedy-sketch/scripts/qa_and_assemble.py \
  --project E:/h3cspeed/output/comedy_kefu_v001
```

目標約 90 秒時，88–95 秒即可。主人若說「不用硬切」，以旁白時長為準，不要為了 90 秒去砍包袱。太短：加大 `--gap`（預設 0.92）或加 tag。太長且主人要卡 90 秒：縮 gap，不要剪包袱落點。修剪只去頭尾靜音，禁止 `stop_periods=1`（會把句中換氣剪成 0.3 秒）。峰值 0.0 dB 但 ASR 對得上 = 大聲削波，組裝時 `alimiter` + `loudnorm`，不必整段重跑。

### 5. 交付

- 對白稿 + 笑點表
- 各段 WAV + 最終 WAV 絕對路徑
- ASR 對照表（原文／聽寫／判定）
- 時長

CLI 沒有附件通道：只報絕對路徑。Telegram 才複製到 `%LOCALAPPDATA%/hermes/audio_cache/`。

## Decision tree

| 主人說 | 做什麼 |
|---|---|
| 做 90 秒笑話小品 | 本 skill H3 全流程 |
| 3～10 分鐘說書／聊齋 | `references/story-stillcut.md`，時長跟旁白 |
| 只要拆笑點、不要出聲 | 只做步驟 1，停 |
| 人聲聽不清／沒聲音 | 改載 `minimax-h3-speech` |
| 要畫面＋口型 | T8 人聲完成後另開 Ref2VA，FFmpeg mux |
| 要多切靜幀＋鎖臉 | 路徑 2，不要硬套 90 秒 |
| 換題材重做 | 新 JSON + 新 `sketch_id`，舊段不要混 |

## Pitfalls

1. **讓模型「自由發揮好笑」。** 沒有紙上包袱就沒有可驗的笑點。
2. **一段塞兩人對答。** T8 described voice 一次一個 S1。
3. **對白裡寫「用甜美的聲音說」。** 模型會把指示唸出來。
4. **長文言、繞口令、四字堆疊。** 已驗證會糊成諧音。口語短句。
5. **Turbo 搶時間。** 有能量沒音素。小品比詩詞更不能糊。
6. **用 SNL／春晚時長套 90 秒。** 春晚小品 10+ 分鐘；90 秒是一個 bit，不是一齣戲。
7. **解釋包袱。** 寫手共識：解釋笑話 = 殺笑話。tag 是新角度，不是註解。
8. **講義腔鉤子。** 「本篇講述……」比「欸你有沒有聽過」弱。
9. **單詞描寫。** 「很平／很白／很輕／很乾」聽起來像標籤。改完整說法。
10. **硬切整點分鐘。** 主人說大約 N 分鐘＝旁白決定時長。

## Verification

- [ ] 笑點表七欄填完，鋪墊沒有提前笑
- [ ] 鉤子是口語、具體，不是講義
- [ ] 旁白沒有單詞標籤（平／白／輕／乾／兇單獨當形容）
- [ ] 每段 1 speaker、≤40 字、5.2–15.1 秒窗（H3 路徑）
- [ ] 圖是 T8 20-step dual_clock，沒有 turbo LoRA（H3 路徑）
- [ ] 每段 volumedetect + ASR 對得上原文
- [ ] 90 秒任務：成片 88–95 秒。說書任務：時長 ≈ 旁白，沒硬切
