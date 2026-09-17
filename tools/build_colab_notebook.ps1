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
$support = [regex]::Replace(
    $support,
    '(?m)^(\s*)([A-Za-z_][A-Za-z0-9_]*(?:\[[^\r\n]+\])?)\.show\(\)\s*$',
    '$1show_plotly($2)'
)

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
- 安装与本教程验证版本一致的 Qlib、Statsmodels 和 LightGBM，并把 Plotly 放在 `/content` 隔离目录中；
- 从 Qlib README 当前推荐的社区镜像下载 A 股教学数据；
- 将数据解压到 Colab 的 `/content/qlib_data/cn_data`；
- 检查 Python 版本和数据目录是否就绪。

> Colab 虚拟机是临时的。运行时被回收后，依赖与数据需要重新准备。
> 本教程采用低内存流程。不要把示例中的小样本改为三份全量数据同时常驻内存。

**连接故障快速判断**

如果在执行任何单元格之前就出现 `/api/kernelspecs` 500，请先新建一个空白 Colab 并运行 `print("ok")`。空白 Notebook 也失败，说明是 Colab 会话、账号配额或网络连接问题，不是本教程代码；请删除当前运行时、重新连接 CPU 运行时后再试。错误链接包含临时运行时令牌，不要公开转发。
'@

$setup = @'
#@title 运行一次：准备 Qlib 教学环境
import sys
import subprocess
from pathlib import Path
from IPython.display import display

if sys.version_info[:2] > (3, 12):
    raise RuntimeError(
        "请将 Colab 运行时版本切换为 2026.07（Python 3.12）后重新运行。"
    )

QLIB_DATA_DIR = Path("/content/qlib_data/cn_data")
PLOTLY_DIR = Path("/content/qlib_plotly_runtime")

print("[1/3] 安装 Python 依赖……")
subprocess.check_call([
    sys.executable, "-m", "pip", "install", "-q", "--no-cache-dir",
    "pyqlib==0.9.7", "statsmodels==0.14.6", "lightgbm==4.6.0",
])

# Plotly 单独安装到 /content，避开 Colab 中可能损坏的系统包。
subprocess.check_call([
    sys.executable, "-m", "pip", "install", "-q", "--no-cache-dir",
    "--upgrade", "--target", str(PLOTLY_DIR), "plotly==6.6.0",
])
sys.path.insert(0, str(PLOTLY_DIR))

# 清除失败导入留下的缓存，再从隔离目录加载 Plotly。
for module_name in list(sys.modules):
    if module_name == "plotly" or module_name.startswith(("plotly.", "_plotly_utils")):
        sys.modules.pop(module_name, None)

calendar_file = QLIB_DATA_DIR / "calendars" / "day.txt"
print("[2/3] 检查 Qlib A 股数据……")
if not calendar_file.exists():
    archive = Path("/content/qlib_bin.tar.gz")
    QLIB_DATA_DIR.mkdir(parents=True, exist_ok=True)
    print("下载教学数据（约 464 MB）……")
    subprocess.check_call([
        "wget", "-q", "--show-progress",
        "https://github.com/chenditc/investment_data/releases/latest/download/qlib_bin.tar.gz",
        "-O", str(archive),
    ])
    subprocess.check_call(
        ["tar", "-xzf", str(archive), "-C", str(QLIB_DATA_DIR), "--strip-components=1"],
    )
    archive.unlink(missing_ok=True)

if not calendar_file.exists():
    raise FileNotFoundError(f"Qlib 数据准备失败：{QLIB_DATA_DIR}")

print("[3/3] 配置 Plotly……")
import plotly
import plotly.io as pio
pio.renderers.default = "colab"

def show_plotly(figure):
    figure.show(renderer="colab", config={"responsive": True})

print(f"Python: {sys.version.split()[0]}")
print(f"Plotly: {plotly.__version__}")
print(f"Qlib 数据目录: {QLIB_DATA_DIR}")
print("环境准备完成 ✓")
'@

$supportHeader = @'
# 教程辅助函数（从 support/Utils_backtest.py 内嵌，确保 Colab 单文件可运行）
'@

$handlerConfig = @'
# ==================== 低内存教学配置 ====================
# 正式训练只覆盖 2017–2020；raw / infer / learn 教学另用一个月的小处理器。
# 正式处理器启用 drop_raw，只保留训练和预测所需的数据。
def show_process_memory(stage):
    """显示当前 Python 进程内存，便于区分内存终止与网络断连。"""
    try:
        import psutil
        rss_gb = psutil.Process().memory_info().rss / (1024 ** 3)
        print(f"[内存] {stage}: {rss_gb:.2f} GiB")
    except Exception:
        pass


