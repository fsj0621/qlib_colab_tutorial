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

1. 在顶部菜单选择 **代码执行程序 → 全部运行**。
2. 首次运行会安装依赖并下载约 464 MB 的教学数据，通常需要数分钟。
3. 遇到“请补充代码”的单元格时完成练习，再继续后续章节。

> 数据仅用于教学演示，不构成投资建议。Notebook 基于 [Microsoft Qlib v0.9.7 官方示例](https://github.com/microsoft/qlib/blob/v0.9.7/examples/workflow_by_code.ipynb) 改编，沿用 MIT License。
'@

$environment = @'
## 1. 云端环境准备

Colab 会为每位学习者提供临时 Python 环境，因此不需要在本地安装 Qlib。下面的初始化单元格会：

- 安装与本教程验证版本一致的 Qlib、Plotly、Statsmodels 和 LightGBM；
- 从 Qlib README 当前推荐的社区镜像下载 A 股教学数据；
- 将数据解压到 Colab 的 `/content/qlib_data/cn_data`；
- 检查 Python 版本和数据目录是否就绪。

> Colab 虚拟机是临时的。运行时被回收后，依赖与数据需要重新准备。
'@

$setup = @'
#@title 运行一次：安装依赖并准备 Qlib A 股数据
import os
import sys
import subprocess
from pathlib import Path

IN_COLAB = "google.colab" in sys.modules
PINNED_PACKAGES = [
    "pyqlib==0.9.7",
    "plotly==6.6.0",
    "statsmodels==0.14.6",
    "lightgbm==4.6.0",
]

if IN_COLAB:
    print("正在安装教学环境……")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", *PINNED_PACKAGES],
        check=True,
    )
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
