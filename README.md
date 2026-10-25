# 摸鱼盒子 · 内容仓库

App 运行时从这里下载**游戏列表**和**每个游戏的 MOD 脚本**。
改这个仓库里的文件 = 改 App 里显示的内容，**不需要重新打包发版**。

---

## 一、你只需要关心 3 个地方

| 位置 | 作用 | 你什么时候动它 |
|---|---|---|
| `games.json` | 有哪些游戏、叫什么名字、图标链接 | **加/删游戏时改这里** |
| `<游戏ID>/` 目录 | 这个游戏的脚本文件 | **换脚本时往里放文件** |
| `common.lua.enc` | 所有游戏共用的基础库 | 基本不用动 |

其余文件都是自动生成的，**不要手改**：

| 文件 | 说明 |
|---|---|
| `games.lua` | 由 `gen_catalog.py` 根据上面三样生成，App 实际读这个 |
| `config.json` | 只存一个 `base_url`（你的仓库地址前缀） |

---

## 二、目录结构

```
.
├── games.json          ← 你编辑：游戏清单（名字/图标/标签）
├── config.json         ← 仓库地址前缀，建仓库后改一次
├── gen_catalog.py      ← 生成器，改完上面两个就跑一次
├── games.lua           ← 自动生成，App 读这个 ⚠️ 别手改
├── common.lua.enc      ← 共用库
├── zmxy4/              ← 一个游戏一个目录，目录名 = luaGameId
│   ├── zmxy4.lua.enc       ← 主脚本（必须有）
│   ├── zmxy4_hooks.lua     ← Frida JS 壳（有高级功能才需要）
│   └── scripts.meta.json   ← 脚本元信息（脚本名/说明）
├── elin/
│   ├── elin.lua.enc
│   ├── elin_patch.lua.enc  ← 同一游戏的第二个脚本，App 里可选
│   └── ...
└── ...
```

**关键规则：目录名必须等于 `games.json` 里的 `luaGameId`。**

---

## 三、日常操作

### 场景 A：换某个游戏的脚本（最常见）

1. 把新的 `zmxy4.lua.enc` 覆盖到 `zmxy4/` 目录
2. 在仓库根目录运行：

```bash
python gen_catalog.py
```

3. 提交并推送（见第五节）

**用户下次打开 App 就会自动拿到新脚本**——App 比对 sha256，发现不一致就重新下载。

### 场景 B：加一个新游戏

1. 建目录，例如新游戏 ID 叫 `newworld`：

```
newworld/
├── newworld.lua.enc
└── newworld_hooks.lua     ← 没有就算了
```

2. 打开 `games.json`，在 `games` 数组里加一项：

```json
{
  "id": "1015",
  "name": "游戏名",
  "luaGameId": "newworld",
  "category": "mod",
  "tag": "单机,动作",
  "compat": "支持64位 全版本",
  "bitWidth": 64,
  "hasSave": false,
  "iconUrl": "https://图标地址.png",
  "coverUrl": "https://封面地址.jpg"
}
```

> `id` 是给程序看的唯一编号，**不要和已有的重复**（现有：1006/1007/1008/1009/1010/1011/1013/1014）。
> `luaGameId` 必须和目录名一模一样。

3. 运行 `python gen_catalog.py`，提交推送。

### 场景 C：下架一个游戏

**不要删目录**（以后还想上架的话）。只要把 `games.json` 里那一条**整块删掉**，然后重新生成、提交推送。

App 下次拉列表就不再有它了。

### 场景 D：只改文案（改简介、改标签）

改 `games.json` → 重新生成 → 推送。脚本文件一个都不用动。

---

## 四、gen_catalog.py 干了什么

```bash
python gen_catalog.py            # 生成 games.lua
python gen_catalog.py --check    # 只检查文件齐不齐，不生成
```

它会：

1. 读 `games.json`（游戏元信息）
2. 去每个 `<luaGameId>/` 目录里找 `*.lua.enc` / `*_hooks.lua` / `scripts.meta.json`
3. 给每个文件算 **sha256** 和大小
4. 按 `config.json` 的 `base_url` 拼出完整下载链接
5. 输出 `games.lua`（Lua 表格式，App 用 LuaJ 解析）

