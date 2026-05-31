#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2025 D_Chuan (GitHub: D-Chuan1)
# Contact: 1010079261@qq.com
# This code is licensed under the MIT License. See the LICENSE file in the repository root for details.

"""
Minecraft 模组自动汉化工具 - 完全免费版
功能：自动扫描 mods 文件夹下的所有 .jar 模组，提取英文语言文件，调用多引擎翻译，
      将翻译后的语言文件重新打包回 jar，输出到汉化文件夹，保留原文件。
支持：DeepSeek、Google、LibreTranslate、MyMemory，自动故障转移，精确保护占位符。
"""

import os
import sys
import subprocess
import zipfile
import json
import shutil
import re
import time
from pathlib import Path
from typing import List, Tuple, Optional

# ================= 常见问题模板（运行时生成） =================

FAQ_CONTENT = '''===========================================================
Minecraft 模组自动汉化工具 - 常见问题与解决方法
===========================================================

【Q1】为什么翻译结果仍是英文？
【A】可能所有翻译引擎都不可用。解决方法：
  1. 检查网络连接是否正常。
  2. 配置 DeepSeek API Key（推荐，质量最高）。
     - 注册地址：https://platform.deepseek.com/
     - 获取 API Key 后，本脚本会在首次运行时询问并自动保存。
  3. 如果使用本地 LibreTranslate，确保服务已启动：
     docker run -it -p 5000:5000 libretranslate/libretranslate
  4. 查看控制台输出的具体错误信息。

【Q2】汉化后模组无法加载？
【A】确保：
  1. 游戏语言设置为“简体中文”。
  2. 没有其他冲突的汉化资源包或模组。
  3. 模组本身支持外置语言文件（本工具只处理标准语言文件）。

【Q3】需要付费吗？
【A】完全不需要。所有接口均免费：
  - DeepSeek 提供大量免费额度，足够个人使用。
  - Google 翻译、MyMemory 无需注册，完全免费。
  - LibreTranslate 可本地部署，永久免费。

【Q4】脚本报错 `ModuleNotFoundError: No module named 'requests'`？
【A】脚本会自动尝试安装 `requests`，如果失败请手动运行：
    pip install requests

【Q5】处理模组时提示“未找到源语言文件”？
【A】说明该模组可能没有标准的外置语言文件（文本硬编码在代码中），本工具无法汉化此类模组。

【Q6】汉化后的模组文件变大或变小了？
【A】正常现象。重新打包时压缩级别可能与原包不同，但不影响运行。

【Q7】如何更新已汉化的模组？
【A】直接用新版本的原始模组替换 `mods` 文件夹中的文件，再次运行脚本即可。脚本会自动生成新的汉化版。

【Q8】如何配置 DeepSeek API Key？
【A】首次运行脚本时会提示输入，输入后会自动保存到 .env 文件。也可以手动创建 .env 文件，内容为：
    DEEPSEEK_API_KEY=sk-你的密钥

【Q9】脚本会生成哪些文件？
【A】脚本会生成一个 FAQ.txt 文件（用记事本打开）和一个 .env 文件（保存 API Key）。
    FAQ.txt 不会自动删除，方便你随时查阅。其他临时文件会在脚本退出时清理。

===========================================================
更多帮助请访问 GitHub 仓库：https://github.com/D-Chuan1/Minecraft-MC-Mod-Pack-Translation-Program
===========================================================
'''

