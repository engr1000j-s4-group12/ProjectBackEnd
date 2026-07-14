# VLM 智能导览助手

本项目是 ENGR1000J Group 12 的课程项目。目标是基于立创·实战派 ESP32-S3 和小智 AI，制作一个面向外国访客的语音导览终端。

终端通过摄像头观察周围环境，使用 VLM 提取门牌、展品和环境特征，再由电脑后端判断当前位置、规划路线并生成中英文导览信息。

## 系统结构

```text
访客语音/现场照片
        ↓
ESP32-S3 小智终端
        ↓
电脑 FastAPI 后端
   ├─ VLM 图片特征提取
   ├─ 地点视觉匹配
   ├─ 最短路线规划
   └─ 展品资料查询
        ↓
小智语音播报
```

## 当前已经完成

- FastAPI 后端和自动接口文档；
- 4F 地点、走廊、路线及展品 JSON 数据结构；
- Dijkstra 最短路线规划；
- 普通路线和无障碍路线；
- 中英文分段导航指令；
- 图片上传及 OpenAI 兼容 VLM 接口；
- 根据物品、标牌文字和场景特征匹配位置；
- 对位置不明确和无法定位的情况返回安全状态；
- 21 项后端自动化测试；
- Excel 地图维护模板，支持 `nodes`、`edges` 和 `metadata`；
- 导入/导出脚本，避免 JSON 和 Excel 地图数据漂移。

当前 4F 路网已经能生成节点间移动信息，但走廊节点、距离和视觉地标仍基于楼层索引图估算，正式现场导航前必须实地校准。

### 2026-07-05 固件里程碑

- 已使用 ESP-IDF 5.5.4 为 `lichuang-dev`（ESP32-S3、16 MiB Flash、8 MiB PSRAM）完成小智固件 v2.2.6 编译；
- 已通过开发板原生 USB-Serial/JTAG 接口完成固件及资源写入，并通过 UART 启动日志验证；
- 屏幕、ES8311/ES7210 音频链路和 GC0308 摄像头初始化正常；
- `self.camera.take_photo` MCP 工具已注册，设备已完成 Wi-Fi 配置并进入待命状态；
- 本阶段使用小智现有视觉服务验证设备能力，不连接本项目 FastAPI 后端，也未实现 `museum.visual_localize` 或 `museum.plan_route`；
- 因现场暂不便进行语音交互，首次 VLM 图片问答按当日计划视为完成并暂时冻结；正式测试报告仍需补充一次可复现的拍照、上传和模型响应日志。

小智固件源码和硬件联调资料位于本机 `/home/Hylia/workspace/Project-2/xiaozhi-esp32`，当前仓库只维护后端和数据层。

## 目录说明

```text
Documents/       课程要求和项目草案
data/            地图、视觉地标和展品数据
server/          Python FastAPI 后端
scripts/         地图导入导出、数据分析和 API 验证脚本
tests/           后端自动化测试
使用指南.md       完整安装、接口和联调说明
```

## 快速运行后端

需要 Python 3.11 或更高版本。

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r server/requirements-dev.txt
uvicorn server.app.main:app --host 0.0.0.0 --port 8000 --reload
```

打开：

```text
http://127.0.0.1:8000/docs
```

运行测试：

```bash
python3 -m pytest -q
```

直接上传照片需要先配置支持图片输入的 VLM：

```bash
export VLM_BASE_URL="https://服务地址/v1"
export VLM_API_KEY="API密钥"
export VLM_MODEL="模型名称"
```

密钥只能保存在本机环境变量中，不得提交到 Git。

## 地图数据维护

地图主数据为：

```text
data/building_map.json
data/exhibits.json
```

当前 `building_map.json` 包含：

- 124 个节点；
- 129 条边；
- 89 个房间节点；
- 12 个走廊节点；
- 4 条不可无障碍通行的楼梯相关边。

Excel 维护文件为：

```text
data/building_map_nodes.xlsx
```

它包含三张表：

- `nodes`：地点、房间、走廊和设施节点；
- `edges`：节点之间的通行边、距离和无障碍属性；
- `metadata`：建筑和楼层坐标说明。

从 JSON 导出 Excel：

```bash
python3 scripts/export_building_map_excel.py
```

从 Excel 导入 JSON：

```bash
python3 scripts/import_building_map_excel.py --input data/building_map_nodes.xlsx --output data/building_map.json
```

导入前可先 dry-run：

```bash
python3 scripts/import_building_map_excel.py --input data/building_map_nodes.xlsx --dry-run
```

端到端 API 验证：

```bash
python3 scripts/verify_api.py
```

## 接下来需要完成

### 固件

- [ ] 在 `xiaozhi-esp32` 中增加 `museum.visual_localize` MCP 工具；
- [ ] 增加 `museum.plan_route` MCP 工具；
- [ ] 增加可持久化的后端地址配置；
- [ ] 完成拍照、上传、解析定位结果和语音播报链路；
- [x] 编译、烧录并在立创 ESP32-S3 上完成基础启动测试。

### 后端与AI

- [ ] 确定实际使用的 VLM 服务和模型；
- [ ] 使用真实图片测试 VLM 返回格式和识别质量；
- [ ] 完善超时、重试和服务不可用提示；
- [ ] 接入 RAG 文档库，用于展品和场馆说明；
- [ ] 完成 ESP32 与电脑局域网联调。

### 现场数据

- [ ] 测量龙宾楼真实路线和节点距离；
- [ ] 为入口、路口、楼梯、电梯和展品采集多角度照片；
- [ ] 用真实视觉地标替换 `data/building_map.json` 中的模拟数据；
- [ ] 收集并核实展品资料；
- [ ] 编写准确的中英文导航指令；
- [ ] 测试相似走廊、楼梯和电梯的误识别情况。

### 演示与项目管理

- [x] 确认开发板、摄像头、串口和网络配置；
- [ ] 确定最终演示路线；
- [ ] 完成设备外壳、供电和佩戴方式；
- [ ] 准备进度报告、甘特图、测试数据和演示视频。

## 团队协作

开始开发前先更新代码：

```bash
git pull --rebase
```

每个功能使用独立分支，提交中不要包含 `build/`、`.venv/`、缓存文件或 API Key。详细配置、接口示例、数据格式和待补充信息见 [使用指南.md](使用指南.md)。
