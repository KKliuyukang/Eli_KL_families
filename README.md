# KL 2026 Family Board

一个本地的小网页，用来整理 kindy 班级里孩子、父母、照片和聊天证据。

## 现在包含

- 从 `_chat.txt` 自动抽取家庭介绍消息
- 生成孩子 + 父母 + WhatsApp 名称 + 聊天证据
- 首页家庭卡片墙
- 父母图库视图
- 待归类图片收件箱
- 为后续手工补充父母照片预留 `manual_assets/assignments.json`

## 如何刷新数据

在项目根目录运行：

```bash
python3 scripts/build_family_data.py
```

## 如何打开网页

直接打开这个文件即可：

- `app/index.html`

如果浏览器限制本地脚本，也可以在项目根目录启动一个本地服务：

```bash
python3 -m http.server 8000
```

然后访问：

- `http://localhost:8000/app/`

手机在同一 Wi‑Fi 下访问时，也可以直接打开：

- `http://你的电脑局域网IP:8000/app/`

例如 `http://192.168.1.23:8000/app/`

## 如何生成可发布的网站

运行：

```bash
python3 scripts/build_static_site.py
```

会生成一个可独立部署的目录：

- `site/`

这个目录可以直接上传到静态托管服务，例如 GitHub Pages、Cloudflare Pages、Netlify 或 Vercel。

本地预览：

```bash
python3 -m http.server 8000 --directory site
```

然后访问：

- `http://localhost:8000/`

手机在同一 Wi‑Fi 下访问：

- `http://你的电脑局域网IP:8000/`

如果想在外面也能访问，最稳的方式是把 `site/` 部署到一个公开静态站点域名上。

## 用 GitHub Pages 发布

这个项目已经包含 GitHub Pages 工作流：

- `.github/workflows/pages.yml`

推荐流程：

1. 在 GitHub 新建一个仓库
2. 把当前目录推到 `main` 分支
3. 在 GitHub 仓库里打开 `Settings -> Pages`
4. 在 `Source` 里选择 `GitHub Actions`
5. 等待 `Deploy family board to GitHub Pages` 工作流跑完

发布后地址通常会是：

- `https://你的用户名.github.io/仓库名/`

GitHub 官方文档也推荐用 GitHub Actions 发布自定义静态站点：

- [Using custom workflows with GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [Configuring a publishing source for your GitHub Pages site](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)

## 如何手工补父母照片

1. 把照片放进 `manual_assets/`
2. 编辑 `manual_assets/assignments.json`
3. 重新运行 `python3 scripts/build_family_data.py`

配置示例：

```json
{
  "items": [
    {
      "family_id": "eli",
      "file": "manual_assets/lily-photo.jpg",
      "category": "mother",
      "note": "校门口常见的妈妈照片",
      "tag": "manual-photo"
    }
  ]
}
```

`category` 当前支持：

- `mother`
- `father`
- `parent`
- `family`
- `child`
- `screenshots`
- `unknown`
