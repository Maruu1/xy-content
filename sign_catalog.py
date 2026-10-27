#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
目录签名工具（ECDSA P-256 + SHA-256）

用途：给 games.lua / components.json 签名。客户端内置公钥，验签失败即拒绝使用。
      这样第三方加速代理无法替换目录内容（哈希在目录里，目录被换就整链失守）。

用法：
    python sign_catalog.py --genkey          # 首次：生成密钥对
    python sign_catalog.py                   # 给 games.lua + components.json 签名

产物：
    ../_signing/keys/catalog_private.pem   ← 私钥，在内容仓库之外，绝不外传
    keys/catalog_public.pem    ← 公钥
    keys/catalog_public_b64.txt← 公钥 DER(base64)，内置到客户端用
    *.sig                      ← DER 格式签名（Java 的 SHA256withECDSA 直接认）
"""
import argparse
import base64
import os
import sys

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
except ImportError:
    print("[X] 需要 pip install cryptography", file=sys.stderr)
    sys.exit(2)

HERE = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# 【2026-10-26 安全事故后改造】密钥目录**移出上传根目录**
#
#   原来密钥放在 _mods-repo/keys/ 里，只靠 push_via_api.py 的排除规则
#   挡着才没上传。2026-10-25 那次排除规则漏了 keys/，签名私钥被推到
#   公开仓库，暴露 37 小时，整条验签链作废、只能轮换密钥。
#
#   现在从物理上断开：密钥放在内容仓库**外面**，
#   push_via_api.py 无论怎么改都不可能遍历到它。
#
#   可用环境变量 XY_KEYS_DIR 覆盖（CI / 换机器时用）。
# ============================================================
KEYS = os.environ.get("XY_KEYS_DIR") or os.path.abspath(
    os.path.join(HERE, "..", "_signing", "keys"))
PRIV = os.path.join(KEYS, "catalog_private.pem")
PUB = os.path.join(KEYS, "catalog_public.pem")
PUB_B64 = os.path.join(KEYS, "catalog_public_b64.txt")

TARGETS = ["games.lua", "components.json", "notice.json"]


def genkey():
    os.makedirs(KEYS, exist_ok=True)
    if os.path.isfile(PRIV):
        print("[!] 私钥已存在，不覆盖（避免客户端全部失配）")
        print("    真要重新生成请先手动删除 " + PRIV)
        return 1
    key = ec.generate_private_key(ec.SECP256R1())
    with open(PRIV, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()))
    pub = key.public_key()
    with open(PUB, "wb") as f:
        f.write(pub.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo))
    der = pub.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo)
    with open(PUB_B64, "w", encoding="ascii") as f:
        f.write(base64.b64encode(der).decode("ascii"))
    print("[OK] 已生成密钥对")
    print("     私钥: " + PRIV + "  ← 绝不外传（已在内容仓库之外）")
    print("     公钥: " + PUB)
    print("     客户端常量（DER base64）:")
    print("     " + base64.b64encode(der).decode("ascii"))
    return 0


def sign_all():
    if not os.path.isfile(PRIV):
        print("[X] 缺私钥，先跑 --genkey", file=sys.stderr)
        return 2
    with open(PRIV, "rb") as f:
        key = serialization.load_pem_private_key(f.read(), password=None)
    ok = 0
    for name in TARGETS:
        path = os.path.join(HERE, name)
        if not os.path.isfile(path):
            print("    - 跳过（不存在）: " + name)
            continue
        data = open(path, "rb").read()
        sig = key.sign(data, ec.ECDSA(hashes.SHA256()))
        with open(path + ".sig", "wb") as f:
            f.write(sig)
        print("    - 已签名 %-18s %6d B  → .sig %d B" % (name, len(data), len(sig)))
        ok += 1
    print("[OK] 共签名 %d 个文件" % ok)
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--genkey", action="store_true")
    a = ap.parse_args()
    sys.exit(genkey() if a.genkey else sign_all())