TEACHING_SEGMENTS = {
    "train": ("2017-01-01", "2017-12-31"),
    "valid": ("2018-01-01", "2018-12-31"),
    "test": ("2019-01-01", "2020-08-01"),
}

# 免费 Colab 的组合回测只使用 2019 年。模型测试集仍保留到 2020-08，
# 但交易所行情缓存的时间范围更短，足以完成课堂演示和绩效分析。
LOW_MEMORY_BACKTEST_END = "2019-12-31"

demo_handler_config = {
    "start_time": "2019-01-01",
    "end_time": "2019-01-31",
    "fit_start_time": "2019-01-01",
    "fit_end_time": "2019-01-31",
    "instruments": market,
}

data_handler_config = {
    "start_time": TEACHING_SEGMENTS["train"][0],
    "end_time": TEACHING_SEGMENTS["test"][1],
    "fit_start_time": TEACHING_SEGMENTS["train"][0],
    "fit_end_time": TEACHING_SEGMENTS["train"][1],
    "instruments": market,
    "drop_raw": True,
}

print("低内存教学区间:", TEACHING_SEGMENTS)
'@

$handlerInit = @'
# ==================== 初始化一个月的演示处理器 ====================
from qlib.contrib.data.handler import Alpha158

# 这个小处理器只负责讲解因子与 raw / infer / learn，不参与正式训练。
demo_handler = Alpha158(**demo_handler_config)
handler = demo_handler
show_process_memory("一个月演示处理器初始化后")
'@

$datasetInit = @'
# ==================== 初始化数据集 ====================
# 先释放一个月的演示处理器，再创建启用 drop_raw 的正式处理器。
import gc

for variable_name in ["features", "labels", "mode_samples"]:
    globals().pop(variable_name, None)

del handler, demo_handler
gc.collect()

handler = Alpha158(**data_handler_config)
show_process_memory("正式 Alpha158 初始化后（drop_raw=True）")

# DatasetH 只引用这一个正式处理器，不会再复制一套 Alpha158。
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

下面的 `mode_samples` 来自独立的一个月演示处理器，足以比较三种模式；进入正式训练前会整体释放。

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
sample_train_period = slice("2017-12-01", "2017-12-31")

train_learn_sample = dataset.prepare(sample_train_period, data_key="learn")
print("学习数据样本形状:", train_learn_sample.shape)
display(train_learn_sample.head())

train_infer_sample = dataset.prepare(sample_train_period, data_key="infer")
print("推理数据样本形状:", train_infer_sample.shape)
display(train_infer_sample.head())

del train_learn_sample, train_infer_sample
gc.collect()
'@

$segmentShapes = @'
# ============================================
# 2. 只读取标签列检查时间段形状
# ============================================
segment_shapes = {}
for segment in ("train", "valid", "test"):
    segment_labels = dataset.prepare(segment, col_set="label")
    segment_shapes[segment] = (len(segment_labels), len(factor_dict))
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
sample_train_period = slice("2017-12-01", "2017-12-31")

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

# 正式处理器已启用 drop_raw；保留兼容性检查，确保 raw 不再常驻。
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

    rid = R.get_recorder().id

print(f"模型训练完成，Recorder ID: {rid}")
'@

$lightweightBacktestExplanation = @'
### 6.2 免费 Colab：轻量 TopK 回测

完整的 `PortAnaRecord` 会创建交易所、行情缓存、账户和逐日成交对象，适合本地或有保证的运行时。免费 Colab 的默认流程改为等价的教学近似：

1. 模型只生成一次预测，并立即释放 Alpha158 数据集；
2. 仅按预测中实际出现的股票读取 2019 年单列未来收益，不创建交易所缓存；
3. 每日保留上一期较高分股票、淘汰 5 只，再补足 Top 50；
4. 用等权收益、换手率和交易费生成与 Qlib 报告兼容的四列结果。

后续绩效图、风险分析、IC 和分组收益单元格无需修改。这里的结果用于课堂理解信号到组合的连接，不模拟涨跌停、停牌和最小成交金额；需要这些成交细节时，再在本地或高内存环境运行上一节给出的完整 `PortAnaRecord` 配置。
'@

$backtestWorkflow = @'
# ==================== 免费 Colab 轻量 TopK 回测 ====================
# 不创建 Qlib Exchange / PortAnaRecord，避免免费运行时的行情缓存峰值。
from qlib.data import D
from qlib.backtest.position import Position
from qlib.contrib.evaluate import risk_analysis

