# Spider_XHS 登录与发布

## 适用范围

只复用本机已配置的 Spider_XHS 运行环境和其公开的 Creator Auth/API 入口，不复制或重写签名算法，不把 Cookie、二维码内部对象或会话材料写入聊天、文案、日志或素材目录。

## 本机运行配置

当前已配置的本机运行目录是 `F:/注册机/Spider_XHS`，Python 解释器是 `D:/environment/python.exe`。每次调用 skill 先执行自带的 `scripts/bootstrap_spider_xhs_runtime.ps1 -InstallPrerequisites`；已有环境会快速复用并验证，不要求用户手动判断依赖。随后再执行 `scripts/check_spider_xhs_runtime.py` 验收模块导入；检查脚本只检查本地目录和模块导入，不联网、不登录、不生成二维码。

如果直接调用 Python，显式设置模块路径，不依赖之前会话留下的环境变量：

```powershell
$env:PYTHONPATH = 'F:/注册机/Spider_XHS'
& 'D:/environment/python.exe' -c "from xhs_utils.xhs_auth import XHSCreatorAuth; from apis.xhs_creator_apis import XHS_Creator_Apis; print('Spider_XHS import OK')"
```

该目录已安装 `requirements.txt` 中的 Python 依赖，并在项目目录执行过 `npm install`。检查失败时先报告缺失目录、解释器或模块，状态为 `受阻`；不要把导入失败误判为账号未登录。

## 迁移到其他电脑

其他电脑没有 Spider_XHS 或依赖时，首次使用需要联网拉取项目并安装本地依赖。使用 skill 自带的 `scripts/bootstrap_spider_xhs_runtime.ps1`：

```powershell
& '<skill目录>/scripts/bootstrap_spider_xhs_runtime.ps1'
```

如果电脑缺少 Python 或 Node.js，skill 会自动尝试运行：

```powershell
& '<skill目录>/scripts/bootstrap_spider_xhs_runtime.ps1' -InstallPrerequisites
```

该选项使用 Windows `winget` 安装 Python 3.12 和 Node.js LTS，并在安装后重新查找解释器和 `npm.cmd`。没有 `winget`、安装源不可访问或权限不足时，只报告具体缺项，不会把依赖安装到共享盘。

脚本会按以下顺序处理：

1. 使用 `XHS_SPIDER_ROOT`，或用户指定的 `-Root`；没有指定时选择可用的非 C 盘并建立 `Codex\Spider_XHS`。
2. 从 `https://github.com/cv-cat/Spider_XHS` 拉取项目（优先 Git；没有 Git 时下载官方 ZIP；已有 checkout 则复用，不覆盖本地改动）。
3. 在项目目录创建 `.venv`，使用虚拟环境安装 `requirements.txt`，再补齐 Spider_XHS 当前 Creator 传输所需的 `curl_cffi` Chrome 150 指纹版本和二维码图片所需的 Pillow，并执行 `npm install`。
4. 运行 `check_spider_xhs_runtime.py` 验证模块可导入，并确认 `curl_cffi` 提供 `chrome150`；缺少该指纹时不得进入二维码登录。

自举会改变本机文件并访问 GitHub，首次执行前向用户说明目标目录和安装内容；共享盘 `\\172.16.11.3` 不参与自举。没有网络时不能在线拉取或安装：在可联网电脑下载 Spider_XHS 源码、Python 安装包、Node.js 安装包和 Python wheels，带到目标电脑的非 C 盘后离线安装，再运行 `scripts/bootstrap_spider_xhs_runtime.ps1 -Root '<目标目录>' -PythonPath '<目标 Python>' -CheckOnly`。`node_modules` 可以作为本地缓存复制，但 `.venv` 只有在目标电脑已有兼容 Python 且解释器路径可用时才适合复制；不要把跨电脑复制 `.venv` 当作 Python 安装替代方案。不能把依赖包或临时文件放到共享盘。

## 登录检查

### 本机 HTML 登录面板

如需让用户在浏览器中完成登录，使用 `scripts/launch_creator_login_panel.ps1`。它会先执行
运行环境自举，再启动 `scripts/creator_login_panel.py`，后者只绑定
`127.0.0.1`，由同一个 Python 进程调用 Spider_XHS 的二维码或手机号登录入口，并在
内存中保留最终 `XHSCreatorAuth`，并把最小会话快照保存为当前 Windows 用户和当前机器
绑定的 DPAPI 加密文件。HTML 不读取浏览器 Cookie，也不会收到 Cookie、二维码
URL、短信验证码或用户标识；接口只返回登录状态。关闭面板进程会释放会话，面板不使用
`localStorage`，磁盘只保存无法直接使用的加密会话文件；面板里的“清除本地登录缓存”
会删除该文件。

```powershell
& 'C:/Users/z/.codex/skills/xiaohongshu-publishing/scripts/launch_creator_login_panel.ps1' `
  -Root 'F:/注册机/Spider_XHS' `
  -OutputDir 'F:/注册机/xhs_login_panel_qr'
```

