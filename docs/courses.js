(() => {
  const grid = document.querySelector("[data-course-grid]");
  const count = document.querySelector("[data-course-count]");

  const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
  }[char]));

  const renderCourse = (course) => `
    <article class="course-card">
      <div class="course-card-mark">${escapeHtml(course.mark)}</div>
      <div>
        <div class="course-card-top"><span class="eyebrow">${escapeHtml(course.version)}</span><span class="course-status">${escapeHtml(course.status)}</span></div>
        <h3>${escapeHtml(course.title)}</h3>
        <p>${escapeHtml(course.summary)}</p>
        <div class="course-meta"><span>${escapeHtml(course.modules)} 个模块</span><span>${escapeHtml(course.duration)}</span></div>
        <div class="course-actions">
          <a class="button button-ghost" href="${escapeHtml(course.landingPage)}">课程介绍</a>
          <a class="button button-primary" href="${escapeHtml(course.tutorialPage)}">进入讲解模式</a>
        </div>
      </div>
    </article>`;

  fetch("courses/catalog.json")
    .then((response) => {
      if (!response.ok) throw new Error(`课程目录加载失败：${response.status}`);
      return response.json();
    })
    .then((catalog) => {
      document.title = catalog.title;
      const courses = Array.isArray(catalog.courses) ? catalog.courses : [];
      count.textContent = `${courses.length} 门课程`;
      grid.innerHTML = courses.length ? courses.map(renderCourse).join("") : '<div class="catalog-loading">暂时没有已发布教程。</div>';
    })
    .catch(() => {
      count.textContent = "目录不可用";
      grid.innerHTML = '<div class="catalog-error">课程目录暂时无法加载，请稍后刷新页面。</div>';
    });
})();
