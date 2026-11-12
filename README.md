# research-wiki 开发与完整技能包

`staged/research-wiki/` 是完整技能目录，包含 SKILL.md、后端、脚本、参考资料、测试、配置示例及已构建的 `app/` 网页资源。前端源码与锁文件保留在 `frontend/`。字体许可位于 `staged/research-wiki/app/licenses/`。

复制技能目录到宿主的技能根后，将 `config.example.json` 复制为本机 `config.json`，填写知识库、画廊、解释器与工具路径。配置示例中的尖括号是待替换占位符。依赖清单为 `requirements.lock.txt`；安装依赖前由作者确认。知识库内容单独保存在 [jjd-wiki](https://github.com/yubinfengjjd/jjd-wiki)。本机配置、虚拟环境、缓存与私有课题数据不分发。

前端更新后，在已有依赖的 `frontend/` 中运行 `npm test` 和 `npm run build`，提交重新生成的 `staged/research-wiki/app/`。构建会从 `frontend/public/licenses/` 自动复制字体许可原文。后端检查在技能目录运行 `python -X utf8 -m pytest -m "not r and not compose and not local"`，本机 Windows 应使用作者指定的实际 Python 解释器。

GitHub 同步与部署到本机技能目录是两个动作；同步本仓库不会更新已安装的副本或修改知识库状态。
