# 团队成员头像

将成员头像集中放在此目录，文件名与 `platform_content.yml` 中的 `avatar_file` 一致。

- 推荐尺寸：320 × 400（4:5）
- 支持格式：WebP、PNG、JPEG
- 推荐命名：`员工工号.webp`
- 图片缺失时，前端自动显示姓名占位头像

生产环境可以通过 `PLATFORM_TEAM_AVATAR_DIR` 指向服务器外部挂载目录，无需重新构建前端。
