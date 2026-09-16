(() => {
  const sidebar = document.querySelector("[data-course-sidebar]");
  const toggle = document.querySelector("[data-toc-toggle]");
  const scrim = document.querySelector("[data-sidebar-scrim]");
  const links = [...document.querySelectorAll("[data-module-link]")];
  const sections = [...document.querySelectorAll("[data-module-section]")];

  const setSidebar = (open) => {
    sidebar?.classList.toggle("is-open", open);
    scrim?.classList.toggle("is-visible", open);
    toggle?.setAttribute("aria-expanded", String(open));
    document.body.classList.toggle("sidebar-open", open);
  };

  toggle?.addEventListener("click", () => setSidebar(!sidebar?.classList.contains("is-open")));
  scrim?.addEventListener("click", () => setSidebar(false));
  links.forEach((link) => link.addEventListener("click", () => setSidebar(false)));
  document.addEventListener("keydown", (event) => event.key === "Escape" && setSidebar(false));

  const setActive = (id) => {
    links.forEach((link) => {
      const active = link.dataset.moduleLink === id;
      link.classList.toggle("is-active", active);
      if (active) link.setAttribute("aria-current", "true");
      else link.removeAttribute("aria-current");
    });
  };

  const sectionObserver = new IntersectionObserver(
    (entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => Math.abs(a.boundingClientRect.top) - Math.abs(b.boundingClientRect.top))[0];
      if (visible) setActive(visible.target.id);
    },
    { rootMargin: "-15% 0px -70% 0px", threshold: 0 }
  );

  sections.forEach((section) => sectionObserver.observe(section));
})();