TOPK = 50
N_DROP = 5
OPEN_COST = 0.0005
CLOSE_COST = 0.0015
LABEL_EXPR = "Ref($close, -2) / Ref($close, -1) - 1"

print("[1/4] 生成并保存测试集预测……", flush=True)
show_process_memory("预测前")

with R.start(experiment_name="backtest_analysis"):
    recorder = R.get_recorder()
    ba_rid = recorder.id

    pred_df = model.predict(dataset)
    if isinstance(pred_df, pd.Series):
        pred_df = pred_df.to_frame("score")
    else:
        pred_df.columns = ["score"]

    # 学生版回测只保留 2019 年，显著缩小后续标签和持仓计算。
    pred_dates = pred_df.index.get_level_values("datetime")
    pred_df = pred_df.loc[pred_dates <= pd.Timestamp(LOW_MEMORY_BACKTEST_END)].copy()
    backtest_codes = sorted(pred_df.index.get_level_values("instrument").unique())
    recorder.save_objects(**{"pred.pkl": pred_df})

    print("[2/4] 释放模型和 Alpha158，再读取单列未来收益……", flush=True)
    for variable_name in ["model", "dataset", "handler", "task"]:
        globals().pop(variable_name, None)
    gc.collect()
    show_process_memory("释放 Alpha158 后")

    # 直接从 Qlib 行情读取一个表达式列，不再让 DatasetH 复制完整测试集。
    label_df = D.features(
        backtest_codes,
        [LABEL_EXPR],
        start_time=TEACHING_SEGMENTS["test"][0],
        end_time=LOW_MEMORY_BACKTEST_END,
        freq="day",
        disk_cache=False,
    )
    label_df.columns = ["label"]
    label_df = label_df.reorder_levels(["datetime", "instrument"]).sort_index()

    print("[3/4] 计算 TopK 持仓、换手率和组合收益……", flush=True)
    signal_and_return = pd.concat([pred_df, label_df], axis=1, join="inner").dropna()
    daily_returns = []
    daily_turnover = []
    trade_dates = []
    positions = {}
    previous_holdings = []

    for trade_date, daily_frame in signal_and_return.groupby(level="datetime", sort=True):
        daily_frame = daily_frame.droplevel("datetime").sort_values("score", ascending=False)
        ranked_codes = daily_frame.index.tolist()
        ranked_set = set(ranked_codes)

        # 保留上一期仍可交易且分数较高的股票，每天最多淘汰 N_DROP 只。
        surviving = [code for code in previous_holdings if code in ranked_set]
        surviving.sort(key=lambda code: daily_frame.at[code, "score"], reverse=True)
        keep_count = max(0, min(len(surviving), TOPK - N_DROP))
        holdings = surviving[:keep_count]
        holdings.extend(code for code in ranked_codes if code not in holdings)
        holdings = holdings[:TOPK]

        if not holdings:
            continue

        current_set = set(holdings)
        if previous_holdings:
            turnover = 1.0 - len(current_set.intersection(previous_holdings)) / len(holdings)
        else:
            turnover = 1.0

        portfolio_return = float(daily_frame.loc[holdings, "label"].mean())
        weight = 1.0 / len(holdings)
        position_dict = {
            code: {"amount": weight, "price": 1.0, "weight": weight}
            for code in holdings
        }
        positions[pd.Timestamp(trade_date)] = Position(cash=0.0, position_dict=position_dict)

        trade_dates.append(pd.Timestamp(trade_date))
        daily_returns.append(portfolio_return)
        daily_turnover.append(turnover)
        previous_holdings = holdings

    report_normal_df = pd.DataFrame(
        {"return": daily_returns, "turnover": daily_turnover},
        index=pd.DatetimeIndex(trade_dates, name="date"),
    )
    report_normal_df["cost"] = report_normal_df["turnover"] * (OPEN_COST + CLOSE_COST)
    if len(report_normal_df):
        report_normal_df.iloc[0, report_normal_df.columns.get_loc("cost")] = OPEN_COST

    # 基准使用与 Alpha158 标签相同的未来收益口径，只读取一个指数、一列数据。
    benchmark_df = D.features(
        [benchmark],
        [LABEL_EXPR],
        start_time=TEACHING_SEGMENTS["test"][0],
        end_time=LOW_MEMORY_BACKTEST_END,
        freq="day",
        disk_cache=False,
    )
    benchmark_return = benchmark_df.iloc[:, 0].droplevel("instrument")
    benchmark_return.index = pd.DatetimeIndex(benchmark_return.index)
    report_normal_df["bench"] = benchmark_return.reindex(report_normal_df.index).fillna(0.0)
    report_normal_df = report_normal_df[["return", "cost", "bench", "turnover"]]

    print("[4/4] 生成风险指标并保存兼容的教学产物……", flush=True)
    analysis_df = pd.concat(
        {
            "excess_return_without_cost": risk_analysis(
                report_normal_df["return"] - report_normal_df["bench"], freq="1day"
            ),
            "excess_return_with_cost": risk_analysis(
                report_normal_df["return"] - report_normal_df["bench"] - report_normal_df["cost"],
                freq="1day",
            ),
        }
    )
    recorder.save_objects(
        artifact_path="portfolio_analysis",
        **{
            "report_normal_1day.pkl": report_normal_df,
            "positions_normal_1day.pkl": positions,
            "port_analysis_1day.pkl": analysis_df,
        },
    )

    # Colab 免费运行时可能在任务完成后回收整台虚拟机，因此把第 7 节所需
    # 数据保存为浏览器下载文件。持仓仅保存股票代码，恢复时再重建 Position。
    import gzip
    import pickle

    checkpoint_path = Path("/content/qlib_analysis_checkpoint.pkl.gz") if IN_COLAB else Path(
        "qlib_analysis_checkpoint.pkl.gz"
    )
    portable_positions = {
        pd.Timestamp(date).isoformat(): position.get_stock_list()
        for date, position in positions.items()
    }
    checkpoint = {
        "schema_version": 1,
        "pred_df": pred_df,
        "label_df": label_df,
        "report_normal_df": report_normal_df,
        "positions": portable_positions,
        "analysis_df": analysis_df,
    }
    with gzip.open(checkpoint_path, "wb", compresslevel=6) as checkpoint_file:
        pickle.dump(checkpoint, checkpoint_file, protocol=pickle.HIGHEST_PROTOCOL)

    print(f"分析检查点已生成：{checkpoint_path.name}", flush=True)
    if IN_COLAB:
        from google.colab import files

        print("浏览器将下载检查点；如果运行时被回收，可在训练回测篇的 6.3 节上传它。", flush=True)
        files.download(str(checkpoint_path))

    del signal_and_return, benchmark_df
    gc.collect()
    show_process_memory("轻量回测完成")

