# Windows 安装包发布流程

每次完成可交付安装包后，提交并推送源码，发布 GitHub Release，并记录过程。当前仓库为 `Lovis-Log/quant-lab-cn-hk`；源码仓库保持原有可见性，安装包放在 Release 附件中。

1. 更新 `VERSION`、CHANGELOG 和本次发布说明。采用语义版本号；验证尚不完整的版本用 `-rc.N` 并标记预发布。
2. 从干净提交运行 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build_windows.ps1 -BuildInstaller`。默认先跑 pytest，失败会停止；发布构建不使用 `-SkipTests`。
3. 运行 `.\.venv\Scripts\python.exe tools\verify_packaged.py --offline`，记录实际测试结果。桌面 GUI、真实行情、安装/卸载各自记录，未验证不能写成通过。
4. 检查 `dist/release/<版本>/build-manifest.json` 的源码提交、测试状态和安装包 SHA-256。完整构建日志留在同目录 `build.log`。
5. 为构建提交创建并推送 `v<版本>` 标签；准备发布说明、版本化安装包、SHA256SUMS.txt 和构建记录。
6. 使用 `.\.venv\Scripts\python.exe tools\publish_release.py --tag v<版本> --notes <发布说明路径> --assets <附件路径...> --receipt <回执路径>`；候选版本加 `--prerelease`。脚本先上传到草稿，核对每个附件的远程大小和 SHA-256 后发布，不覆盖旧版。
7. 将公开元数据回执、实际命令与验证结果记录到 `docs/releases/`，提交并推送。交付 Release 链接。

发布脚本只读取 `GH_TOKEN`/`GITHUB_TOKEN` 或已有 Git 凭据管理器，凭据不写入文件与日志。可用 `--list` 只读查看现有 Release。

## 发布记录

| 版本 | 状态 | 记录 |
| --- | --- | --- |
| v1.1.0-rc.1 | 准备中，预发布 | [发布说明与过程](releases/v1.1.0-rc.1.md) |