def generate_and_open_faq():
    """生成 FAQ.txt 并用系统默认编辑器打开（不阻塞）"""
    faq_path = Path("FAQ.txt")
    with open(faq_path, 'w', encoding='utf-8') as f:
        f.write(FAQ_CONTENT)
    print(f"[提示] 已生成常见问题文件: {faq_path.absolute()}")
    try:
        if sys.platform == "win32":
            os.startfile(faq_path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", faq_path])
        else:
            subprocess.Popen(["xdg-open", faq_path])
        print("[提示] 已自动打开常见问题文件，请查阅后关闭即可。")
    except Exception as e:
        print(f"[警告] 无法自动打开文件: {e}，请手动打开 {faq_path} 查看常见问题。")

# ================= API 密钥配置管理 =================

def load_api_key():
    """从 .env 文件或环境变量加载 DeepSeek API Key"""
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if key:
        return key
    env_file = Path(".env")
    if env_file.exists():
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("DEEPSEEK_API_KEY="):
                        key = line.split("=", 1)[1].strip()
                        if key and not key.startswith('"'):
                            return key
        except:
            pass
    return ""

def save_api_key(key):
    """保存 API Key 到 .env 文件"""
    env_file = Path(".env")
    try:
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(f"DEEPSEEK_API_KEY={key}\n")
        print(f"[配置] API Key 已保存到 {env_file}")
    except Exception as e:
        print(f"[错误] 保存 API Key 失败: {e}")

def configure_api_key():
    """交互式配置 DeepSeek API Key"""
    print("\n" + "="*50)
    print("首次使用提示：为了获得最佳翻译质量，建议配置 DeepSeek API Key")
    print("DeepSeek 提供免费额度，注册地址：https://platform.deepseek.com/")
    print("="*50)
    key = input("请输入你的 DeepSeek API Key（直接回车跳过，将使用其他免费引擎）: ").strip()
    if key:
        save_api_key(key)
        return key
    else:
        print("[提示] 未配置 DeepSeek API Key，将使用 Google/LibreTranslate/MyMemory 等免费引擎（质量略低）")
        return ""

# ================= 依赖自动安装 =================

def install_requests():
    try:
        import requests
        return True
    except ImportError:
        print("正在自动安装 requests 库...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
            print("requests 安装成功，请重新运行脚本。")
            sys.exit(0)
        except Exception as e:
            print(f"自动安装失败，请手动执行: pip install requests\n错误: {e}")
            sys.exit(1)

install_requests()
import requests

# ================= 翻译核心逻辑 =================

DEFAULT_MODS_DIR = "./mods"
DEFAULT_OUTPUT_DIR = "./汉化"
DEFAULT_TARGET_LANG = "zh-CN"
DEFAULT_SOURCE_PATTERNS = ["en_us", "en_US", "en_ud", "en_pt"]

# 加载 DeepSeek API Key
DEEPSEEK_API_KEY = load_api_key()
if not DEEPSEEK_API_KEY:
    DEEPSEEK_API_KEY = configure_api_key()

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

TRANSLATION_ENGINES = [
    {"name": "DeepSeek-Expert", "url": DEEPSEEK_API_URL, "api_key": DEEPSEEK_API_KEY,
     "model": "deepseek-reasoner", "timeout": 15},
    {"name": "DeepSeek-Fast", "url": DEEPSEEK_API_URL, "api_key": DEEPSEEK_API_KEY,
     "model": "deepseek-chat", "timeout": 10},
    {"name": "GoogleTranslate", "url": "https://translate.googleapis.com/translate_a/single",
     "api_key": None, "timeout": 8},
    {"name": "LibreTranslate", "url": "http://localhost:5000/translate",
     "api_key": None, "timeout": 10},
    {"name": "MyMemory", "url": "https://api.mymemory.translated.net/get",
     "api_key": None, "timeout": 8},
]

class MultiTranslator:
    def __init__(self, engines_config):
        self.engines = engines_config
        self.current_engine_idx = 0

    def _call_deepseek(self, engine, text):
        api_key = engine.get('api_key')
        if not api_key:
            return None
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": engine['model'],
            "messages": [
                {"role": "system", "content": "You are a professional translator. Translate English game text to Simplified Chinese accurately. Keep placeholders like %s, {0}, <item> unchanged. Output only translation."},
                {"role": "user", "content": text}
            ],
            "temperature": 0.3,
            "max_tokens": 2048
        }
        try:
            resp = requests.post(engine['url'], headers=headers, json=payload, timeout=engine['timeout'])
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()
        except:
            pass
        return None

    def _call_google(self, text):
        params = {"client": "gtx", "sl": "en", "tl": "zh-CN", "dt": "t", "q": text}
        try:
            resp = requests.get("https://translate.googleapis.com/translate_a/single", params=params, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0 and len(data[0]) > 0:
                    return ''.join([item[0] for item in data[0] if item[0]])
        except:
            pass
        return None

    def _call_libretranslate(self, text):
        payload = {"q": text, "source": "en", "target": "zh", "format": "text"}
        try:
            resp = requests.post("http://localhost:5000/translate", json=payload, timeout=10)
            if resp.status_code == 200:
                return resp.json().get("translatedText")
        except:
            pass
        return None

    def _call_mymemory(self, text):
        params = {"q": text, "langpair": "en|zh-CN"}
        try:
            resp = requests.get("https://api.mymemory.translated.net/get", params=params, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("responseData", {}).get("translatedText")
        except:
            pass
        return None

    def translate(self, text):
        if not text or not text.strip():
            return text, "None"
        for i in range(len(self.engines)):
            idx = (self.current_engine_idx + i) % len(self.engines)
            engine = self.engines[idx]
            name = engine['name']
            if name.startswith("DeepSeek") and not engine.get('api_key'):
                continue
            try:
                start = time.time()
                if name.startswith("DeepSeek"):
                    result = self._call_deepseek(engine, text)
                elif name == "GoogleTranslate":
                    result = self._call_google(text)
                elif name == "LibreTranslate":
                    result = self._call_libretranslate(text)
                elif name == "MyMemory":
                    result = self._call_mymemory(text)
                else:
                    continue
                if result:
                    self.current_engine_idx = idx
                    print(f"      [翻译] 使用 {name} ({int((time.time()-start)*1000)}ms)")
                    return result, name
            except:
                pass
            time.sleep(0.3)
        print(f"      [错误] 所有翻译引擎失败，保留原文")
        return text, "None"

translator = MultiTranslator(TRANSLATION_ENGINES)

def protect_placeholders(text: str):
    pattern = re.compile(r'(%[a-zA-Z]|{\d+}|<[^>]+>|&[a-f0-9A-FK-ORa-fk-or]|\\u[0-9a-fA-F]{4})')
    placeholders = {}
    def repl(m):
        key = f"__PH_{len(placeholders)}__"
        placeholders[key] = m.group(0)
        return key
    return pattern.sub(repl, text), placeholders

def restore_placeholders(text: str, placeholders: dict):
    for k, v in placeholders.items():
        text = text.replace(k, v)
    return text

def translate_text(text: str) -> str:
    if not text.strip():
        return text
    protected, ph = protect_placeholders(text)
    translated, _ = translator.translate(protected)
    return restore_placeholders(translated, ph)

def translate_lang_file(content: str) -> str:
    lines = content.splitlines()
    out = []
    for line in lines:
        if line.strip() and not line.startswith('#'):
            if '=' in line:
                k, v = line.split('=', 1)
                out.append(f"{k}={translate_text(v.strip())}")
            else:
                out.append(line)
        else:
            out.append(line)
    return '\n'.join(out)

def translate_json_file(content: str) -> str:
    try:
        data = json.loads(content)
        new = {}
        for k, v in data.items():
            if isinstance(v, str):
                new[k] = translate_text(v)
            else:
                new[k] = v
        return json.dumps(new, indent=2, ensure_ascii=False)
    except:
        return content

def get_lang_files(jar_path: Path, patterns: List[str]) -> List[Tuple[str, str, str]]:
    """扫描 jar 内所有匹配源语言模式的语言文件"""
    files = []
    with zipfile.ZipFile(jar_path, 'r') as zf:
        for info in zf.filelist:
            path = info.filename
            parts = Path(path).parts
            if len(parts) >= 4 and parts[0] == 'assets' and parts[2] == 'lang':
                fname = parts[-1]
                if fname.endswith(('.json', '.lang')):
                    stem = Path(fname).stem
                    if stem.lower() in [p.lower() for p in patterns]:
                        files.append((path, parts[1], fname))
    return files

def process_mod(jar: Path, out_dir: Path, temp_dir: Path, target_lang: str, patterns: List[str]) -> bool:
    """处理单个模组：解压 -> 翻译 -> 重新打包 -> 输出"""
    name = jar.stem
    print(f"\n处理模组: {name}")
    extract = temp_dir / name
    extract.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(jar, 'r') as zf:
        zf.extractall(extract)
    lang_files = get_lang_files(jar, patterns)
    if not lang_files:
        print("  未找到源语言文件，跳过")
        shutil.rmtree(extract, ignore_errors=True)
        return False
    modified = False
    for full, ns, fname in lang_files:
        print(f"  处理: {full}")
        src = extract / full
        with open(src, 'r', encoding='utf-8') as f:
            orig = f.read()
        if fname.endswith('.json'):
            trans = translate_json_file(orig)
        else:
            trans = translate_lang_file(orig)
        target_fname = f"{target_lang}.json" if fname.endswith('.json') else f"{target_lang}.lang"
        target_path = src.parent / target_fname
        if trans != orig or not target_path.exists():
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(trans)
            modified = True
            print(f"    已生成: {target_path}")
    if not modified:
        print("  未产生有效翻译，跳过打包")
        shutil.rmtree(extract, ignore_errors=True)
        return False
    new_jar = out_dir / f"{name}.jar"
    with zipfile.ZipFile(new_jar, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(extract):
            for file in files:
                full = Path(root) / file
                zf.write(full, full.relative_to(extract))
    print(f"  ✅ 汉化模组已生成: {new_jar}")
    shutil.rmtree(extract, ignore_errors=True)
    return True

def main():
    import argparse
    p = argparse.ArgumentParser(description='Minecraft 模组自动汉化（完全免费）')
    p.add_argument('--mods-dir', default=DEFAULT_MODS_DIR,
                   help=f'模组文件夹路径（默认 {DEFAULT_MODS_DIR}）')
    p.add_argument('--output-dir', default=DEFAULT_OUTPUT_DIR,
                   help=f'输出文件夹路径（默认 {DEFAULT_OUTPUT_DIR}）')
    p.add_argument('--target-lang', default=DEFAULT_TARGET_LANG,
                   help=f'目标语言代码（默认 {DEFAULT_TARGET_LANG}）')
    p.add_argument('--source-patterns', default=','.join(DEFAULT_SOURCE_PATTERNS),
                   help=f'源语言文件名匹配模式，逗号分隔（默认 en_us,en_US,en_ud,en_pt）')
    args = p.parse_args()

    # 1. 生成并打开常见问题文件
    generate_and_open_faq()

    # 2. 执行汉化
    mods_path = Path(args.mods_dir)
    if not mods_path.exists():
        print(f"错误: 模组目录 '{args.mods_dir}' 不存在")
        sys.exit(1)

    out_path = Path(args.output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    temp_path = out_path.parent / ".temp_localizer"
    temp_path.mkdir(parents=True, exist_ok=True)

    patterns = [x.strip() for x in args.source_patterns.split(',') if x.strip()]
    jars = list(mods_path.glob("*.jar"))
    if not jars:
        print(f"在 '{args.mods_dir}' 中未找到任何 .jar 文件")
        sys.exit(0)

    print(f"找到 {len(jars)} 个模组")
    print(f"输出: {out_path.absolute()}")
    print("引擎顺序: DeepSeek专家 → DeepSeek快速 → Google → LibreTranslate → MyMemory")
    print("-" * 50)

    success = 0
    for jar in jars:
        if process_mod(jar, out_path, temp_path, args.target_lang, patterns):
            success += 1

    shutil.rmtree(temp_path, ignore_errors=True)
    print(f"\n🎉 完成！成功汉化 {success}/{len(jars)} 个模组")
    print(f"输出目录: {out_path.absolute()}\n原始模组未改动")
    print("\n[提示] 常见问题文件 (FAQ.txt) 已自动打开，请查阅。")

if __name__ == "__main__":
    main()