# -*- coding: utf-8 -*-
import os
import json
import base64
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.scrolledtext import ScrolledText
from importlib import resources as ir

# ===== 尝试加载 Pillow（仅用于缩略图预览）=====
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

# ------- HTTP -------
import requests

# ======== 内置常量 / 模型 ========
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL_SLOW_DEFAULT = "deepseek-reasoner"
MODEL_FAST = "deepseek-chat"  # 用于提取两个脚本（你要求 deepseek-chat）
MODEL_QWEN_TEXT = "qwen-text"
QWEN_TEXT_DEFAULT = "qwen-plus"
QWEN_VL_DEFAULT = "qwen-vl-max"

DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DASHSCOPE_CHAT_COMPLETIONS_URL = f"{DASHSCOPE_BASE_URL}/chat/completions"

# ======== API KEY（环境变量或直接填）========
DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "").strip()
API_KEY_HERE = os.environ.get("API_KEY_DEEPSEEK", "").strip()

# ======== UI 样式 ========
FONT_SIZE = 16

# ======== 头部与固定提示 ========
HEAD_STR = "Please generate two complete scripts according to the following description and instruction. Default names: genDB.py and DSA_SIM.py."
IMG_FIXED_PROMPT = "Please describe the obstacles, simulation box, and simulated molecules in the picture."

# ======== 包内资源访问 ========
def _resource_path(name: str) -> str:
    """把包内 autosim.data/<name> 提取为临时文件路径，用于需要文件路径的 API（如 PhotoImage）"""
    with ir.as_file(ir.files("autosim.data").joinpath(name)) as p:
        return str(p)

def _resource_text(name: str, encoding="utf-8") -> str:
    data = ir.files("autosim.data").joinpath(name).read_bytes()
    return data.decode(encoding, errors="replace")

# 文件名常量（对外创建的实际输出）
GEN_FILE = "genDB.py"
SIM_FILE = "DSA_SIM.py"

# ================= DeepSeek =================
def _probe_ds_key() -> str:
    return (API_KEY_HERE or os.environ.get("DEEPSEEK_API_KEY", "")).strip()

def ds_chat_once(content: str, model: str, temperature: float = 0.3, timeout: int = 120) -> str:
    key = _probe_ds_key()
    if not key:
        raise RuntimeError("DeepSeek API Key not configured.")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    data = {"model": model, "messages": [{"role": "user", "content": content}], "temperature": temperature}
    r = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=timeout)
    r.raise_for_status()
    j = r.json()
    return (j.get("choices", [{}])[0].get("message", {}).get("content", "") or "").strip()

# ================= Qwen (DashScope via OpenAI-compat) =================
def _dashscope_headers():
    api_key = (DASHSCOPE_API_KEY or os.environ.get("DASHSCOPE_API_KEY", "")).strip()
    if not api_key:
        raise RuntimeError("DashScope API Key not configured.")
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

def qwen_chat_once(content: str, text_model_name: str = QWEN_TEXT_DEFAULT, temperature: float = 0.3) -> str:
    payload = {"model": text_model_name, "messages": [{"role": "user", "content": content}], "temperature": temperature}
    r = requests.post(DASHSCOPE_CHAT_COMPLETIONS_URL, headers=_dashscope_headers(), json=payload, timeout=120)
    r.raise_for_status()
    j = r.json()
    try:
        return (j["choices"][0]["message"]["content"] or "").strip()
    except Exception:
        return json.dumps(j, ensure_ascii=False)

def _file_to_data_url(image_path: str) -> str:
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Image Not Found: {image_path}")
    with open(image_path, "rb") as f:
        img_bytes = f.read()
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    ext = os.path.splitext(image_path)[1].lower()
    mime = "image/jpeg"
    if ext in [".png"]: mime = "image/png"
    elif ext in [".webp"]: mime = "image/webp"
    elif ext in [".bmp"]: mime = "image/bmp"
    return f"data:{mime};base64,{b64}"