print(f"轻量回测完成，共 {len(report_normal_df)} 个交易日，Recorder ID: {ba_rid}")
'@

$analysisRecorderCell = @'
from qlib.contrib.report import analysis_model, analysis_position

required_analysis_objects = [
    "pred_df", "label_df", "report_normal_df", "positions", "analysis_df"
]
missing_analysis_objects = [name for name in required_analysis_objects if name not in globals()]
if missing_analysis_objects:
    raise RuntimeError(
        "当前运行时没有分析数据。请从训练流程重新运行，"
        "或在训练回测篇的 6.3 节上传 qlib_analysis_checkpoint.pkl.gz。"
    )

print("轻量回测结果已在内存中，可直接进行绩效与 IC 分析。")
'@

$predictionOverviewCell = @'
# ==================== 查看预测数据 ====================
# pred_df 已由轻量回测生成，或由分析检查点恢复，不再访问 MLflow。
pred_info = pd.DataFrame({
    "属性": [
        "数据形状", "列名", "索引层级", "日期范围（开始）", "日期范围（结束）", "股票数量"
    ],
    "值": [
        f"{pred_df.shape[0]:,} × {pred_df.shape[1]}",
        ", ".join(pred_df.columns.tolist()),
        ", ".join(pred_df.index.names),
        str(pred_df.index.get_level_values("datetime").min()),
        str(pred_df.index.get_level_values("datetime").max()),
        f"{len(pred_df.index.get_level_values('instrument').unique()):,}",
    ],
}).set_index("属性")

print("\n【预测数据概览】")
display(pred_info)
print("\n【预测结果预览（前5行）】")
display(pred_df.head(5))
'@

$backtestDataCell = @'
# ==================== 查看回测数据 ====================
# 报告、持仓和风险分析已在内存中，或由分析检查点恢复。
data_info = get_backtest_data_info(report_normal_df, positions, analysis_df)

print("\n【回测报告信息】")
display(data_info["report_info"])
print("\n【回测报告预览（前5行）】")
display(report_normal_df.head(5))
print("\n【回测报告统计摘要】")
display(report_normal_df.describe().style.format("{:.4f}"))
'@

# 分成两个独立运行时后，训练回测篇可以恢复 Qlib 标准的
# SignalRecord + PortAnaRecord 流程；仍保留缩短区间和单一 Alpha158。
$standardBacktestExplanation = @'
### 6.2 Qlib 低内存标准回测流程

