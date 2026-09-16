(() => {
  const sidebar = document.querySelector("[data-course-sidebar]");
  const toggle = document.querySelector("[data-toc-toggle]");
  const scrim = document.querySelector("[data-sidebar-scrim]");
  const nav = document.querySelector("[data-course-nav]");
  const content = document.querySelector("[data-course-content]");

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

  const lesson = (module, index, total, nextModule) => {
    const id = `module-${module.number}`;
    const next = index < total - 1 ? `<div class="lesson-next"><span>下一节</span><a href="#module-${nextModule.number}">${escapeHtml(nextModule.shortTitle || nextModule.title)} →</a></div>` : "";
    return `
      <section class="lesson" id="${id}" data-module-section>
        <div class="lesson-heading">
          <span class="lesson-number">${escapeHtml(module.number)}</span>
          <div><div class="lesson-kicker">Module ${escapeHtml(module.number)}</div><h1>${escapeHtml(module.title)}</h1><p>${escapeHtml(module.summary)}</p></div>
        </div>
        <div class="lesson-meta"><span>◷ ${escapeHtml(module.duration)}</span><span>Notebook：${escapeHtml(module.notebookSection)}</span></div>
        <div class="objective-box"><h2>学习目标</h2><ul>${module.objectives.map((item) => `<li>${inline(item)}</li>`).join("")}</ul></div>
        ${metrics(module.metrics)}
        <div class="teaching-grid">
          <article><h2>${escapeHtml(module.primary.title)}</h2>${list(module.primary)}</article>
          <article><h2>${escapeHtml(module.secondary.title)}</h2>${list(module.secondary)}</article>
        </div>
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

  const renderCourse = (course) => {
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

    content.innerHTML = course.modules.map((module, index) => lesson(module, index, course.modules.length, course.modules[index + 1])).join("") + `
      <div class="course-finish">
        <div><span class="lesson-kicker">完成课程</span><h2>回到 Notebook 完成练习</h2></div>
        <a class="button button-primary" data-course-colab target="_self" href="#">打开 Colab ↗</a>
      </div>`;

    const colabUrl = `https://colab.research.google.com/github/${course.owner}/${course.repo}/blob/${course.release}/${encodeURI(course.notebookPath)}`;
    const downloadUrl = new URL(encodeURI(course.downloadPath), document.baseURI).href;
    document.querySelectorAll("[data-course-colab]").forEach((link) => { link.href = colabUrl; });
    document.querySelectorAll("[data-course-download]").forEach((link) => {
      link.href = downloadUrl;
      link.setAttribute("download", course.notebookPath.split("/").pop());
    });
    initializeNavigation();
    if (window.location.hash) {
      requestAnimationFrame(() => document.querySelector(window.location.hash)?.scrollIntoView());
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
    .then(renderCourse)
    .catch(() => {
      content.innerHTML = '<div class="tutorial-error"><strong>没有找到这门教程</strong><p>请返回教程中心选择已发布课程。</p><a class="button button-primary" href="courses.html">返回全部教程</a></div>';
      const loading = nav.querySelector(".nav-loading");
      if (loading) loading.textContent = "课程目录不可用";
    });
})();
