/* 官网交互：导航高亮、FAQ、下载提示、年份。纯原生 JS，无外部依赖。 */
(function () {
  "use strict";
  var page = location.pathname.split("/").pop() || "index.html";
  document.querySelectorAll("nav.links a").forEach(function (a) {
    if (a.getAttribute("href") === page) a.classList.add("active");
  });
  var y = document.getElementById("year");
  if (y) y.textContent = new Date().getFullYear();

  /* 移动端汉堡菜单：开关 + 无障碍属性 + 点链接/点外部自动收起 */
  var toggle = document.querySelector(".nav-toggle");
  var navLinks = document.querySelector("nav.links");
  if (toggle && navLinks) {
    function setMenu(open) {
      navLinks.classList.toggle("open", open);
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      toggle.setAttribute("aria-label", open ? "收起导航菜单" : "展开导航菜单");
      toggle.textContent = open ? "✕" : "☰";
    }
    toggle.addEventListener("click", function (e) {
      e.stopPropagation();
      setMenu(!navLinks.classList.contains("open"));
    });
    navLinks.querySelectorAll("a").forEach(function (a) {
      a.addEventListener("click", function () { setMenu(false); });
    });
    document.addEventListener("click", function (e) {
      if (!navLinks.contains(e.target) && e.target !== toggle) setMenu(false);
    });
    window.addEventListener("resize", function () {
      if (window.innerWidth > 860) setMenu(false);
    });
  }

  document.querySelectorAll("[data-demo-download]").forEach(function (el) {
    el.addEventListener("click", function (e) {
      var href = el.getAttribute("href") || "";
      if (!href || href === "#") {
        e.preventDefault();
        alert("正式发布后这里将提供下载；当前可在项目 04-发布输出 目录获取安装包与便携版。");
      }
    });
  });
})();
