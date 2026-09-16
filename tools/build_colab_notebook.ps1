param(
    [Parameter(Mandatory = $true)]
    [string]$SourceNotebook,
    [Parameter(Mandatory = $true)]
    [string]$SupportModule,
    [Parameter(Mandatory = $true)]
    [string]$OutputNotebook
)

$ErrorActionPreference = 'Stop'

function ConvertTo-SourceLines([string]$Text) {
    if ([string]::IsNullOrEmpty($Text)) { return @() }
    return @([regex]::Matches($Text, '.*?(?:\r\n|\n|\r)|.+$') | ForEach-Object {
        $_.Value -replace "`r`n", "`n" -replace "`r", "`n"
    })
}

function New-MarkdownCell([string]$Text) {
    return [ordered]@{
        cell_type = 'markdown'
        metadata = [ordered]@{}
        source = @(ConvertTo-SourceLines $Text)
    }
}

function New-CodeCell([string]$Text) {
    return [ordered]@{
        cell_type = 'code'
        execution_count = $null
        metadata = [ordered]@{}
        outputs = @()
        source = @(ConvertTo-SourceLines $Text)
    }
}

$source = Get-Content -LiteralPath $SourceNotebook -Raw -Encoding UTF8 | ConvertFrom-Json
$support = Get-Content -LiteralPath $SupportModule -Raw -Encoding UTF8

$intro = @'
# Qlib 量化投资工作流教程

> **Colab 学生版 · 从数据到回测的完整实践**

本教程以沪深 300 为例，带你完成 Qlib 初始化、数据探索、Alpha158 特征构建、LightGBM 训练、组合回测与绩效分析。练习单元格保留为学生作业，其余部分可以在 Google Colab 云端运行。

**建议使用方式**

1. Notebook 会连接到固定的 Colab 2026.07 运行时（Python 3.12）。
2. 在顶部菜单选择 **代码执行程序 → 全部运行**。
3. 首次运行会安装依赖并下载约 464 MB 的教学数据，通常需要数分钟。
4. 教学展示只读取小时间段样本，并复用同一个 Alpha158 数据集，适配 Colab 标准内存运行时。
5. 遇到“请补充代码”的单元格时完成练习，再继续后续章节。

