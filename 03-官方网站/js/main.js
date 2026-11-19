/* 官网交互：导航高亮、FAQ、下载提示、年份。纯原生 JS，无外部依赖。 */
(function () {
  "use strict";
  var page = location.pathname.split("/").pop() || "index.html";
  document.querySelectorAll("nav.links a").forEach(function (a) {
    if (a.getAttribute("href") === page) a.classList.add("active");
  });
  var y = document.getElementById("year");
  if (y) y.textContent = new Date().getFullYear();

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