训练回测篇从全新运行时开始，并保留 Qlib 的标准组合回测组件：

1. 模型只预测一次，将测试集得分保存为当前实验的 `pred.pkl`；
2. `PortAnaRecord` 读取预测信号并运行 `TopkDropoutStrategy`；
3. `SimulatorExecutor` 按收盘价、涨跌停和交易成本模拟逐日成交；
4. 结果保存在当前 Qlib 实验记录中，紧接着由第 7 节读取分析。

这里不调用 `SignalRecord.generate()`：Qlib 0.9.7 会在预测后强制读取 raw 标签，而低内存处理器已设置 `drop_raw=True`。本节直接保存同样的预测产物，标签从已有的 infer 数据中单独读取，避免恢复整份 raw 数据。训练、验证和测试区间继续使用课堂轻量范围，组合回测只覆盖 2019 年，并限制为预测结果中实际出现的股票。
'@

$standardBacktestWorkflow = @'
# ==================== Qlib 低内存信号与标准组合回测 ====================
import gc

# SignalRecord.generate() 会额外读取 raw 标签，与 drop_raw=True 冲突。
# 这里执行它的核心步骤：预测一次，并把 pred.pkl 保存到当前 recorder。
print("[1/4] 从 infer 数据保留测试集标签……", flush=True)
label_df = dataset.prepare("test", col_set="label", data_key="infer")
label_df.columns = ["label"]
label_dates = label_df.index.get_level_values("datetime")
label_df = label_df.loc[label_dates <= pd.Timestamp(LOW_MEMORY_BACKTEST_END)].copy()
print(f"已保留 {len(label_df):,} 行标签。", flush=True)

print("[2/4] 模型生成测试集预测……", flush=True)
show_process_memory("预测前")
pred_df = model.predict(dataset)
if isinstance(pred_df, pd.Series):
    pred_df = pred_df.to_frame("score")
pred_dates = pred_df.index.get_level_values("datetime")
pred_df = pred_df.loc[pred_dates <= pd.Timestamp(LOW_MEMORY_BACKTEST_END)].copy()
backtest_codes = sorted(pred_df.index.get_level_values("instrument").unique())
port_analysis_config["backtest"]["exchange_kwargs"]["codes"] = backtest_codes

with R.start(experiment_name="backtest_analysis"):
    recorder = R.get_recorder()
    ba_rid = recorder.id
    recorder.save_objects(**{"pred.pkl": pred_df})
    print(f"预测已保存：{len(pred_df):,} 行，{len(backtest_codes)} 只股票。", flush=True)

    print("[3/4] 释放模型与 Alpha158，准备标准组合回测……", flush=True)
    del pred_df
    for variable_name in ["model", "dataset", "handler", "task"]:
        globals().pop(variable_name, None)
    gc.collect()
    show_process_memory("组合回测前")

    print("[4/4] PortAnaRecord 执行 2019 年 TopK 回测……", flush=True)
    par = PortAnaRecord(recorder, port_analysis_config, "day")
    par.generate()
    del par
    gc.collect()
    show_process_memory("组合回测完成")

print(f"标准回测完成，Recorder ID: {ba_rid}")
'@

$standardAnalysisRecorderCell = @'
from qlib.contrib.report import analysis_model, analysis_position

# 从当前回测实验读取预测、组合报告、持仓和风险分析。
recorder = R.get_recorder(
    recorder_id=ba_rid,
    experiment_name="backtest_analysis",
)
print(recorder)
'@

$standardPredictionOverviewCell = @'
# ==================== 加载预测结果 ====================
pred_df = recorder.load_object("pred.pkl")
pred_dates = pred_df.index.get_level_values("datetime")
pred_df = pred_df.loc[pred_dates <= pd.Timestamp(LOW_MEMORY_BACKTEST_END)].copy()

pred_info = pd.DataFrame({
    "属性": [
        "数据形状", "列名", "索引名称", "日期范围（开始）", "日期范围（结束）", "股票数量"
    ],
    "值": [
        f"{pred_df.shape[0]:,} × {pred_df.shape[1]}",
        ", ".join(pred_df.columns.tolist()),
        ", ".join(pred_df.index.names),
        str(pred_df.index.get_level_values("datetime").min()),
        str(pred_df.index.get_level_values("datetime").max()),
        f"{len(pred_df.index.get_level_values('instrument').unique()):,}",
    ],
}).set_index("属性")

print("\n【预测数据概览】")
display(pred_info)
print("\n【预测数据预览（前5行）】")
display(pred_df.head(5))
'@

