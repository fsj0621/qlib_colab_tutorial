(() => {
  const config = window.TUTORIAL_CONFIG || {};
  const host = window.location.hostname;
  const pathParts = window.location.pathname.split("/").filter(Boolean);
  const onGitHubPages = host.endsWith(".github.io");
  const inferredOwner = onGitHubPages ? host.split(".")[0] : "";
  const inferredRepo = onGitHubPages ? (pathParts[0] || `${inferredOwner}.github.io`) : "";
  const owner = config.owner || inferredOwner;
  const repo = config.repo || inferredRepo;
  const branch = config.branch || "main";
  const notebookPath = config.notebookPath || "notebooks/Qlib量化投资工作流教程_Colab学生版.ipynb";

  const colabLinks = document.querySelectorAll("[data-colab-link]");
  const githubLinks = document.querySelectorAll("[data-github-link]");
  const downloadLinks = document.querySelectorAll("[data-notebook-download]");
  const deploymentHint = document.querySelector("[data-deployment-hint]");
  const colabDialog = document.querySelector("[data-colab-dialog]");

  const configureDownloadLinks = (url, local = false) => {
    downloadLinks.forEach((link) => {
      link.href = url;
      if (local) link.setAttribute("download", "");
      else link.removeAttribute("download");
    });
  };

  if (owner && repo) {
    const githubUrl = `https://github.com/${owner}/${repo}`;
    const colabUrl = `https://colab.research.google.com/github/${owner}/${repo}/blob/${branch}/${encodeURI(notebookPath)}`;
    const notebookUrl = `https://raw.githubusercontent.com/${owner}/${repo}/${encodeURIComponent(branch)}/${encodeURI(notebookPath)}`;
    colabLinks.forEach((link) => {
      link.href = colabUrl;
      // Some embedded browsers silently block links that open a new tab.
      // Keep Colab navigation in the current tab so one click always works.
      link.target = "_self";
      link.removeAttribute("rel");
    });
    githubLinks.forEach((link) => {
      link.href = githubUrl;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
    });
    configureDownloadLinks(notebookUrl);
    if (deploymentHint) deploymentHint.hidden = true;
  } else {
    configureDownloadLinks(`../${notebookPath}`, true);
    colabLinks.forEach((link) => {
      link.href = "#colab-setup";
      link.addEventListener("click", (event) => {
        event.preventDefault();
        if (typeof colabDialog?.showModal === "function") colabDialog.showModal();
      });
    });
    githubLinks.forEach((link) => {
      link.hidden = true;
    });
  }

  const themeButton = document.querySelector("[data-theme-toggle]");
  const themeStorageKey = "qlib-tutorial-theme-v2";
  let savedTheme = null;
  try { savedTheme = localStorage.getItem(themeStorageKey); } catch (_) { /* file:// may restrict storage */ }
  if (savedTheme) document.documentElement.dataset.theme = savedTheme;
  themeButton?.addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem(themeStorageKey, next); } catch (_) { /* keep theme for this page only */ }
  });

  document.querySelectorAll("[data-dialog-close]").forEach((button) => {
    button.addEventListener("click", () => colabDialog?.close());
  });
  colabDialog?.addEventListener("click", (event) => {
    if (event.target === colabDialog) colabDialog.close();
  });

  const menuButton = document.querySelector("[data-menu-toggle]");
  const nav = document.querySelector("[data-nav]");
  menuButton?.addEventListener("click", () => {
    const open = nav.classList.toggle("is-open");
    menuButton.setAttribute("aria-expanded", String(open));
  });
  nav?.querySelectorAll("a").forEach((link) => link.addEventListener("click", () => nav.classList.remove("is-open")));

  const observer = new IntersectionObserver(
    (entries) => entries.forEach((entry) => entry.isIntersecting && entry.target.classList.add("is-visible")),
    { threshold: 0.12 }
  );
  document.querySelectorAll(".reveal").forEach((element) => observer.observe(element));
})();
