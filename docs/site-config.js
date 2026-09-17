// 使用默认空值时，部署到 https://<owner>.github.io/<repo>/ 后会自动识别仓库。
// 自定义域名或非标准路径部署时，只需填写 owner 和 repo。
window.TUTORIAL_CONFIG = {
  owner: "fsj0621",
  repo: "qlib_colab_tutorial",
  // 固定到经过验证的教学版本，避免 GitHub/Colab 缓存到旧 Notebook。
  branch: "v1.1.0",
  explorationNotebookPath: "notebooks/Qlib数据与因子探索_Colab教学版.ipynb",
  explorationDownloadPath: "downloads/Qlib数据与因子探索_Colab教学版.ipynb",
  trainingNotebookPath: "notebooks/Qlib模型训练与回测_Colab教学版.ipynb",
  trainingDownloadPath: "downloads/Qlib模型训练与回测_Colab教学版.ipynb",
};