$standardBacktestDataCell = @'
# ==================== 加载标准回测数据 ====================
report_normal_df, positions, analysis_df = load_backtest_data(
    recorder,
    analysis_freq="1day",
)
data_info = get_backtest_data_info(report_normal_df, positions, analysis_df)

print("\n【回测报告信息】")
display(data_info["report_info"])
print("\n【回测报告预览（前5行）】")
display(report_normal_df.head(5))
print("\n【回测报告统计摘要】")
display(report_normal_df.describe().style.format("{:.4f}"))
'@

$standardLabelCell = @'
# 预测前已从 infer 数据保留单列标签；完整 Alpha158 已在回测前释放。
if "label_df" not in globals():
    raise RuntimeError("请先顺序运行第 6.2 节的标准回测单元格。")

print(f"标签数据形状: {label_df.shape}")
'@

$homework3Markdown = @'
##### **课后作业（3）：计算累计超额收益率**

本题已经给出输入检查、无成本日超额收益和结果表格。请只补全代码中标记的 **3 个核心计算**：

1. 含成本日超额收益；
2. 不含成本累计超额收益；
3. 含成本累计超额收益。

累计收益使用 `cumsum()`，完成后运行下一单元格中的检查代码。
'@

$homework3Code = @'
def analyze_excess_return(report_normal_df: pd.DataFrame) -> pd.DataFrame:
    """计算超额收益统计；学生只需补全 3 个核心公式。"""
    required_columns = {"return", "bench", "cost"}
    missing_columns = required_columns.difference(report_normal_df.columns)
    if missing_columns:
        raise KeyError(f"回测报告缺少列: {sorted(missing_columns)}")

    # 已给出：不含成本的日超额收益 = 策略收益 - 基准收益
    excess_return_without_cost = report_normal_df["return"] - report_normal_df["bench"]

    # TODO 1：含成本的日超额收益 = 策略收益 - 基准收益 - 交易成本
    excess_return_with_cost = ...

    # TODO 2：用 cumsum() 计算不含成本的累计超额收益序列
    cumulative_excess_without_cost = ...

    # TODO 3：用 cumsum() 计算含成本的累计超额收益序列
    cumulative_excess_with_cost = ...

    if any(
        value is Ellipsis
        for value in (
            excess_return_with_cost,
            cumulative_excess_without_cost,
            cumulative_excess_with_cost,
        )
    ):
        raise NotImplementedError("请补全课后作业（3）的 3 个 TODO。")

    # 结果表结构已给出，不需要修改。
    result = pd.DataFrame(
        {
            "数值": [
                cumulative_excess_without_cost.iloc[-1],
                cumulative_excess_with_cost.iloc[-1],
                excess_return_without_cost.mean(),
                excess_return_with_cost.mean(),
                excess_return_without_cost.std(),
                excess_return_with_cost.std(),
            ]
        },
        index=[
            "最终累计超额收益（不含成本）",
            "最终累计超额收益（含成本）",
            "日均超额收益（不含成本）",
            "日均超额收益（含成本）",
            "日超额收益标准差（不含成本）",
            "日超额收益标准差（含成本）",
        ],
    )
    result.index.name = "指标"
    return result


# 完成 3 个 TODO 后取消下面代码的注释进行检查：
# excess_return_stats = analyze_excess_return(report_normal_df)
# display(excess_return_stats.style.format("{:.6f}"))
'@

$homework4Markdown = @'
##### **课后作业（4）：计算超额收益最大回撤（含成本）**

本题已经给出含成本超额收益、累计收益、回撤起止日期和结果表格。请只补全 **3 个核心计算**：

1. 历史累计收益峰值；
2. 每日回撤序列；
3. 最大回撤。

提示：历史峰值使用 `cummax()`；回撤等于“当前累计收益 − 历史峰值”，因此最大回撤通常是负数。
'@

