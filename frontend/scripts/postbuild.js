// 微信小程序构建后钩子：复制 sitemap.json 到产物根目录。
// uni-app 的 static/ 目录会整体复制到产物里（dist/.../static/sitemap.json），
// 但微信开发者工具要求 sitemap.json **必须在产物根目录**，否则模拟器不渲染。
// 运行时机：npm run build:mp-weixin / dev:mp-weixin 的 && 后缀
const fs = require('fs');
const path = require('path');

// __dirname = scripts/，回到上一级才是项目根
const root = path.resolve(__dirname, '..');
const src = path.join(root, 'src', 'static', 'sitemap.json');
const dests = [
  path.join(root, 'dist', 'build', 'mp-weixin', 'sitemap.json'),
  path.join(root, 'dist', 'dev', 'mp-weixin', 'sitemap.json'),
];

for (const dest of dests) {
  try {
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    fs.copyFileSync(src, dest);
    console.log(`[sitemap] copied → ${path.relative(root, dest)}`);
  } catch (e) {
    // dev 目录可能尚未存在，静默即可
    console.log(`[sitemap] skip ${path.relative(root, dest)}: ${e.code || e.message}`);
  }
}