# Qlib Colab 教程网站

这是由现有 `Qlib基础教程.ipynb` 转换得到的发布原型，包含：

- 零构建依赖的静态教程首页；
- 清除大型输出后的 Colab 学生版 Notebook；
- 内嵌回测辅助函数，Notebook 可作为单文件运行；
- GitHub Pages 与 Colab 链接自动推断；
- 固定版本的 Colab 依赖清单。

## 本地预览

在 `qlib_colab_tutorial` 的上一级目录执行：

```powershell
python -m http.server 8000 --directory qlib_colab_tutorial
```

然后访问 `http://localhost:8000/docs/`。本地预览时，“在 Colab 中运行”会提示先配置 GitHub 仓库，“下载 Notebook（.ipynb）”是独立按钮；部署到 GitHub Pages 后，主按钮会自动生成正确的 Colab URL。

## 发布到 GitHub Pages

1. 将 `qlib_colab_tutorial` 整个目录作为一个 GitHub 仓库推送，默认分支使用 `main`。
2. 打开仓库的 **Settings → Pages**。
3. 在 **Build and deployment** 中选择 **Deploy from a branch**。
4. 选择 `main` 分支和 `/docs` 目录并保存。
5. 发布地址通常为 `https://<owner>.github.io/<repo>/`。

标准 GitHub Pages 地址无需修改配置。如果使用自定义域名，请编辑 `docs/site-config.js`，填写 `owner` 和 `repo`。

## Colab 数据说明

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
```

生成脚本会清除所有输出、加入 Colab 环境单元格、内嵌辅助函数、替换数据路径，并修复作业占位代码的语法错误。

## 版权

Notebook 基于 Microsoft Qlib v0.9.7 官方示例改编，保留原始版权与 MIT License 信息。课程新增文字、页面样式和教学组织内容请按课程建设项目要求使用。
