# 🍽 Restaurant Queue Simulator — 本地 UI 使用教程

> **COMP1110 Group Project — 本地可视化界面**
>
> 本 UI 完全不修改原项目任何文件，仅新增 `app.py` 和 `ui.html` 两个文件。

---

## 📁 文件说明

将以下两个新文件放入**与 `main.py` 相同的目录**（即你的项目文件夹 `COMP1110_F15/`）：

```
COMP1110_F15/
├── main.py              ← 原项目文件（不修改）
├── request1.csv         ← 原项目文件（不修改）
├── request2.csv         ← 原项目文件（不修改）
├── ...
├── request10.csv        ← 原项目文件（不修改）
├── restaurant1.csv      ← 原项目文件（不修改，若存在）
├── ...
├── restaurant10.csv     ← 原项目文件（不修改，若存在）
├── app.py               ← 【新增】Flask 本地服务器
└── ui.html              ← 【新增】浏览器界面
```

---

## 🚀 快速开始（3 步）

### 第 1 步：安装依赖

打开终端（Windows 用 PowerShell 或 CMD，Mac/Linux 用 Terminal），运行：

```bash
pip install flask flask-cors
```

> 如果你的电脑同时装了 Python 2 和 Python 3，请用 `pip3` 代替 `pip`。

---

### 第 2 步：启动服务器

在终端中，**进入项目文件夹**，然后运行 `app.py`：

```bash
# Windows（PowerShell 或 CMD）
cd "C:\Users\你的用户名\OneDrive - The University of Hong Kong - Connect\COMP1110\COMP1110_F15"
python app.py

# Mac / Linux
cd ~/path/to/COMP1110_F15
python3 app.py
```

启动成功后，终端会显示：

```
=======================================================
  🍽  Restaurant Queue Simulator - Local UI
=======================================================
  项目目录: /path/to/COMP1110_F15
  请在浏览器打开: http://localhost:5000
  按 Ctrl+C 停止服务器
=======================================================
 * Running on http://127.0.0.1:5000
```

---

### 第 3 步：打开浏览器

在浏览器（推荐 Chrome 或 Edge）地址栏输入：

```
http://localhost:5000
```

即可看到完整的模拟界面。

---

## 🖥 界面功能说明

界面分为左侧导航栏和右侧内容区，共 5 个页面：

### 🪑 餐桌配置
- 动态添加、删除桌型（每种桌型配置数量和座位容量）
- 提供 3 种快速预设：小型 / 默认 / 大型餐厅
- 实时显示总桌数、总容量、桌型种数

### 👥 顾客请求
- **手动添加**：填写表单（人数、到达时间、用餐时长、拼桌/VIP/预订/过号等）
- **CSV 批量导入**：点击上传区或拖拽 CSV 文件
- **列表管理**：表格展示所有请求，支持行内编辑和删除
- **导出请求**：将当前请求列表导出为 CSV

> **到达时间格式**：`YYYYMMDDHHmmss`，例如 `20260101120000` 表示 2026年1月1日 12:00:00

### 📂 预置用例
- 自动加载项目目录中的 `request1.csv` ~ `request10.csv`
- 点击任意用例卡片，一键将数据加载到「顾客请求」页面
- 若对应的 `restaurant{n}.csv` 存在，餐桌配置也会同步加载

### ▶️ 运行模拟
- 显示当前配置摘要（桌数、请求数、总容量）
- 点击「开始模拟」按钮，调用 `main.py` 中的 `simulate()` 函数
- 模拟完成后自动跳转到结果页面

### 📊 模拟结果
展示以下内容：

| 模块 | 内容 |
|------|------|
| 统计卡片 | 平均等待时间、最大等待时间、峰值队列长度、服务组数、桌子利用率、服务水平（10分钟内入座比例）、总模拟时长 |
| 等待时间分布图 | 柱状图，按 0-5分 / 5-10分 / 10-15分 / 15-20分 / 20分+ 分组 |
| 桌子利用率图 | 环形图，展示每张桌子的占用率 |
| 等待时间明细表 | 每位顾客的等待时间、VIP 状态、是否达标（≤10分钟） |
| 桌子利用率明细表 | 每张桌子的容量、利用率、占用时长 |
| 导出 CSV | 包含统计摘要 + 每位顾客数据 + 每张桌子数据 |

---

## ❓ 常见问题

### Q: 提示 `ModuleNotFoundError: No module named 'flask'`
**A:** 未安装 Flask，请运行：
```bash
pip install flask flask-cors
```

### Q: 提示 `Address already in use` / 端口被占用
**A:** 5000 端口已被其他程序占用。可以修改 `app.py` 最后一行的端口号：
```python
app.run(host="127.0.0.1", port=5001, debug=False)  # 改为 5001
```
然后访问 `http://localhost:5001`。

### Q: 预置用例显示「未找到预置用例文件」
**A:** 请确保 `app.py` 和 `request1.csv` ~ `request10.csv` 在**同一目录**下。

### Q: 模拟报错「无法导入 main.py」
**A:** 请确保 `app.py` 与 `main.py` 在**同一目录**下，且 `main.py` 没有语法错误。

### Q: 浏览器打开后界面显示「服务器未连接」
**A:** 请检查终端中 `app.py` 是否正在运行，没有报错。

### Q: Mac 上 `python app.py` 提示找不到命令
**A:** 尝试用 `python3 app.py`。

---

## 🛑 停止服务器

在运行 `app.py` 的终端中按 `Ctrl + C` 即可停止服务器。

---

## 📋 CSV 文件格式参考

### 顾客请求 CSV（request{n}.csv）

```
index,people,arrival,duration,share,miss,comeback,vip,reserved
1,2,20260101120000,30,1,0,0,0,0
2,4,20260101120500,45,0,0,0,1,0
```

| 字段 | 说明 | 取值 |
|------|------|------|
| index | 请求编号 | 正整数 |
| people | 人数 | 正整数 |
| arrival | 到达时间 | YYYYMMDDHHmmss |
| duration | 用餐时长（分钟）| 正整数 |
| share | 拼桌意愿 | 1=愿意，0=不愿意 |
| miss | 过号 | 1=是，0=否 |
| comeback | 过号后返回 | 1=是，0=否 |
| vip | VIP | 1=是，0=否 |
| reserved | 预订 | 1=是，0=否 |

### 餐桌配置 CSV（restaurant{n}.csv）

```
count,capacity
5,2
3,4
2,6
1,8
```

| 字段 | 说明 |
|------|------|
| count | 该桌型的数量 |
| capacity | 该桌型的座位容量 |

---