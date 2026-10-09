# 从源码构建

[← 返回首页](../README.md) · [架构](ARCHITECTURE.md) · [验证](VERIFICATION.md)

## 先分清两个目标

| 目标 | 必需资源 |
| --- | --- |
| 检查公开源码 | Git、Node.js 24，不需要账号/APK |
| 启动开发版 | Apple Silicon、macOS 13+、Python 3.11+、私有原始 `.13` ZIP |
| 组装 Mac ZIP | 源码工具、Python、原始 `.13` ZIP，Windows 也可交叉组包 |
| 修改 Java 连接层 | 另需 JDK 17、Maven 3 和自行准备的原生资源 |

## 检查与编译

```bash
git clone https://github.com/lhl1/hongguoL-macOS-ARM64.git
cd hongguoL-macOS-ARM64
npm ci
npm run build
npm test
```

npm 按锁文件下载依赖，包括 Electron。build 运行 TypeScript 和 Vite；测试使用合成响应，不读私人账号。依赖下载需网络，离线测试不请求原服务。

## 基线资源

原始 `.13` ARM64 ZIP 的 SHA256：

```text
4c03646010252092f61a8da4c152825c51b1e95f2098087af68e7f8b453bef45
```

这是文件校验值，不是播放密钥或下载地址。用 `shasum -a 256 文件.zip` 比较。基线没有放入仓库，脚本也不会下载；不要绕过哈希检查接受未知组件。

在 Apple Silicon Mac 上：

```bash
npm run prepare:mac -- --baseline "/你的路径/原始-.13-macOS-arm64.zip"
npm start
```

准备脚本只向 `native-resources-macos/arm64/` 提取资源，检查路径边界并保留权限与链接，不改系统设置。已有目录拒绝覆盖，先备份移开。脚本不全局解除隔离；开发版若被系统拒绝，优先用完整组包和准备流程检查。

资源含 JRE、Java JAR、APK 原生库和 FFmpeg，全部被 Git 忽略。SDK 身份字段 6、7、8、9、13 必须为空；启动后新建服务游客会话。

## 本地组包

```bash
npm run pack:mac -- --baseline "/你的路径/原始-.13-macOS-arm64.zip"
```

构建界面后，脚本生成 app.asar，用它和版本 plist 更新基线，保留其余组件字节/权限，再生成完整校验清单。输出目录已存在会拒绝覆盖。

```text
release-macos-2.3.4-arm64/
  Hongguo-2.3.4-macOS-arm64.zip
  SHA256SUMS.txt
  macOS发布校验.json
  app.asar
```

2.3.4 的 bundle build 为 2340。公开界面源码使用原创 SVG，基线应用图标保留在私有成品内。因此开源构建的整体哈希不等于以前本地成品，原生资源则保持一致。工具不会偷偷重新下载/替换 JNI 或 FFmpeg。

交叉组包不等于运行 Mac 程序。所有新包仍需在 Mac 上运行 `准备Mac版.command` 做本机签名和首帧自检。更换基线、Electron 或原生组件需要重新研究，不只是改版本号。完整输出包含第三方资源，不能当作 MIT 下可任意分发的文件。

## Java 适配器

`native-adapter/` 是本项目编写的连接层，已去除研究入口与私人配置。源码目标 JDK 17：

```bash
mvn -f native-adapter/pom.xml package -DskipTests dependency:copy-dependencies
```

产物在 `native-adapter/target/`。替换本地 JAR 前先备份，保留依赖 LICENSE/NOTICE，在 Mac 验证注册、请求、播放与签名；默认构建直接复用核实过的基线，不替换组件。

## 集成验证

```bash
npm run test:live
npm run test:desktop
```

需要本地资源且真实访问服务。前者检查游客、目录和视频信息，不等于画面播放；后者使用隐藏静音 Electron 窗口检查页面/播放，不读取已登录账号、不发短信、不抢占活动窗口。缺少本地 HEIC 样本与资源时，可选图片测试明确跳过。详见[验证文档](VERIFICATION.md)。
