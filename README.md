# Sinotech Hugo 本地网站

来源：https://www.sinotech.ch/ ，采集日期 2026-10-26。

## 使用

安装 Hugo 后在此目录执行 `hugo server`，访问 http://localhost:1313/ 。Windows 可运行 `start.ps1`。

静态构建：`hugo --minify`，输出在 `public/`。部署前把 `hugo.toml` 的 baseURL 改为正式地址。

## 内容与证据

- `content/posts/`：原站文章正文，保留原始文章 URL、日期、分类与来源。
- `content/pages/`：协会介绍、分会、组织机构等页面。
- `static/wp-content/uploads/`：本地化的原站图片及附件。
- `archive/html/`：下载的原始 HTML，用于核对与重新转换。
- `archive/reports/`：页面、资源、SHA-256、采集范围、失败与校验清单。
- `scripts/`：可重复运行的采集和转换脚本。

没有把外站链接的整个网站纳入采集；无法访问的资源、外部在线播放器等以失败清单及原链接为准。内容保留历史原文，导航和视觉样式已重建。

## 本次采集结果

466 篇文章（2009-03-23 至 2022-10-22）、54 个协会/图片附件说明页、799 份原始 HTML、428 个资源文件。
原站有 25 个页面链接及 734 个资源地址无法访问。5 个页面仅有标题；573 处缺失图片引用已标示为原站不可用。
这份结果覆盖公开页面递归链接和47页主文章列表，不能代表原服务器未公开的数据库、无链接文件或历史已删除资料。

构建校验：767 个 HTML 文件，本地引用缺失0，外部嵌入资源0；搜索索引520条。浏览器实测“春晖杯”返回69条。

重新采集：先用 pip 将 beautifulsoup4 安装到 `.deps`，依次执行 `scripts/crawl.py`、`scripts/repair.py`、`scripts/finalize.py`。已有下载缓存会复用。
原文 HTML 可用于回溯；`failures.json` 保留最初失败记录，`unresolved.json` 记录恢复尝试后仍不可访问的地址。