$homework4Code = @'
def analyze_excess_return_drawdown(report_normal_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """计算含成本超额收益最大回撤；学生只需补全 3 个核心公式。"""
    required_columns = {"return", "bench", "cost"}
    missing_columns = required_columns.difference(report_normal_df.columns)
    if missing_columns:
        raise KeyError(f"回测报告缺少列: {sorted(missing_columns)}")

    # 已给出：先计算含成本日超额收益及其累计曲线。
    excess_return_with_cost = (
        report_normal_df["return"]
        - report_normal_df["bench"]
        - report_normal_df["cost"]
    )
    cumulative_excess_with_cost = excess_return_with_cost.cumsum()

    # TODO 1：用 cummax() 计算截至每一天的历史累计收益峰值
    running_peak = ...

    # TODO 2：每日回撤 = 当前累计收益 - 历史累计收益峰值
    drawdown = ...

    # TODO 3：最大回撤是回撤序列中的最小值
    max_drawdown = ...

    if any(value is Ellipsis for value in (running_peak, drawdown, max_drawdown)):
        raise NotImplementedError("请补全课后作业（4）的 3 个 TODO。")

    # 起止日期和结果表结构已给出，不需要修改。
    drawdown_end = drawdown.idxmin()
    drawdown_start = cumulative_excess_with_cost.loc[:drawdown_end].idxmax()
    duration_days = (
        (drawdown_end - drawdown_start).days
        if hasattr(drawdown_end - drawdown_start, "days")
        else None
    )

    stats = pd.DataFrame(
        {
            "数值": [
                max_drawdown,
                drawdown_start,
                drawdown_end,
                duration_days,
            ]
        },
        index=["最大回撤", "回撤开始日期", "回撤结束日期", "持续天数"],
    )
    stats.index.name = "指标"
    return {
        "with_cost": stats,
        "drawdown_series": drawdown.to_frame("drawdown"),
    }


# 完成 3 个 TODO 后取消下面代码的注释进行检查：
# excess_dd_result = analyze_excess_return_drawdown(report_normal_df)
# display(excess_dd_result["with_cost"])
'@

$sqliteInit = @'
# 本教程仅面向 Colab，直接把 MLflow 数据库放在临时运行时目录。
mlflow_db = Path("/content/qlib_mlflow.db")
exp_manager = {
    "class": "MLflowExpManager",
    "module_path": "qlib.workflow.expm",
    "kwargs": {
        "uri": f"sqlite:///{mlflow_db.resolve().as_posix()}",
        "default_exp_name": "Experiment",
    },
}

qlib.init(provider_uri=provider_uri, region=REG_CN, exp_manager=exp_manager, kernels=1)
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

    if ($cell.cell_type -eq 'markdown' -and $text -match 'SignalRecord\.generate\(\)' -and $text -match 'PortAnaRecord\.generate\(\)') {
        $text = $standardBacktestExplanation
    }

    if ($cell.cell_type -eq 'code') {
        $text = $text.Replace("provider_uri =  './qlib_data/cn_data' # target_dir", "provider_uri = str(QLIB_DATA_DIR)  # Colab 与本地共用")
        $text = $text.Replace('stock_features_path = Path("./qlib_data/cn_data/features/sh600000")', 'stock_features_path = QLIB_DATA_DIR / "features" / "sh600000"')
        $text = $text.Replace('"num_threads": 20,', '"num_threads": 2,')
        $text = $text.Replace('qlib.init(provider_uri=provider_uri, region=REG_CN)', $sqliteInit)
        if ($text -match 'from qlib\.workflow\.record_temp import SignalRecord, PortAnaRecord') {
            $text = $text.Replace('from qlib.workflow.record_temp import SignalRecord, PortAnaRecord', "from qlib.workflow.record_temp import PortAnaRecord`nfrom qlib.backtest.high_performance_ds import PandasQuote")
        }

        if ($text -match '# 获取实际的 feaure 数据') { $text = $featureSample }
        if ($text -match '# 获取实际的 label 数据') { $text = $labelSample }
        if ($text -match '# ==================== 数据处理器配置') { $text = $handlerConfig }
        if ($text -match 'handler = Alpha158\(\*\*data_handler_config\)') {
            $text = $handlerInit
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
            $text = $text.Replace('# 训练集：7年数据', '# 训练集：1年课堂轻量数据')
            $text = $text.Replace('# 验证集：2年数据（用于早停）', '# 验证集：1年数据（用于早停）')
            $text = $text.Replace('# 测试集：3.5年数据（用于最终评估）', '# 测试集：约1.5年数据（用于最终评估）')
        }

        if ($text -match 'port_analysis_config\s*=') {
            $text = $text.Replace('"start_time": "2017-01-01"', '"start_time": TEACHING_SEGMENTS["test"][0]')
            $text = $text.Replace('"end_time": "2020-08-01"', '"end_time": LOW_MEMORY_BACKTEST_END')
            $text = $text.Replace('"model": model,                              # 使用的预测模型', '"signal": "<PRED>",                         # 复用 SignalRecord 已保存的预测')
            $text = $text.Replace("            `"dataset`": dataset,                          # 数据集`n", '')
            $text = $text.Replace('"freq": "day",                               # 交易频率：日频', "`"codes`": market,                              # 运行时会替换为预测中实际出现的股票`n            `"quote_cls`": PandasQuote,                    # 避免 NumpyQuote 的二次 float64 缓存`n            `"freq`": `"day`",                               # 交易频率：日频")
        }

        # task 中保留数据集配置用于实验记录，但训练时复用第 4 节已创建的 dataset。
        $text = $text.Replace('dataset = init_instance_by_config(task["dataset"])', 'print("复用第 4 节已创建的 DatasetH，避免重复加载 Alpha158。")')

        if ($text -match 'with R\.start\(experiment_name="train_model"\)' -and $text -match 'model\.fit\(dataset\)') {
            $text = $trainingCell
        }

        if ($text -match 'with R\.start\(experiment_name="backtest_analysis"\)' -and $text -match 'SignalRecord\(') {
            $text = $standardBacktestWorkflow
        }

        if ($text -match 'recorder\s*=\s*R\.get_recorder\(recorder_id=ba_rid') {
            $text = $standardAnalysisRecorderCell
        }

        # 回测工作流本身也会读取 pred.pkl；只替换原 Notebook 的独立“查看预测”单元格。
        if ($text -match 'pred_df\s*=\s*recorder\.load_object\("pred\.pkl"\)' -and $text -notmatch 'SignalRecord\(') {
            $text = $standardPredictionOverviewCell
        }

        if ($text -match 'load_backtest_data\(recorder') {
            $text = $standardBacktestDataCell
        }

        if ($text -match '# 准备预测和标签数据') {
            $text = $standardLabelCell
        }

        # Qlib 的 show_notebook 自动显示在部分 Colab 会话中会失效。
        # 先拿到 Figure，再通过上面的 Colab renderer 显式 show。
        $text = $text.Replace(
            'analysis_position.report_graph(report_normal_df)',
            'report_fig_list = analysis_position.report_graph(report_normal_df, show_notebook=False)' + "`n" +
            'for figure in report_fig_list:' + "`n" +
            '    show_plotly(figure)'
        )
        $text = $text.Replace(
            'analysis_position.risk_analysis_graph(analysis_df, report_normal_df)',
            'risk_overview_figs = analysis_position.risk_analysis_graph(analysis_df, report_normal_df, show_notebook=False)' + "`n" +
            'for figure in risk_overview_figs:' + "`n" +
            '    show_plotly(figure)'
        )
        $text = $text.Replace(
            'analysis_model.model_performance_graph(pred_label)',
            'model_overview_figs = analysis_model.model_performance_graph(pred_label, show_notebook=False)' + "`n" +
            'for figure in model_overview_figs:' + "`n" +
            '    show_plotly(figure)'
        )

        # 原稿中各子图使用 fig.show()；统一走显式 renderer，避免空白输出。
        $text = [regex]::Replace(
            $text,
            '(?m)^(\s*)([A-Za-z_][A-Za-z0-9_]*(?:\[[^\r\n]+\])?)\.show\(\)\s*$',
            '$1show_plotly($2)'
        )

        if ($text -match 'from Utils_backtest import \*') {
            $text = $text.Replace("import sys`nfrom pathlib import Path`n`n# 导入回测分析模块`nsys.path.insert(0, str(Path.cwd() / 'py'))`nfrom Utils_backtest import *`n", "# 回测分析辅助函数已在环境准备部分内嵌，无需额外文件。`n")
        }

        if ($text -match 'ex_return_wo_cost\s*=\s*\r?\n') {
            $text = $homework3Code
        }

        if ($text -match 'max_drawdown\s*=\s*\r?\n') {
            $text = $homework4Code
        }

        $cell.execution_count = $null
        # 主 Notebook 同时是讲解网页的数据源：只保留原稿中的 Plotly 图表输出。
        # 两本学生 Notebook 会在拆分时继续清空全部输出，保证 Colab 从头运行。
        $cell.outputs = @($cell.outputs | Where-Object {
            $_.data -and
            ($_.data.PSObject.Properties.Name -contains 'application/vnd.plotly.v1+json')
        })
    }

    if ($cell.cell_type -eq 'markdown' -and $text -match '课后作业（2）：理解三种数据模式') {
        $text = $dataModeExercise
    }
    if ($cell.cell_type -eq 'markdown' -and $text -match '课后作业（3）') {
        $text = $homework3Markdown
    }
    if ($cell.cell_type -eq 'markdown' -and $text -match '课后作业（4）') {
        $text = $homework4Markdown
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
Write-Output "Next: run scripts/build_split_notebooks.py to generate the two student-facing notebooks."
