#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 games.lua（客户端读取的唯一内容清单）

用法：
    python gen_catalog.py                    # 用 config.json 里的 base_url
    python gen_catalog.py --base-url https://raw.githubusercontent.com/你/仓库/main
    python gen_catalog.py --check            # 只校验文件是否齐全，不写文件

你只需要改两个东西：
    1. games.json   —— 有哪些游戏、叫什么、图标链接
    2. 游戏目录     —— 例如 zmxy4/ 里面放脚本文件

其余（sha256、size、URL 拼接、Lua 格式）全部由本脚本生成。
"""
import argparse
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG = os.path.join(HERE, "games.lua")
CONFIG = os.path.join(HERE, "config.json")


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def file_entry(base_url, rel_path):
    """返回 {url, sha256, size}；文件不存在返回 None"""
    abs_path = os.path.join(HERE, rel_path)
    if not os.path.isfile(abs_path):
        return None
    return {
        "url": base_url.rstrip("/") + "/" + rel_path.replace(os.sep, "/"),
        "sha256": sha256_of(abs_path),
        "size": os.path.getsize(abs_path),
    }


def lua_escape(s):
    # 只转义 lua 双引号字符串里真正需要转义的字符
    return (s.replace("\\", "\\\\")
             .replace('"', '\\"')
             .replace("\r", "\\r")
             .replace("\n", "\\n"))


def emit_val(v, indent):
    pad = "    " * indent
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, str):
        return '"' + lua_escape(v) + '"'
    if isinstance(v, dict):
        return "{\n" + "".join(
            '%s    %s = %s,\n' % (pad, k, emit_val(val, indent + 1))
            for k, val in v.items()
        ) + pad + "}"
    if isinstance(v, list):
        return "{\n" + "".join(
            "%s    %s,\n" % (pad, emit_val(x, indent + 1))
            for x in v
        ) + pad + "}"
    raise TypeError("不支持的类型: %r" % (type(v),))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--show-url", action="store_true",
                    help="只打印 config.json 里的 base_url（供批处理脚本取用）")
    args = ap.parse_args()

    base_url = args.base_url
    if not base_url and os.path.isfile(CONFIG):
        base_url = json.load(open(CONFIG, encoding="utf-8")).get("base_url")
    if not base_url:
        print("[X] 缺少 base_url：请写进 config.json 或用 --base-url 传", file=sys.stderr)
        return 2
    if args.show_url:
        print(base_url)
        return 0
    if not base_url.startswith(("http://", "https://")):
        print("[X] base_url 必须以 http:// 或 https:// 开头", file=sys.stderr)
        return 2

    meta = json.load(open(os.path.join(HERE, "games.json"), encoding="utf-8"))
    out = []
    problems = []

    for g in meta["games"]:
        gid = g["luaGameId"]
        gdir = os.path.join(HERE, gid)

        files = {}
        # 默认主脚本 <gid>/<gid>.lua.enc
        main_script = file_entry(base_url, "%s/%s.lua.enc" % (gid, gid))
        if main_script is None:
            problems.append("%s: 缺主脚本 %s/%s.lua.enc" % (gid, gid, gid))
        else:
            files["script"] = main_script

        hooks = file_entry(base_url, "%s/%s_hooks.lua" % (gid, gid))
        if hooks:
            files["hooks"] = hooks

        smeta = file_entry(base_url, "%s/scripts.meta.json" % gid)
        if smeta:
            files["meta"] = smeta

        # 所有可用脚本（多脚本模式：「MOD管理」页让用户选）
        scripts = []
        if os.path.isdir(gdir):
            for fn in sorted(os.listdir(gdir)):
                if not fn.endswith(".lua.enc"):
                    continue
                name = fn[: -len(".lua.enc")]
                e = file_entry(base_url, "%s/%s" % (gid, fn))
                if e:
                    e["name"] = name
                    scripts.append(e)
        else:
            problems.append("%s: 目录不存在（该游戏将不下发脚本）" % gid)

        entry = dict(g)          # 保留 games.json 里全部字段
        entry.pop("luaGameId")
        entry = {
            "id": g["id"],
            "name": g["name"],
            "luaGameId": gid,
            "category": g.get("category", "mod"),
            "tag": g.get("tag", ""),
            "compat": g.get("compat", ""),
            "bitWidth": g.get("bitWidth", 64),
            "hasSave": g.get("hasSave", False),
            "supportsAdvanced": g.get("supportsAdvanced", False),
            "iconUrl": g.get("iconUrl", ""),
            "coverUrl": g.get("coverUrl", ""),
            # 【2026-10-26】目标游戏包名（逗号分隔多渠道），仅用于客户端
            #   「本机已安装」徽标识别。留空 = 不做识别，不影响其他功能。
            "pkg": (g.get("pkg") or "").strip(),
        }
        # 【整改 2026-10-25】详情页用到的文案与链接，原来由私有服务器 clubInfo 下发
        for key in ("notice", "help", "download", "group"):
            val = (g.get(key) or "").strip()
            if val:
                entry[key] = val
        if files:
            entry["files"] = files
        if scripts:
            entry["scripts"] = scripts
        out.append(entry)

    common = file_entry(base_url, "common.lua.enc")
    if common is None:
        problems.append("缺 common.lua.enc（共享库，所有游戏都要用）")

    body = []
    body.append("-- ============================================================")
    body.append("-- 自动生成，请勿手动修改！")
    body.append("-- 改 games.json / 换文件后重新运行： python gen_catalog.py")
    body.append("-- base_url = %s" % base_url)
    body.append("-- ============================================================")
    body.append("")
    body.append("games = " + emit_val(out, 0))
    body.append("")
    body.append("common = " + (emit_val(common, 0) if common else "nil"))
    body.append("")
    text = "\n".join(body)

    if problems:
        print("[!] 有 %d 处问题：" % len(problems))
        for p in problems:
            print("    - " + p)

    if args.check:
        print("[OK] 校验完成（未写入 games.lua）")
        return 0 if not problems else 1

    with open(CATALOG, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("[OK] 已生成 %s（%d 款游戏，%d 字节）" % (
        os.path.basename(CATALOG), len(out), len(text.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