> 数据仅用于教学演示，不构成投资建议。Notebook 基于 [Microsoft Qlib v0.9.7 官方示例](https://github.com/microsoft/qlib/blob/v0.9.7/examples/workflow_by_code.ipynb) 改编，沿用 MIT License。
'@

$environment = @'
## 1. 云端环境准备

Colab 会为每位学习者提供临时 Python 环境，因此不需要在本地安装 Qlib。下面的初始化单元格会：

- 固定使用 Colab 2026.07 运行时（Python 3.12），避免 Qlib 与 Python 3.13 不兼容；
- 安装与本教程验证版本一致的 Qlib、Plotly、Statsmodels 和 LightGBM；
- 从 Qlib README 当前推荐的社区镜像下载 A 股教学数据；
- 将数据解压到 Colab 的 `/content/qlib_data/cn_data`；
- 检查 Python 版本和数据目录是否就绪。

> Colab 虚拟机是临时的。运行时被回收后，依赖与数据需要重新准备。
> 本教程采用低内存流程。不要把示例中的小样本改为三份全量数据同时常驻内存。

**连接故障快速判断**

如果在执行任何单元格之前就出现 `/api/kernelspecs` 500，请先新建一个空白 Colab 并运行 `print("ok")`。空白 Notebook 也失败，说明是 Colab 会话、账号配额或网络连接问题，不是本教程代码；请删除当前运行时、重新连接 CPU 运行时后再试。错误链接包含临时运行时令牌，不要公开转发。
'@

$setup = @'
#@title 运行一次：安装依赖并准备 Qlib A 股数据
import os
import sys
import subprocess
from pathlib import Path

IN_COLAB = "google.colab" in sys.modules
SUPPORTED_PYTHON_MAX = (3, 12)
PINNED_PACKAGES = [
    "pyqlib==0.9.7",
    "plotly==6.6.0",
    "statsmodels==0.14.6",
    "lightgbm==4.6.0",
]

if IN_COLAB and sys.version_info[:2] > SUPPORTED_PYTHON_MAX:
    from IPython.display import HTML, display
    display(HTML("""
    <div style="padding:16px;border:2px solid #f59e0b;border-radius:12px;background:#fffbeb">
      <b>需要切换到 Python 3.12 运行时</b><br>
      当前 Colab 使用 Python 3.13，但 Qlib 0.9.7 尚未提供 Python 3.13 安装包。<br>
      请选择：<b>代码执行程序 → 更改运行时类型 → 运行时版本 → 2026.07</b>，保存后重新运行全部单元格。
    </div>
    """))
    raise RuntimeError(
        f"当前 Python {sys.version.split()[0]} 不受 Qlib 0.9.7 支持；请切换到 Colab 2026.07（Python 3.12）。"
    )

if IN_COLAB:
    print("正在安装教学环境……")
    install_result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", *PINNED_PACKAGES],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if install_result.returncode != 0:
        print("\n依赖安装日志（最后 40 行）：")
        print("\n".join(install_result.stdout.splitlines()[-40:]))
        raise RuntimeError("教学环境安装失败，请保留上方日志并联系教师。")
    QLIB_DATA_DIR = Path("/content/qlib_data/cn_data")
else:
    print("当前不是 Colab：请先执行 pip install -r requirements-colab.txt")
    QLIB_DATA_DIR = Path("./qlib_data/cn_data").resolve()

calendar_file = QLIB_DATA_DIR / "calendars" / "day.txt"
if IN_COLAB and not calendar_file.exists():
    archive = Path("/content/qlib_bin.tar.gz")
    QLIB_DATA_DIR.mkdir(parents=True, exist_ok=True)
    print("正在下载 Qlib A 股教学数据（约 464 MB）……")
    subprocess.run(
        [
            "wget", "-q", "--show-progress",
            "https://github.com/chenditc/investment_data/releases/latest/download/qlib_bin.tar.gz",
            "-O", str(archive),
        ],
        check=True,
    )
    subprocess.run(
        ["tar", "-xzf", str(archive), "-C", str(QLIB_DATA_DIR), "--strip-components=1"],
        check=True,
    )
    archive.unlink(missing_ok=True)

if not calendar_file.exists():
    raise FileNotFoundError(
        f"没有找到 Qlib 数据：{QLIB_DATA_DIR}\n"
        "在 Colab 中请重新运行本单元格；本地运行请按 README 准备数据。"
    )

print(f"Python: {sys.version.split()[0]}")
print(f"Qlib 数据目录: {QLIB_DATA_DIR}")
print("环境准备完成 ✓")
'@

$supportHeader = @'
# 教程辅助函数（从 support/Utils_backtest.py 内嵌，确保 Colab 单文件可运行）
'@

$handlerConfig = @'
# ==================== 低内存教学配置 ====================
# 保留完整的测试区间，但缩短训练与归一化区间。
# 这能显著减少 Alpha158 内部 raw / infer / learn 三份数据的常驻内存。
def show_process_memory(stage):
    """显示当前 Python 进程内存，便于区分内存终止与网络断连。"""
    try:
        import psutil
        rss_gb = psutil.Process().memory_info().rss / (1024 ** 3)
        print(f"[内存] {stage}: {rss_gb:.2f} GiB")
    except Exception:
        pass


TEACHING_SEGMENTS = {
    "train": ("2014-01-01", "2015-12-31"),
    "valid": ("2016-01-01", "2016-12-31"),
    "test": ("2017-01-01", "2020-08-01"),
}

data_handler_config = {
    "start_time": TEACHING_SEGMENTS["train"][0],
    "end_time": TEACHING_SEGMENTS["test"][1],
    "fit_start_time": TEACHING_SEGMENTS["train"][0],
    "fit_end_time": TEACHING_SEGMENTS["train"][1],
    "instruments": market,
}

print("低内存教学区间:", TEACHING_SEGMENTS)
'@

$datasetInit = @'
# ==================== 初始化数据集 ====================
# DatasetH 只引用上面已经创建的 Alpha158，不会再复制一套处理器。
from qlib.data.dataset import DatasetH

dataset = DatasetH(handler=handler, segments=TEACHING_SEGMENTS)

print("训练、验证、测试区间按时间顺序排列:")
for segment_name, segment_range in TEACHING_SEGMENTS.items():
    print(f"  {segment_name:>5}: {segment_range[0]} → {segment_range[1]}")
'@

$featureSample = @'
# 获取一个月的特征样本，避免在教学展示阶段复制整套 Alpha158 数据
sample_period = slice("2019-01-01", "2019-01-31")
features = handler.fetch(selector=sample_period, col_set="feature")
print("特征样本形状:", features.shape)
features.head()
'@

$labelSample = @'
# 获取与特征相同时间段的标签样本
labels = handler.fetch(selector=sample_period, col_set="label")
print("标签样本形状:", labels.shape)
labels.head()
'@

$dataModeSamples = @'
# ============================================
# 低内存方式：只比较一个月样本，不保留三份全量矩阵
# ============================================
import gc

sample_period = slice("2019-01-01", "2019-01-31")
mode_samples = {}

for data_key, label in (("raw", "原始"), ("infer", "推理"), ("learn", "学习")):
    sample = handler.fetch(selector=sample_period, data_key=data_key)
    mode_samples[data_key] = sample
    print(f"{label}数据样本形状: {sample.shape}")
    display(sample.head(2))

print("三种模式仅保留一个月样本；完整数据仍由 handler 统一管理。")
'@

$dataModeExercise = @'
##### **课后作业（2）：理解三种数据模式（raw / infer / learn）**

下面的 `mode_samples` 只包含一个月数据，足以比较三种处理模式，同时避免在 Colab 中保存三份约百万行的全量矩阵。

1. 比较三种样本的形状与缺失值数量；
2. 比较标签的均值和标准差；
3. 用文字说明 raw、infer、learn 分别适合什么场景。
'@

$dataModeExerciseCode = @'
# 对比三种小样本的差异
print("数据形状对比:")
for key, frame in mode_samples.items():
    print(f"{key:>5}: {frame.shape}")

print("\n缺失值对比:")
# TODO: 请补充代码，分别计算三种样本的缺失值数量

print("\n标签统计对比:")
# TODO: 请补充代码，比较三种样本中 LABEL0 的均值与标准差
'@

$datasetSample = @'
# ============================================
# 1. 查看训练期内一个月的小样本
# ============================================
sample_train_period = slice("2014-12-01", "2014-12-31")

train_learn_sample = dataset.prepare(sample_train_period, data_key="learn")
print("学习数据样本形状:", train_learn_sample.shape)
display(train_learn_sample.head())

train_raw_sample = dataset.prepare(sample_train_period, data_key="raw")
print("原始数据样本形状:", train_raw_sample.shape)
display(train_raw_sample.head())

del train_learn_sample, train_raw_sample
gc.collect()
'@

$segmentShapes = @'
# ============================================
# 2. 只读取标签列检查时间段形状
# ============================================
segment_shapes = {}
for segment in ("train", "valid", "test"):
    segment_labels = dataset.prepare(segment, col_set="label")
    segment_shapes[segment] = (len(segment_labels), len(handler.get_cols(col_set="feature")))
    del segment_labels
    gc.collect()

print("\n数据集划分:")
print(f"训练集: {segment_shapes['train']}")
print(f"验证集: {segment_shapes['valid']}")
print(f"测试集: {segment_shapes['test']}")
'@

$featureLabelSamples = @'
# ============================================
# 3. 使用小时间段查看特征和标签
# ============================================
sample_train_period = slice("2014-12-01", "2014-12-31")

features_df = dataset.prepare(sample_train_period, col_set="feature")
print("\n特征样本形状:", features_df.shape)
display(features_df.head())

label_df = dataset.prepare(sample_train_period, col_set="label")
print("\n标签样本形状:", label_df.shape)
display(label_df.head())
'@

$trainingCell = @'
# 训练前释放教学展示阶段的 DataFrame，降低 Colab 内存峰值
import gc

for variable_name in [
    "features", "labels", "mode_samples",
    "features_df", "label_df", "segment_shapes",
    "train_df", "valid_df", "test_df",
    "raw_data", "infer_data", "learn_data",
]:
    globals().pop(variable_name, None)

# raw 数据已经完成教学展示，训练和预测只需要 learn / infer。
# 删除处理器内部 raw 表可再释放一份完整 Alpha158 数据。
if hasattr(handler, "_data"):
    del handler._data

gc.collect()
show_process_memory("训练前（已清理 raw 与演示变量）")

# 使用 Qlib workflow 记录训练实验
with R.start(experiment_name="train_model"):
    R.log_params(**flatten_dict(task))

    # 复用第 4 节创建的 dataset，不再初始化第二套 Alpha158
    model.fit(dataset)

    # 训练结束后释放 LightGBM 的训练矩阵，只保留可预测的 Booster
    if hasattr(model, "model") and hasattr(model.model, "free_dataset"):
        model.model.free_dataset()
    gc.collect()
    show_process_memory("模型训练后")

    R.save_objects(trained_model=model)
    rid = R.get_recorder().id

print(f"模型训练完成，Recorder ID: {rid}")
'@

$sqliteInit = @'
mlflow_db = (Path("/content") if IN_COLAB else Path.cwd()) / "qlib_mlflow.db"
exp_manager = {
    "class": "MLflowExpManager",
    "module_path": "qlib.workflow.expm",
    "kwargs": {
        "uri": f"sqlite:///{mlflow_db.resolve().as_posix()}",
        "default_exp_name": "Experiment",
    },
}

qlib.init(provider_uri=provider_uri, region=REG_CN, exp_manager=exp_manager)
print(f"MLflow 实验数据库: {mlflow_db}")
'@

$newCells = [System.Collections.ArrayList]::new()
[void]$newCells.Add((New-MarkdownCell $intro))
[void]$newCells.Add((New-MarkdownCell $environment))
[void]$newCells.Add((New-CodeCell $setup))
[void]$newCells.Add((New-CodeCell ($supportHeader + "`n" + $support)))

# 原 notebook 的 0-3 号单元格由上面的 Colab 专用说明替代。
for ($i = 4; $i -lt $source.cells.Count; $i++) {
    $cell = $source.cells[$i]
    $text = ($cell.source -join '')

    if ($cell.cell_type -eq 'code') {
        $text = $text.Replace("provider_uri =  './qlib_data/cn_data' # target_dir", "provider_uri = str(QLIB_DATA_DIR)  # Colab 与本地共用")
        $text = $text.Replace('stock_features_path = Path("./qlib_data/cn_data/features/sh600000")', 'stock_features_path = QLIB_DATA_DIR / "features" / "sh600000"')
        $text = $text.Replace('"num_threads": 20,', '"num_threads": max(1, min(4, os.cpu_count() or 2)),')
        $text = $text.Replace('qlib.init(provider_uri=provider_uri, region=REG_CN)', $sqliteInit)

        if ($text -match '# 获取实际的 feaure 数据') { $text = $featureSample }
        if ($text -match '# 获取实际的 label 数据') { $text = $labelSample }
        if ($text -match '# ==================== 数据处理器配置') { $text = $handlerConfig }
        if ($text -match 'handler = Alpha158\(\*\*data_handler_config\)') {
            $text = $text.Replace('handler = Alpha158(**data_handler_config)', "handler = Alpha158(**data_handler_config)`nshow_process_memory(`"Alpha158 初始化后`")")
        }
        if ($text -match '# 直接从 DataHandler 获取三种数据') { $text = $dataModeSamples }
        if ($text -match '# 对比三种数据的差异') { $text = $dataModeExerciseCode }
        if ($text -match '# ==================== 初始化数据集') { $text = $datasetInit }
        if ($text -match '# 1\. 查看单个时间段的数据') { $text = $datasetSample }
        if ($text -match '# 2\. 查看多个时间段的数据') { $text = $segmentShapes }
        if ($text -match '# 3\. 查看特征和标签') { $text = $featureLabelSamples }

        # task 中的数据集配置与前面的低内存教学区间保持一致。
        if ($text -match '# 使用配置字典定义模型和数据集参数') {
            $text = $text.Replace('"train": ("2008-01-01", "2014-12-31")', '"train": TEACHING_SEGMENTS["train"]')
            $text = $text.Replace('"valid": ("2015-01-01", "2016-12-31")', '"valid": TEACHING_SEGMENTS["valid"]')
            $text = $text.Replace('"test": ("2017-01-01", "2020-08-01")', '"test": TEACHING_SEGMENTS["test"]')
            $text = $text.Replace('# 训练集：7年数据', '# 训练集：2年低内存教学数据')
            $text = $text.Replace('# 验证集：2年数据（用于早停）', '# 验证集：1年数据（用于早停）')
        }

        # task 中保留数据集配置用于实验记录，但训练时复用第 4 节已创建的 dataset。
        $text = $text.Replace('dataset = init_instance_by_config(task["dataset"])', 'print("复用第 4 节已创建的 DatasetH，避免重复加载 Alpha158。")')

        if ($text -match 'with R\.start\(experiment_name="train_model"\)' -and $text -match 'model\.fit\(dataset\)') {
            $text = $trainingCell
        }

        if ($text -match 'from Utils_backtest import \*') {
            $text = $text.Replace("import sys`nfrom pathlib import Path`n`n# 导入回测分析模块`nsys.path.insert(0, str(Path.cwd() / 'py'))`nfrom Utils_backtest import *`n", "# 回测分析辅助函数已在环境准备部分内嵌，无需额外文件。`n")
        }

        if ($text -match 'ex_return_wo_cost\s*=\s*\r?\n') {
            $text = @'
def analyze_excess_return(report_normal_df: pd.DataFrame) -> pd.DataFrame:
    """课后作业：计算累计、均值与波动率等超额收益统计。"""
    # TODO: 请补充代码。返回一个以“指标”为索引、包含“数值”列的 DataFrame。
    return pd.DataFrame(columns=["数值"]).rename_axis("指标")
'@
        }

        if ($text -match 'max_drawdown\s*=\s*\r?\n') {
            $text = @'
def analyze_excess_return_drawdown(report_normal_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """课后作业：计算超额收益最大回撤及其起止日期。"""
    # TODO: 请补充代码。当前占位返回值保证“全部运行”不会出现语法错误。
    empty = pd.DataFrame(columns=["数值"]).rename_axis("指标")
    return {"without_cost": empty}
'@
        }

        $cell.execution_count = $null
        $cell.outputs = @()
    }

    if ($cell.cell_type -eq 'markdown' -and $text -match '课后作业（2）：理解三种数据模式') {
        $text = $dataModeExercise
    }

    $cell.source = @(ConvertTo-SourceLines $text)
    [void]$newCells.Add($cell)
}

for ($i = 0; $i -lt $newCells.Count; $i++) {
    $cellId = 'qlib-{0:d3}' -f $i
    if ($newCells[$i] -is [System.Collections.IDictionary]) {
        $newCells[$i]['id'] = $cellId
    }
    else {
        $newCells[$i] | Add-Member -NotePropertyName id -NotePropertyValue $cellId -Force
    }
}

$output = [ordered]@{
    cells = @($newCells)
    metadata = [ordered]@{
        accelerator = 'CPU'
        colab = [ordered]@{
            name = 'Qlib量化投资工作流教程_Colab学生版.ipynb'
            provenance = @()
            runtime_attributes = [ordered]@{
                runtime_version = '2026.07'
            }
        }
        kernelspec = [ordered]@{
            display_name = 'Python 3'
            language = 'python'
            name = 'python3'
        }
        language_info = [ordered]@{
            name = 'python'
            version = '3.12'
        }
    }
    nbformat = 4
    nbformat_minor = 5
}

$outputDirectory = Split-Path -Parent $OutputNotebook
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
$json = $output | ConvertTo-Json -Depth 100
[System.IO.File]::WriteAllText($OutputNotebook, $json, [System.Text.UTF8Encoding]::new($false))
Write-Output "Created $OutputNotebook"

$projectRoot = Split-Path -Parent $PSScriptRoot
$downloadDirectory = Join-Path $projectRoot 'docs\downloads'
$downloadNotebook = Join-Path $downloadDirectory 'Qlib量化投资工作流教程_Colab学生版.ipynb'
New-Item -ItemType Directory -Path $downloadDirectory -Force | Out-Null
Copy-Item -LiteralPath $OutputNotebook -Destination $downloadNotebook -Force
Write-Output "Synced download copy to $downloadNotebook"
