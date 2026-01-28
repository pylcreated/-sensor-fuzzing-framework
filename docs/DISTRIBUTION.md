# 项目分发指南

> 工业传感器模糊测试框架文件获取方式

项目主页: [https://github.com/pylcreated/-sensor-fuzzing-framework](https://github.com/pylcreated/-sensor-fuzzing-framework)

## 📋 实际可用的获取方式

### 🌐 **方式1：Git 克隆（推荐）**

```bash
# 从 GitHub 克隆最新代码
git clone https://github.com/pylcreated/-sensor-fuzzing-framework.git
cd -sensor-fuzzing-framework

# 创建虚拟环境并安装
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# 运行框架
python -m sensor_fuzz
```

### 💻 **方式2：直接文件传输（离线场景）**

### 🐳 **方式2：Docker镜像分发**

```bash
# 如果有Docker镜像（需要先构建）
# 1. 从维护者获取 Dockerfile
# 2. 构建镜像
docker build -t sensor-fuzz-framework -f deploy/Dockerfile .

# 3. 运行容器
docker run -p 8000:8000 sensor-fuzz-framework
```

### 📦 **方式3：Python包分发**

```bash
# 1. 从维护者获取 wheel 文件
# sensor_fuzz_framework-0.1.0-py3-none-any.whl

# 2. 安装包
pip install sensor_fuzz_framework-0.1.0-py3-none-any.whl

# 3. 运行
sensor-fuzz
```

## 🔗 未来在线分发

### GitHub仓库设置
```bash
# 创建GitHub仓库后，其他用户可以：
git clone https://github.com/your-org/sensor-fuzzing-framework.git
```

### PyPI发布
```bash
# 发布到PyPI后，其他用户可以：
pip install sensor-fuzz-framework
```

### Docker Hub发布
```bash
# 发布镜像后，其他用户可以：
docker pull your-org/sensor-fuzz-framework:latest
```

## 📞 联系方式

如需获取项目文件，请联系项目维护者：
- 邮箱：your-email@example.com
- 内部系统：公司文件共享平台
- 物理媒介：U盘/移动硬盘传输

## ✅ 验证安装

安装完成后，运行以下命令验证：

```bash
# 1. 导入测试
python -c "import sensor_fuzz; print('✅ 模块导入成功')"

# 2. 功能测试
python -m sensor_fuzz --help

# 3. SIL合规测试
python sil_compliance_test.py
```

## 🚀 快速部署脚本

创建 `setup_and_run.ps1` (Windows) 或 `setup_and_run.sh` (Linux)：

```powershell
# Windows PowerShell脚本
Expand-Archive -Path sensor-fuzzing-framework.zip -DestinationPath .
cd sensor-fuzzing-framework
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m sensor_fuzz
```</content>
<parameter name="filePath">C:\Users\31601\Desktop\学年论文2\docs\DISTRIBUTION.md