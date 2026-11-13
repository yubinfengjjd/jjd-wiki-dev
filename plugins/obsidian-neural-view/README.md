# 科研知识库神经图谱 · native Obsidian view

本地只读 ItemView，原版光球视频、五只水母、Canvas 粒子与神经丝、伞状展开和详情侧栏。条目来自当前 vault 的 `layouts/*.md`、`templates/*.md`、`methods/*.md`、`interfaces/*.md`、`projects/*.md`；子目录资源、verify/source、索引和日志不建节点。空模块保持 0，不填示例。

只显示明确的页面链接，不从标签、正文相似或 raw status 计算语义兼容性。已有 status 仅标为原始 frontmatter 字段。未解析及范围外引用禁用，点击不会创建空笔记。打开时重新核对当前 vault 的精确路径与 `TFile`，通过原生 leaf `openFile` 打开；已删除或移动的旧图谱条目不会创建空白笔记。图谱插件不修改 Markdown/frontmatter、不保存业务状态、不使用 localStorage、不联网。

## Build and checks

```powershell
cd E:\research-wiki\开发\obsidian-neural-view
npm ci --ignore-scripts
npm run verify
```

`dist/` 是插件安装内容。将其复制到目标 vault 的 `.obsidian/plugins/research-wiki-neural-view/`，在社区插件中启用。插件使用 Obsidian 的 `vault.getMarkdownFiles()`、`cachedRead()`、`metadataCache.getFileCache()`、`getFirstLinkpathDest()`；媒体路径由 vault adapter 的 `getResourcePath()` 产生。没有 filesystem/Node 读取 vault 的运行时代码。

功能入口：左侧 network 图标，或命令面板“科研知识库 · 神经图谱: 打开科研神经图谱”。空工作区加载后打开图谱；已有布局和原生笔记保持原有焦点。已存在图谱复用，不重复创建。

图谱加载时、点击刷新时及元数据或文件事件后重新读取；隐藏标签暂停视频及绘图工作，关闭视图/禁用插件取消 rAF、暂停视频、断开 ResizeObserver/IntersectionObserver 并卸载 React。11 条一页，避免大量真实笔记重叠，保留完整筛选与分页。Escape 只在图谱中返回上一层。

## Isolated visual harness

```powershell
npm run build
npm run preview
```

打开 `http://127.0.0.1:5178`。这是明确标记的五条 fixture，实际 vault 不对服务器开放；fixture 不进入 `dist/main.js`。视觉核对原 Scene/Canvas、五模块、扇形、详情、暂停/重播；原生打开与 Obsidian 媒体解码应在真实 Obsidian 中验收。

## License and provenance

来源、上游固定版本与每类文件改动见 `PROVENANCE.md`。阅读保留的 `LICENSE`、`NOTICE.md` 与 `licenses/MIT-legacy.txt`；当前上游包含 PolyForm 非商业条款、旧 MIT 授权例外及 AI 素材权利限制，不能将整个集成目录称作 MIT 作品。
