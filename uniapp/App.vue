<script setup>
import { onLaunch, onShow, onHide } from '@dcloudio/uni-app'

onLaunch(() => {
  console.log('App Launch')
})

onShow(() => {
  console.log('App Show')
})

onHide(() => {
  console.log('App Hide')
})
</script>

<style>
/* 全局样式 */
page {
  background-color: #f7f7f8;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
  height: 100vh;
  /* iOS 平滑滚动 */
  -webkit-overflow-scrolling: touch;
  /* 禁用 iOS 点击高亮 */
  -webkit-tap-highlight-color: transparent;
  /* iOS 文字大小调整（防止横屏时文字变大） */
  -webkit-text-size-adjust: 100%;
}

/* iOS 安全区域适配 */
/* iPhone X 及以上底部横条 */
@supports (padding-bottom: env(safe-area-inset-bottom)) {
  .safe-area-bottom {
    padding-bottom: env(safe-area-inset-bottom);
  }
}

/* iOS 输入框聚焦时不缩放 */
@media screen and (max-width: 500px) {
  input, textarea {
    font-size: 16px !important; /* 防止 iOS 自动放大 */
  }
}

/* 通用变量 */
:root {
  --color-primary: #4d6bfe;
  --color-primary-light: #6b85ff;
  --color-bg-page: #f7f7f8;
  --color-bg-card: #ffffff;
  --color-text-primary: #1d2129;
  --color-text-secondary: #4e5969;
  --color-text-hint: #86909c;
  --color-border: #e5e6eb;
  --radius-sm: 8rpx;
  --radius-md: 16rpx;
  --radius-lg: 24rpx;
  --shadow-card: 0 2rpx 12rpx rgba(0, 0, 0, 0.08);
}
</style>
