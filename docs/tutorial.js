(() => {
  const sidebar = document.querySelector("[data-course-sidebar]");
  const toggle = document.querySelector("[data-toc-toggle]");
  const scrim = document.querySelector("[data-sidebar-scrim]");
  const nav = document.querySelector("[data-course-nav]");
  const content = document.querySelector("[data-course-content]");
  const plotlyFigures = new Map();

  const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
  }[char]));
  const inline = (value) => escapeHtml(value).replace(/`([^`]+)`/g, "<code>$1</code>");

  const setSidebar = (open) => {
    sidebar?.classList.toggle("is-open", open);
    scrim?.classList.toggle("is-visible", open);
    toggle?.setAttribute("aria-expanded", String(open));
    document.body.classList.toggle("sidebar-open", open);
  };

  toggle?.addEventListener("click", () => setSidebar(!sidebar?.classList.contains("is-open")));
  scrim?.addEventListener("click", () => setSidebar(false));
  document.addEventListener("keydown", (event) => event.key === "Escape" && setSidebar(false));

  const list = (block) => {
    const ordered = block.style === "ordered";
    const className = block.style === "check" ? "check-list" : block.style === "question" ? "question-list" : "";
    const tag = ordered ? "ol" : "ul";
    return `<${tag} class="${className}">${block.items.map((item) => `<li>${inline(item)}</li>`).join("")}</${tag}>`;
  };

  const metrics = (items = []) => items.length ? `<div class="metric-grid">${items.map((item) => `
    <article><strong>${escapeHtml(item.name)}</strong><span>${escapeHtml(item.description)}</span></article>`).join("")}</div>` : "";

  const notebookOutput = (outputs = [], cellNumber) => outputs.map((output) => {
    if (output.type === "plotly") {
      const key = `cell-${cellNumber}-output-${output.index}`;
      plotlyFigures.set(key, output.figure);
      return `
        <div class="notebook-output notebook-chart-output">
          <div class="cell-label"><span>运行示例图</span><span>实际结果以 Colab 运行为准</span></div>
          <div class="notebook-plot" data-plot-key="${escapeHtml(key)}" role="img" aria-label="Cell ${escapeHtml(cellNumber)} 的运行示例图">
            <span class="chart-loading">展开后加载图表…</span>
          </div>
        </div>`;
    }
    return `
      <div class="notebook-output">
        <div class="cell-label">输出${output.truncated ? "（已截取）" : ""}</div>
        <pre>${escapeHtml(output.text)}</pre>
      </div>`;
  }).join("");

  const notebookCell = (cell) => {
    if (cell.type === "markdown") return `<div class="notebook-prose">${cell.html}</div>`;
    const code = `<pre class="notebook-code"><code>${escapeHtml(cell.source)}</code></pre>`;
    const codeBody = cell.collapsed ? `
      <details class="code-fold">
        <summary>查看代码 · ${escapeHtml(cell.lineCount)} 行</summary>
        ${code}
      </details>` : code;
    return `
      <article class="notebook-cell ${cell.exercise ? "is-exercise" : ""}">
        <div class="cell-label"><span>${cell.exercise ? "练习" : "代码"} · Cell ${escapeHtml(cell.cell)}</span>${cell.omitted ? "<span>长辅助函数</span>" : ""}</div>
        ${codeBody}
        ${cell.omitted ? '<p class="cell-omitted">这里只展示前 18 行，完整辅助函数请在 Colab 中查看。</p>' : ""}
        ${notebookOutput(cell.outputs, cell.cell)}
      </article>`;
  };

  const renderPlotlyIn = (root) => {
    root.querySelectorAll(".notebook-plot:not([data-rendered])").forEach((element) => {
      const figure = plotlyFigures.get(element.dataset.plotKey);
      if (!figure || !window.Plotly) {
        element.classList.add("has-error");
        element.textContent = "图表组件加载失败，请在 Colab 中运行本单元格查看。";
        return;
      }
      element.dataset.rendered = "true";
      const { width: _sourceWidth, ...sourceLayout } = figure.layout || {};
      const layout = {
        ...sourceLayout,
        autosize: true,
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
      };
      const config = {
        ...(figure.config || {}),
        responsive: true,
        displaylogo: false,
      };
      element.replaceChildren();
      window.Plotly.newPlot(element, figure.data, layout, config).catch(() => {
        element.classList.add("has-error");
        element.textContent = "图表渲染失败，请在 Colab 中运行本单元格查看。";
      });
    });
  };

  const initializePlotlyOutputs = () => {
    document.querySelectorAll(".notebook-step").forEach((step) => {
      step.addEventListener("toggle", () => {
        if (step.open) renderPlotlyIn(step);
      });
      if (step.open) renderPlotlyIn(step);
    });
  };

  const notebookWalkthrough = (notebookModule, revision) => {
    if (!notebookModule) return "";
    const groups = notebookModule.groups.map((group, index) => `
      <details class="notebook-step ${group.exercise ? "is-exercise" : ""}" ${index === 0 ? "open" : ""}>
        <summary>
          <span><small>${group.exercise ? "课后作业" : `步骤 ${index + 1}`}</small>${escapeHtml(group.title)}</span>
          <span class="step-meta">${group.codeCount ? `${group.codeCount} 个代码单元` : "讲解"}</span>
        </summary>
        <div class="notebook-step-body">${group.cells.map(notebookCell).join("")}</div>
      </details>`).join("");
    return `
      <section class="notebook-walkthrough" aria-label="Notebook 讲解内容">
        <div class="notebook-walkthrough-heading">
          <div><span class="lesson-kicker">Notebook Walkthrough</span><h2>跟着 Notebook 讲</h2></div>
          <span class="source-chip">${escapeHtml(revision)} · Cells ${escapeHtml(notebookModule.cellRange[0])}–${escapeHtml(notebookModule.cellRange[1])}</span>
        </div>
        <p class="notebook-lead">教材原文、代码和作业已按 Notebook 小节整理。展开小节即可讲解，实际运行请使用 Colab。</p>
        <div class="notebook-steps">${groups}</div>
      </section>`;
  };

  const teachingGuide = (module) => `
    <details class="teaching-guide">
      <summary>教师提示与课堂检查</summary>
      <div class="teaching-grid">
        <article><h2>${escapeHtml(module.primary.title)}</h2>${list(module.primary)}</article>
        <article><h2>${escapeHtml(module.secondary.title)}</h2>${list(module.secondary)}</article>
      </div>
    </details>`;

  const lesson = (module, index, total, nextModule, notebookModule, revision) => {
    const id = `module-${module.number}`;
    const notebookPart = module.notebookPart === "training" ? "training" : "exploration";
    const notebookLabel = notebookPart === "training" ? "在训练回测篇中运行" : "在数据探索篇中运行";
    const next = index < total - 1 ? `<div class="lesson-next"><span>下一节</span><a href="#module-${nextModule.number}">${escapeHtml(nextModule.shortTitle || nextModule.title)} →</a></div>` : "";
    return `
      <section class="lesson" id="${id}" data-module-section>
        <div class="lesson-heading">
          <span class="lesson-number">${escapeHtml(module.number)}</span>
          <div><div class="lesson-kicker">Module ${escapeHtml(module.number)}</div><h1>${escapeHtml(module.title)}</h1><p>${escapeHtml(module.summary)}</p></div>
        </div>
        <div class="lesson-meta"><span>◷ ${escapeHtml(module.duration)}</span><span>Notebook：${escapeHtml(module.notebookSection)}</span></div>
        <div class="lesson-notebook-action"><a class="button button-small ${notebookPart === "training" ? "button-primary" : "button-ghost"}" data-module-notebook="${notebookPart}" target="_self" href="#">${notebookLabel} ↗</a></div>
        <div class="objective-box"><h2>学习目标</h2><ul>${module.objectives.map((item) => `<li>${inline(item)}</li>`).join("")}</ul></div>
        ${metrics(module.metrics)}
        ${notebookWalkthrough(notebookModule, revision)}
        ${teachingGuide(module)}
        <aside class="teaching-note ${module.note.tone === "warning" ? "warning" : ""}"><strong>${escapeHtml(module.note.title)}</strong><p>${escapeHtml(module.note.text)}</p></aside>
        ${next}
      </section>`;
  };

  const setActive = (id) => {
    document.querySelectorAll("[data-module-link]").forEach((link) => {
      const active = link.dataset.moduleLink === id;
      link.classList.toggle("is-active", active);
      if (active) link.setAttribute("aria-current", "true");
      else link.removeAttribute("aria-current");
    });
  };

  const initializeNavigation = () => {
    const links = [...document.querySelectorAll("[data-module-link]")];
    links.forEach((link) => link.addEventListener("click", () => setSidebar(false)));
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => Math.abs(a.boundingClientRect.top) - Math.abs(b.boundingClientRect.top))[0];
        if (visible) setActive(visible.target.id);
      },
      { rootMargin: "-15% 0px -70% 0px", threshold: 0 }
    );
    document.querySelectorAll("[data-module-section]").forEach((section) => observer.observe(section));
  };

  const renderCourse = (course, notebookContent) => {
    document.title = course.pageTitle || `${course.title} · 讲解模式`;
    document.querySelector("[data-course-mark]").textContent = course.mark;
    document.querySelector("[data-course-title]").textContent = course.title;
    document.querySelector("[data-course-subtitle]").textContent = course.subtitle;
    document.querySelector("[data-course-version]").textContent = `${course.subtitle} · ${course.version}`;
    document.querySelector("[data-course-home]").href = course.landingPage;

    const navItems = course.modules.map((module, index) => `
      <a class="module-link ${index === 0 ? "is-active" : ""}" href="#module-${module.number}" data-module-link="module-${module.number}">
        <span class="nav-number">${escapeHtml(module.number)}</span><span class="nav-title">${escapeHtml(module.shortTitle || module.title)}</span><span class="nav-time">${escapeHtml(module.duration)}</span>
      </a>`).join("");
    nav.querySelector(".nav-loading").outerHTML = navItems;

    const notebookModules = new Map((notebookContent?.modules || []).map((module) => [Number(module.number), module]));
    content.innerHTML = course.modules.map((module, index) => lesson(
      module,
      index,
      course.modules.length,
      course.modules[index + 1],
      notebookModules.get(Number(module.number)),
      notebookContent?.revision || course.version
    )).join("") + `
      <div class="course-finish">
        <div><span class="lesson-kicker">两阶段实践</span><h2>选择对应 Notebook 完成练习</h2></div>
        <div class="hero-actions">
          <a class="button button-ghost" data-course-exploration target="_self" href="#">第一部分：数据探索 ↗</a>
          <a class="button button-primary" data-course-training target="_self" href="#">第二部分：训练与回测 ↗</a>
        </div>
      </div>`;

    const explorationColabUrl = `https://colab.research.google.com/github/${course.owner}/${course.repo}/blob/${course.release}/${encodeURI(course.explorationNotebookPath)}`;
    const trainingColabUrl = `https://colab.research.google.com/github/${course.owner}/${course.repo}/blob/${course.release}/${encodeURI(course.trainingNotebookPath)}`;
    const explorationDownloadUrl = new URL(encodeURI(course.explorationDownloadPath), document.baseURI).href;
    const trainingDownloadUrl = new URL(encodeURI(course.trainingDownloadPath), document.baseURI).href;
    document.querySelectorAll("[data-course-exploration], [data-module-notebook='exploration']").forEach((link) => { link.href = explorationColabUrl; });
    document.querySelectorAll("[data-course-training], [data-module-notebook='training']").forEach((link) => { link.href = trainingColabUrl; });
    document.querySelectorAll("[data-course-exploration-download]").forEach((link) => {
      link.href = explorationDownloadUrl;
      link.setAttribute("download", course.explorationNotebookPath.split("/").pop());
    });
    document.querySelectorAll("[data-course-training-download]").forEach((link) => {
      link.href = trainingDownloadUrl;
      link.setAttribute("download", course.trainingNotebookPath.split("/").pop());
    });
    initializePlotlyOutputs();
    initializeNavigation();
    if (window.location.hash) {
      requestAnimationFrame(() => document.getElementById(window.location.hash.slice(1))?.scrollIntoView());
    }
  };

  const allowedSlug = /^[a-z0-9-]+$/;
  const requested = new URLSearchParams(window.location.search).get("course") || "qlib";
  const slug = allowedSlug.test(requested) ? requested : "qlib";

  fetch(`courses/${slug}.json`)
    .then((response) => {
      if (!response.ok) throw new Error(`课程配置加载失败：${response.status}`);
      return response.json();
    })
    .then((course) => {
      if (!course.notebookContent) return [course, null];
      return fetch(course.notebookContent)
        .then((response) => response.ok ? response.json() : null)
        .catch(() => null)
        .then((notebookContent) => [course, notebookContent]);
    })
    .then(([course, notebookContent]) => renderCourse(course, notebookContent))
    .catch(() => {
      content.innerHTML = '<div class="tutorial-error"><strong>没有找到这门教程</strong><p>请返回教程中心选择已发布课程。</p><a class="button button-primary" href="courses.html">返回全部教程</a></div>';
      const loading = nav.querySelector(".nav-loading");
      if (loading) loading.textContent = "课程目录不可用";
    });
})();