def qwen_analyze_image_return_T(image_path: str, vision_model_name: str = QWEN_VL_DEFAULT) -> str:
    data_url = _file_to_data_url(image_path)
    payload = {
        "model": vision_model_name,  # ← 使用 qwen-vl-max
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": data_url}},
                {"type": "text", "text": IMG_FIXED_PROMPT}
            ]
        }],
        "temperature": 0.3,
    }
    r = requests.post(DASHSCOPE_CHAT_COMPLETIONS_URL, headers=_dashscope_headers(), json=payload, timeout=280)
    r.raise_for_status()
    j = r.json()
    try:
        return (j["choices"][0]["message"]["content"] or "").strip()
    except Exception:
        return json.dumps(j, ensure_ascii=False)

# ================= 工具 =================
def strip_code_fences(text: str) -> str:
    if "```" not in text:
        return text
    parts = text.split("```")
    for i in range(1, len(parts), 2):
        block = parts[i]
        if "\n" in block:
            first_line, rest = block.split("\n", 1)
            if first_line.strip().lower() in {"python", "py", "bash", "sh", "text", ""}:
                return rest.strip()
            else:
                return block.strip()
        else:
            return block.strip()
    return text

# ================= 主界面 =================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AutoSim")
        self.geometry("1380x900")
        self.minsize(1180, 720)

        # DeepSeek/Qwen 模型
        self.model_var = tk.StringVar(value=MODEL_SLOW_DEFAULT)
        self.qwen_text_model_var = tk.StringVar(value=QWEN_TEXT_DEFAULT)
        self.qwen_vision_model_var = tk.StringVar(value=QWEN_VL_DEFAULT)

        self.status_var = tk.StringVar(value="Ready")

        # 图片
        self.image_path = None
        self.image_thumb = None

        self._build_ui()
        self.after(100, self._place_sash_initial)

    def _place_sash_initial(self):
        try:
            total = self.winfo_width()
            self.pw.sashpos(0, int(total * 0.58))
        except Exception:
            pass

    def _build_ui(self):
        # 顶部 Banner（显示 logo）

        self.pw = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.pw.pack(fill=tk.BOTH, expand=True)

        left_frame = ttk.Frame(self.pw)
        right_frame = ttk.Frame(self.pw)
        self.pw.add(left_frame, weight=4)
        self.pw.add(right_frame, weight=2)

        # 左侧：两个代码框
        gen_group = ttk.LabelFrame(left_frame, text="Simulation Scenario Script", padding=(8, 6))
        gen_group.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=8, pady=(8, 4))
        gen_btns = ttk.Frame(gen_group)
        gen_btns.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(gen_btns, text="save", command=self.save_gen_file).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(gen_btns, text="save as…", command=self.save_gen_as).pack(side=tk.LEFT, padx=(0, 6))
        self.gen_text = ScrolledText(gen_group, wrap=tk.NONE, undo=True, font=("Consolas", FONT_SIZE))
        self.gen_text.pack(fill=tk.BOTH, expand=True)

        sim_group = ttk.LabelFrame(left_frame, text="Main Simulation Script", padding=(8, 6))
        sim_group.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=8, pady=(4, 8))
        sim_btns = ttk.Frame(sim_group)
        sim_btns.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(sim_btns, text="save", command=self.save_sim_file).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(sim_btns, text="save as…", command=self.save_sim_as).pack(side=tk.LEFT, padx=(0, 6))
        self.sim_text = ScrolledText(sim_group, wrap=tk.NONE, undo=True, font=("Consolas", FONT_SIZE))
        self.sim_text.pack(fill=tk.BOTH, expand=True)

        # 右侧：输入 + 控件
        input_group = ttk.LabelFrame(right_frame, text="Simulation Description", padding=(8, 6))
        input_group.pack(side=tk.TOP, fill=tk.BOTH, expand=False, padx=8, pady=(8, 4))
        self.input_text = ScrolledText(input_group, wrap=tk.WORD, height=10, font=("Microsoft YaHei UI", FONT_SIZE))
        self.input_text.pack(fill=tk.BOTH, expand=True)
        self.status_label = ttk.Label(input_group, textvariable=self.status_var, foreground="#666")
        self.status_label.pack(anchor="w", pady=(6, 0))

        img_group = ttk.LabelFrame(right_frame, text="Sketch of the simulation setting (optional)", padding=(8, 6))
        img_group.pack(side=tk.TOP, fill=tk.BOTH, expand=False, padx=8, pady=(4, 4))
        img_top = ttk.Frame(img_group)
        img_top.pack(fill=tk.X)
        ttk.Button(img_top, text="Import Sketch…", command=self.on_import_image).pack(side=tk.LEFT)
        ttk.Button(img_top, text="Clear", command=self.on_clear_image).pack(side=tk.LEFT, padx=(8, 0))
        self.img_preview = ttk.Label(img_group, text="No image imported", width=40, anchor="center")
        self.img_preview.pack(fill=tk.X, pady=(6, 6))

        btn_group = ttk.Frame(right_frame)
        btn_group.pack(side=tk.TOP, fill=tk.X, padx=8, pady=(4, 2))
        self.send_btn = ttk.Button(btn_group, text="Generate", command=self.on_send_clicked)
        self.send_btn.pack(side=tk.LEFT)
        self.restart_btn = ttk.Button(btn_group, text="Restart", command=self.on_restart_clicked)
        self.restart_btn.pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(btn_group, text="Clear", command=lambda: self.input_text.delete("1.0", tk.END)).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(btn_group, text="Model:").pack(side=tk.LEFT, padx=(12, 4))
        self.model_combo = ttk.Combobox(
            btn_group, textvariable=self.model_var,
            values=[MODEL_SLOW_DEFAULT, MODEL_FAST, MODEL_QWEN_TEXT],
            state="readonly", width=18
        )
        self.model_combo.pack(side=tk.LEFT)

        # 新增：中间过程显示
        process_group = ttk.LabelFrame(right_frame, text="Intermediate Process", padding=(8, 6))
        process_group.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=8, pady=(4, 8))
        self.process_text = ScrolledText(process_group, wrap=tk.WORD, font=("Consolas", FONT_SIZE))
        self.process_text.pack(fill=tk.BOTH, expand=True)

    # 图片处理
    def on_import_image(self):
        path = filedialog.askopenfilename(
            title="Choose image",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.webp *.bmp"), ("All files", "*")]
        )
        if not path:
            return
        self.image_path = path
        self._update_image_preview(path)

    def on_clear_image(self):
        self.image_path = None
        self.image_thumb = None
        self.img_preview.configure(image="", text="No Image Imported")

    def _update_image_preview(self, path: str):
        if not PIL_AVAILABLE:
            self.img_preview.configure(text=f"Chose: {os.path.basename(path)} (No Pillow, No preview)")
            return
        try:
            im = Image.open(path)
            im.thumbnail((420, 240))
            self.image_thumb = ImageTk.PhotoImage(im)
            self.img_preview.configure(image=self.image_thumb, text="")
        except Exception as e:
            self.image_thumb = None
            self.img_preview.configure(image="", text=f"Preview failed: {e}")

    # 保存
    def save_gen_file(self):
        content = self.gen_text.get("1.0", tk.END)
        with open(GEN_FILE, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        messagebox.showinfo("saved", f"saved as {GEN_FILE}")

    def save_sim_file(self):
        content = self.sim_text.get("1.0", tk.END)
        with open(SIM_FILE, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        messagebox.showinfo("saved", f"saved as {SIM_FILE}")

    def save_gen_as(self):
        path = filedialog.asksaveasfilename(defaultextension=".py", initialfile=GEN_FILE)
        if not path: return
        content = self.gen_text.get("1.0", tk.END)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        messagebox.showinfo("saved", f"saved as {path}")

    def save_sim_as(self):
        path = filedialog.asksaveasfilename(defaultextension=".py", initialfile=SIM_FILE)
        if not path: return
        content = self.sim_text.get("1.0", tk.END)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        messagebox.showinfo("saved", f"saved as {path}")

    # 发送流程
    def on_send_clicked(self):
        user_text = self.input_text.get("1.0", tk.END).strip()

        # instructions 从包内读取（不依赖当前路径）
        try:
            instr = _resource_text("instructions.txt")
        except Exception:
            messagebox.showerror("No file", "Cannot read embedded instructions.txt")
            return

        chosen_model = self.model_var.get().strip() or MODEL_SLOW_DEFAULT

        if chosen_model.startswith("deepseek") and not _probe_ds_key():
            messagebox.showwarning("Missing Key", "DeepSeek API Key not detected")
            return

        needs_qwen = (chosen_model == MODEL_QWEN_TEXT) or bool(self.image_path)
        if needs_qwen and not (DASHSCOPE_API_KEY or os.environ.get("DASHSCOPE_API_KEY", "").strip()):
            messagebox.showwarning("Missing Key", "Please set DASHSCOPE_API_KEY")
            return

        if not user_text and not self.image_path:
            messagebox.showwarning("Note", "Please input prompt or image.")
            return

        self.send_btn.config(state=tk.DISABLED)
        self._set_status("running…")

        threading.Thread(
            target=self._run_pipeline_thread,
            args=(user_text, instr, chosen_model),
            daemon=True
        ).start()

    def on_restart_clicked(self):
        self._append_process("\n\n[Restarting task...]\n")
        self.on_send_clicked()

    def _run_pipeline_thread(self, user_text: str, instr: str, chosen_model: str):
        try:
            # 0) Optional: image analysis -> T_string
            T_string = ""
            if self.image_path:
                self._set_status("Calling Qwen (multimodal) to analyze image…")
                T_string = qwen_analyze_image_return_T(
                    self.image_path,
                    self.qwen_vision_model_var.get().strip() or QWEN_VL_DEFAULT
                )
                if T_string:
                    self._append_process("[Image Analysis - Qwen]\n" + T_string + "\n")

            # 1) Compose (不打印 composed)
            if T_string:
                composed = f"{HEAD_STR}\n\n[Image Analysis]\n{T_string}\n\n[Documentation]\n{instr}\n\n[Instruction]\n{user_text}\n"
            else:
                composed = f"{HEAD_STR}\n\n[Documentation]\n{instr}\n\n[Instruction]\n{user_text}\n"

            # 2) 主生成（选定模型）
            self._set_status(f"Requesting: using {chosen_model} to generate scripts…")
            reply1 = self._chat_router(chosen_model, composed)
            self._append_process("[Reply1 - Combined Scripts]\n" + reply1 + "\n")

            # 3) 提取两个脚本 —— 固定使用 deepseek-chat
            fast_model = MODEL_FAST
            self._set_status("Extract genDB.py…")
            prompt_gen = f"Extract only genDB.py script:\n\n{reply1}"
            reply2_code = strip_code_fences(self._chat_router(fast_model, prompt_gen))
            self._append_process("[Reply2 - genDB.py]\n" + reply2_code + "\n")

            self._set_status("Extract DSA_SIM.py…")
            prompt_sim = f"Extract only DSA_SIM.py script:\n\n{reply1}"
            reply3_code = strip_code_fences(self._chat_router(fast_model, prompt_sim))
            self._append_process("[Reply3 - DSA_SIM.py]\n" + reply3_code + "\n")

            # 4) 写文件 & 显示
            with open(GEN_FILE, "w", encoding="utf-8", newline="\n") as f:
                f.write(reply2_code)
            with open(SIM_FILE, "w", encoding="utf-8", newline="\n") as f:
                f.write(reply3_code)

            self._set_text(self.gen_text, reply2_code)
            self._set_text(self.sim_text, reply3_code)
            self._set_status("Done.")
        except Exception as e:
            self._error(str(e))
        finally:
            self._enable_send()

    # 路由不同模型
    def _chat_router(self, model_name: str, content: str, override_text_model: str = "") -> str:
        if model_name.startswith("deepseek"):
            return ds_chat_once(content, model=model_name)
        elif model_name == MODEL_QWEN_TEXT:
            text_model = override_text_model or self.qwen_text_model_var.get().strip() or QWEN_TEXT_DEFAULT
            return qwen_chat_once(content, text_model_name=text_model)
        elif model_name.startswith("qwen"):
            return qwen_chat_once(content, text_model_name=model_name)
        raise ValueError(f"Unknown Model: {model_name}")

    # UI helpers
    def _set_status(self, txt: str):
        self.after(0, lambda: self.status_var.set(txt))

    def _enable_send(self):
        self.after(0, lambda: self.send_btn.config(state=tk.NORMAL))

    def _set_text(self, widget: ScrolledText, txt: str):
        def _update():
            widget.delete("1.0", tk.END)
            widget.insert("1.0", txt)
        self.after(0, _update)

    def _append_process(self, txt: str):
        def _update():
            self.process_text.insert(tk.END, txt + "\n")
            self.process_text.see(tk.END)
        self.after(0, _update)

    def _error(self, msg: str):
        self.after(0, lambda: messagebox.showerror("error", msg))

def run():
    app = App()
    app.mainloop()

if __name__ == "__main__":
    run()
