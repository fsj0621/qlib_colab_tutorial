# 量化投资 Colab 教程网站

这是一个可承载多门课程的静态教程网站。当前已发布 Qlib 量化投资工作流教程，包含：

- 课程目录、课程首页与配置驱动的讲解模式；
- 两本独立的 Colab Notebook：数据与因子探索、模型训练与回测；
- 内嵌回测辅助函数，Notebook 可作为单文件运行；
- GitHub Pages、Colab 与同源下载链接；
- 固定版本的 Colab 依赖清单。

## 本地预览

在 `qlib_colab_tutorial` 的上一级目录执行：

```powershell
python -m http.server 8000 --directory qlib_colab_tutorial
```

然后访问：

- `http://localhost:8000/docs/`：Qlib 课程首页；
- `http://localhost:8000/docs/courses.html`：全部教程；
- `http://localhost:8000/docs/tutorial.html?course=qlib`：Qlib 讲解模式。

## 新增一门教程

网站的讲解页由课程配置自动生成，无需复制 HTML：

1. 复制 `docs/courses/qlib.json`，并以课程代号命名，例如 `docs/courses/qmt.json`；
2. 修改课程名称、仓库、发布版本、Notebook 路径和模块内容；
3. 在 `docs/courses/catalog.json` 中增加课程卡片；
4. 将 Notebook 放入仓库，并确保配置中的下载路径可以访问；
5. 新教程的讲解地址即为 `tutorial.html?course=qmt`。

课程配置支持模块名称、预计时间、学习目标、授课提示和绩效指标卡。页面会自动生成侧栏、章节锚点、上一节/下一节导航、Colab 和下载链接。

讲解页还可以直接读取 Notebook 整理后的内容。Qlib 教程使用下面的命令，把 Notebook 的章节、教材文字、代码单元和作业标识生成到网页数据中：

```powershell
python scripts/build_tutorial_content.py `
  --input "notebooks/Qlib量化投资工作流教程_Colab学生版.ipynb" `
  --output "docs/courses/qlib-notebook.json" `
  --revision "v1.1.3"
```

课程配置中的 `notebookContent` 指向生成结果。更新已发布 Notebook 后重新运行此命令，网页讲解内容就会同步更新。

## 发布到 GitHub Pages

1. 将 `qlib_colab_tutorial` 整个目录作为一个 GitHub 仓库推送，默认分支使用 `main`。
2. 打开仓库的 **Settings → Pages**。
3. 在 **Build and deployment** 中选择 **Deploy from a branch**。
4. 选择 `main` 分支和 `/docs` 目录并保存。
5. 发布地址通常为 `https://<owner>.github.io/<repo>/`。

标准 GitHub Pages 地址无需修改配置。如果使用自定义域名，请编辑 `docs/site-config.js`，填写 `owner` 和 `repo`。

## Colab 数据说明

Notebook 固定使用 Colab `2026.07` 运行时（Python 3.12.13），因为 `pyqlib==0.9.7` 暂无 Python 3.13 安装包。若已经连接到 Python 3.13，请在 **代码执行程序 → 更改运行时类型 → 运行时版本** 中选择 `2026.07`，然后重新运行。

`v1.1.3` 将课堂实践拆成两个独立运行时。第一部分只讲数据、表达式特征与一个月的 Alpha158 小样本，不创建正式训练集；完成后主动删除运行时。第二部分从干净环境独立创建唯一一套正式 Alpha158，并恢复 Qlib 的 `SignalRecord`、`PortAnaRecord` 与 `SimulatorExecutor` 标准流程。训练、验证、测试区间继续使用 2017、2018、2019–2020 的课堂轻量范围，组合回测只覆盖 2019 年；不再生成或下载额外检查点文件。讲解网页会按需渲染原始课程中的 Plotly 示例图，而两本学生 Notebook 仍保持无预存输出。课后作业 3、4 已改为限定式代码骨架，学生各自只需补全 3 个核心计算。

Qlib 当前 README 说明官方数据下载暂时停用，因此 Notebook 使用其推荐的社区数据镜像：

`https://github.com/chenditc/investment_data/releases/latest/download/qlib_bin.tar.gz`

首次运行会下载约 464 MB 数据。数据只用于教学演示，不构成投资建议。

## 重新生成 Notebook

若源 Notebook 更新，可运行：

```powershell
powershell -ExecutionPolicy Bypass -File tools/build_colab_notebook.ps1 `
  -SourceNotebook "源文件路径\Qlib基础教程.ipynb" `
  -SupportModule "源文件路径\Utils_backtest.py" `
  -OutputNotebook "notebooks\Qlib量化投资工作流教程_Colab学生版.ipynb"

python scripts/build_split_notebooks.py `
  --input "notebooks\Qlib量化投资工作流教程_Colab学生版.ipynb" `
  --exploration-output "notebooks\Qlib数据与因子探索_Colab教学版.ipynb" `
  --training-output "notebooks\Qlib模型训练与回测_Colab教学版.ipynb"
```

主生成脚本会清除所有输出、加入 Colab 环境单元格、内嵌辅助函数、替换数据路径，并修复作业占位代码的语法错误；拆分生成器会创建相互独立的探索篇和训练回测篇。后者连续完成训练、标准回测和分析，不再生成额外的断线恢复文件。发布前将两本 Notebook 同步到 `docs/downloads/`。

## 版权

Notebook 基于 Microsoft Qlib v0.9.7 官方示例改编，保留原始版权与 MIT License 信息。课程新增文字、页面样式和教学组织内容请按课程建设项目要求使用。
