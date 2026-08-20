# MiniMax H3 笑話語音小品

Hermes skill：先拆鉤子／鋪墊／包袱／tag，再用本機 ComfyUI MiniMax H3 **T8 speech** 分段出聲；或走 Token Plan 靜幀說書，時長跟旁白走。

Repo 是 **root-level skill**（`SKILL.md` 在根目錄，不是 `skills/<name>/`）。Hub 只拷 `SKILL.md` 會缺 scripts，請用下面的安裝方式。

## Install

裝到目前 profile 的 `skills/media/`（與本機已驗證路徑一致）：

```bash
git clone https://github.com/stevenke1981/minimax-h3-comedy-sketch.git
python minimax-h3-comedy-sketch/scripts/install_skill.py --target-dir "$LOCALAPPDATA/hermes/skills/media" --force
python "$LOCALAPPDATA/hermes/skills/media/minimax-h3-comedy-sketch/scripts/selftest.py"
```

然後 `/reload-skills` 或開新 session。

## Run

ComfyUI 需在 `http://127.0.0.1:8188`。

```bash
python "$LOCALAPPDATA/hermes/skills/minimax-h3-comedy-sketch/scripts/run_comedy_sketch.py" \
  --sketch "$LOCALAPPDATA/hermes/skills/minimax-h3-comedy-sketch/templates/人工服務.json"

python "$LOCALAPPDATA/hermes/skills/minimax-h3-comedy-sketch/scripts/qa_and_assemble.py" \
  --project E:/h3cspeed/output/comedy_kefu_v001
```

預設輸出：`E:\h3cspeed\output\<sketch_id>\`

## Layout

```
SKILL.md
references/joke-structure.md
references/story-stillcut.md
templates/人工服務.json
scripts/run_comedy_sketch.py
scripts/qa_and_assemble.py
scripts/install_skill.py
scripts/selftest.py
```

引擎契約：T8 20-step `dual_clock_euler` / `native_flow` / 64×64。禁止 turbo LoRA。