**sha256 是干什么的**：App 下载完文件后会自己算一遍哈希，对不上就不用。
所以哪怕链接被中间人换成别的内容，App 也不会执行——**这个哈希是唯一的安全保证**。

---

## 五、怎么发布

### 一条命令搞定（推荐）

改完任何东西，**双击 `推送.bat`** 就行。它会自动做三件事：

```
1. python gen_catalog.py     ← 重新算 sha256、重写 games.lua
2. python push_via_api.py    ← 上传到 GitHub
3. 本地 git 留档
```

看到 `完成: 成功 N, 失败 0` 就好了。**GitHub CDN 需要 1-5 分钟**刷新，之后 App 重新打开就能拿到新内容。

### 手动执行（等价）

```bash
cd /d D:\AndroidProcess\_mods-repo
python gen_catalog.py
python push_via_api.py
```

### 为什么不用 git push

本机网络环境下：

| 目标 | 直连 | 走 Clash 代理 |
| --- | --- | --- |
| `github.com` | 慢/断 | 通 |
| `raw.githubusercontent.com` | 超时 | 通 |
| **`api.github.com`** | **直连就通** | — |

`git push` 走的是 `github.com`，被墙；而 `push_via_api.py` 走的是 `api.github.com`，**直连就通，不用挂任何代理**。

所以内容更新这条路**完全不依赖加速器** —— 机场跑了也不影响发版。

### Token 说明

`token.txt` 里存的是 GitHub fine-grained PAT，已加入 `.gitignore`，**不会上传**。

| 项 | 值 |
| --- | --- |
| 权限 | 只有 `Contents: Read and write` |
| 范围 | 只有 `Maruu1/xy-content` 这一个仓库 |
| 有效期 | **7 天**（到期自动作废） |

**token 过期后**怎么续：

1. 打开 https://github.com/settings/personal-access-tokens/new （要挂 Clash）
2. Token name 随便填；Expiration 选 7 天
3. Repository access → Only select repositories → 勾 `xy-content`
4. Permissions → Repository permissions → **Contents = Read and write**
5. Generate token → 复制 → 粘进 `token.txt` 覆盖旧的

配好之后发版反倒不需要代理了。

## 六、第一次建仓库要做的事

1. 在 GitHub 网页点 **New repository**
   - Repository name 随便起，例如 `moyu-content`
   - 选 **Public**（必须公开，私有仓库的 raw 链接外部访问不了）
   - **不要**勾选 Add README / .gitignore / license（保持空仓库）
2. 复制仓库地址，把 `config.json` 里的 `base_url` 改成：

```
https://raw.githubusercontent.com/你的用户名/moyu-content/main
```

3. 运行 `python gen_catalog.py` 重新生成 `games.lua`
4. 按第五节推上去

---

## 七、常见问题

| 现象 | 原因 |
|---|---|
| App 里一个游戏都没有 | `games.lua` 里的 `base_url` 和你实际仓库地址对不上 |
| 某个游戏有卡片但点开没脚本 | 该目录下缺 `<luaGameId>.lua.enc`，或 `gen_catalog.py` 提示缺文件 |
| 改了脚本 App 没更新 | 忘了跑 `gen_catalog.py`，`games.lua` 里的 sha256 还是旧的 |
| 提交后 App 还是旧的 | GitHub CDN 缓存，等 1～5 分钟 |
| 提示 sha256 不符 | 文件被 GitHub 或代理改过（例如用了会重编码的网盘），重新上传原件 |

---

## 八、⚠️ 合规红线（重要）

这个仓库是**公开**的，任何人都能下载和围观。上架前必须确认：

1. **不能有付费解锁内容**——所有内容对所有人免费
2. **不能有联网游戏的外挂脚本**——只做纯单机
3. **不能有重签游戏包**——本仓库只放 Lua 脚本，不含任何 APK
4. 每个脚本的 `compat` 字段写清支持的版本，别写"全渠道全版本可用"这种无法验证的话（除非真的验证过）

被举报下架一次，整个分发渠道就没了。宁可少上几个游戏。
