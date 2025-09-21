# AutoSim
**AutoSim** is an **Automated Simulation Script Generator** powered by large language models (DeepSeek and Qwen).  
Its purpose is to help researchers and students generate simulation scripts automatically from natural language descriptions and optional sketches.  

With AutoSim, you can:
- Write a description of your simulation scenario in plain English or Chinese.
- Optionally provide a sketch (image) of the simulation box and obstacles.
- Automatically generate **two ready-to-run Python scripts**:
  - `genDB.py`: Builds the initial configuration of the system.
  - `DSA_SIM.py`: Runs the main simulation procedure.
- Edit and save the generated scripts directly in the GUI.
- Track intermediate LLM outputs in a process log window.

Currently, AutoSim is mainly designed for **particle-based simulations**.  
It has built-in familiarity with the **pygamd** package and can generate scripts accordingly.  
If you want to extend AutoSim to other types of simulations, you can simply modify or extend the instructions provided in:
```
autosim/data/instructions.txt
```
By updating this file, AutoSim can be guided to generate scripts for different simulation frameworks or problem domains.

---

## Installation

### 1. Install from source

Clone the repository and install:

```bash
git clone https://github.com/JianfengFD/autosim.git
cd autosim
pip install .
```

Now you can launch AutoSim from the command line:

```bash
autosim
```

On Windows, if you prefer a GUI entry without a console window:

```bash
autosim-gui
```

---

### 2. Build as a standalone app/executable

If you want AutoSim as a double-clickable desktop application:

#### macOS

1. Install PyInstaller:

```bash
pip install pyinstaller
```

2. Run:

```bash
pyinstaller -w -n AutoSim
--add-data=autosim/data/title.gif:autosim/data
--add-data=autosim/data/instructions.txt:autosim/data
-i autosim/data/title.icns
autosim/app.py
```

This will create:

```
dist/AutoSim.app
```

Double-click it in Finder, or run:

```bash
open dist/AutoSim.app
```

#### Windows

```bash
pyinstaller -F -w -n AutoSim ^
  --add-data "autosim/data/title.gif;autosim/data" ^
  --add-data "autosim/data/instructions.txt;autosim/data" ^
  -i autosim/data/title.ico ^
  autosim/app.py
```

This will create:

```
dist/AutoSim.exe
```

---

## API Key Configuration

AutoSim requires external LLM APIs (DeepSeek and Qwen/DashScope).  
You must configure environment variables for API keys before running.

### DeepSeek API Key

**macOS / Linux (bash/zsh):**

```bash
export DEEPSEEK_API_KEY="your_deepseek_key"
```

**Windows (PowerShell):**

```powershell
setx DEEPSEEK_API_KEY "your_deepseek_key"
```

---

### Qwen (DashScope) API Key

**macOS / Linux (bash/zsh):**

```bash
export DASHSCOPE_API_KEY="your_dashscope_key"
```

**Windows (PowerShell):**

```powershell
setx DASHSCOPE_API_KEY "your_dashscope_key"
```

---

### Verify

After setting environment variables, you can verify:

**macOS/Linux:**

```bash
echo $DEEPSEEK_API_KEY
echo $DASHSCOPE_API_KEY
```

**Windows (PowerShell):**

```powershell
echo %DEEPSEEK_API_KEY%
echo %DASHSCOPE_API_KEY%
```

---

## Summary

AutoSim provides a **user-friendly graphical interface** to convert text and images into simulation scripts.  
By combining **DeepSeek for reasoning** and **Qwen for multimodal image analysis**, AutoSim makes simulation setup:  
- Faster  
- Smarter  
- Easier  

It is useful for:
- Rapid prototyping in research
- Teaching demonstrations
- Automating repetitive simulation setup tasks