可选地使用 `-SessionFile` 指定非 `C:` 盘的加密会话文件路径；默认保存到
`<OutputDir>/creator-session.dpapi`。该文件只能由同一 Windows 用户在同一台机器上解密，
更换用户或机器后需要重新登录。

登录成功后，后续 Creator API 调用必须继续在该本机进程中完成；不得改为从网页端
提取或传输 Cookie。面板的 `/api/start`、`/api/input` 和 `/api/close` 受本次进程生成
的本地 UI token 保护，服务不记录请求体。

1. 有本地保存会话时，用 `XHSCreatorAuth.from_cookie(...)` 创建 Creator Auth，再创建 `XHS_Creator_Apis(creator_auth)` 并调用 `bootstrap()`。只有 Creator `user/info` 验收成功才算已登录。
2. 会话缺失、Cookie 不完整、`bootstrap()` 失败、返回访客状态或导入异常，都按未登录处理。
3. 未登录时必须立即生成二维码并展示给用户，不能只发送“未登录”文字。使用 skill 自带的 `scripts/creator_login_qr.py`：它拦截 Spider_XHS 的二维码图片回调，把二维码保存到本机非 C 盘，再用桌面图片预览/消息图片展示给用户；二维码 URL、Cookie、令牌和二维码内部对象不得输出到聊天或日志。
4. 展示二维码后保持同一进程等待扫码和手机确认，向用户报告状态：`待扫描`、`待手机确认`、`登录成功`、`二维码已过期` 或 `登录失败`。二维码过期时重新生成一次；连续两次失败就停止并说明原因。
5. 登录成功后在同一进程再次调用 `bootstrap()`，并保留会话对象给后续 API 使用。若桌面无法展示图片，才退回终端二维码；不得跳过二维码展示。

如果 Spider_XHS 不存在、依赖未安装、入口导入失败或会话无法验收，状态为 `受阻`；说明缺失的运行环境，不要改用未经验证的接口或假装登录成功。

## 发布调用

发布前再次执行：

```python
creator_api = XHS_Creator_Apis(creator_auth).bootstrap()
```

得到用户明确发布确认后再调用 `creator_api.post_note(note_info)`：

```python
{
    "title": "标题",
    "desc": "正文",
    "media_type": "image",  # 或 "video"
    "images": ["D:/工作目录/图片.jpg"],
    "topics": ["产品体验", "使用场景"],
    "type": 0,
}
```

`privacy_info.type` 的当前 Creator 请求语义为：`0`=公开，`1`=仅自己可见。发布图文默认必须传 `type: 0`；只有用户明确要求私密/仅自己可见时才改用 `1`，并在最终预览中明确展示可见性。视频使用本机视频路径并设置 `media_type: "video"`。地点、定时和其他可见性只有在用户明确提供时才传入。让 Spider_XHS 自己处理上传许可、签名、视频封面/转码和有限重试；不要在 skill 中复制这些实现。

发布成功后不要只依据 `success=true` 判定公开：记录返回的笔记 ID，并用 Creator 作品列表或可见的状态字段做一次结果核对；若发现为“仅自己可见”，先停止重复发布，报告实际可见性和笔记 ID，再按用户指示通过正常 Creator 页面调整。

只有返回 `success=true` 并取得明确成功信息或笔记链接，才将状态改为 `已发布`。遇到验证码、二次验证、账号异常、406、敏感词、业务参数错误或平台限制时停止并报告。

## 定时发布执行边界

定时发布不是提前调用 `post_note()`。任务必须先保存完整的本机发布包，并在预览中展示计划时间（统一使用 `Asia/Shanghai`）后取得用户明确确认。

- 当前已验证的 Spider_XHS `post_note(note_info)` 入口使用可选 `noteInfo["postTime"]` 接收定时发布时间；传入 13 位 Unix 毫秒时间戳，且仅在用户选择定时并明确确认后设置。执行前把用户填写的 `Asia/Shanghai` 时间转换为该时间戳并再次校验仍在未来；若本机 Spider_XHS 版本变更导致该字段未被验证，退回“仅保存并报告缺口”，不得猜测其他字段。
- 若没有可验证的原生定时入口，使用已配置的本机定时执行器在计划时间唤醒任务。执行器只引用保存包路径和非敏感元数据，不复制 Cookie、二维码 URL、短信验证码或明文密码。
- 到点执行前必须在同一台机器重新加载 DPAPI 会话并调用 `bootstrap()`；登录失效、验证码、二次验证、风控或平台限制时停止，状态记为 `待重新登录` 或 `受阻`，不得提前发布或伪造成功。
- 只有调度注册成功才记为 `待定时发布`，只有实际取得明确成功信息或笔记链接才记为 `已发布`。调度器不可用时只能记为 `已保存` 并报告缺口。

参考项目：[cv-cat/Spider_XHS](https://github.com/cv-cat/Spider_XHS)。
