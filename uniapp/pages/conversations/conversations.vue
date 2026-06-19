<template>
  <view class="page">
    <!-- 对话列表 -->
    <view v-if="conversations.length > 0" class="conv-list">
      <view
        v-for="(item, idx) in conversations"
        :key="idx"
        class="conv-item"
        @click="switchConv(item)"
      >
        <view class="conv-icon">💬</view>
        <view class="conv-info">
          <text class="conv-title">{{ item.title }}</text>
          <text class="conv-time">{{ formatTime(item.updated_at) }}</text>
        </view>
        <view class="conv-actions">
          <view class="delete-btn" @click.stop="deleteConv(item)">
            <text>✕</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 空状态 -->
    <view v-else class="empty-state">
      <text class="empty-icon">💬</text>
      <text class="empty-text">暂无对话记录</text>
    </view>

    <!-- 新建按钮 -->
    <view class="new-btn" @click="createNew">
      <text>+ 新建对话</text>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import {
  fetchConversations,
  createConversation,
  deleteConversation as delConv
} from '../../utils/api.js'

const conversations = ref([])

onShow(async () => {
  await loadList()
})

async function loadList() {
  try {
    const data = await fetchConversations()
    if (data.conversations) {
      conversations.value = data.conversations
    }
  } catch (e) {
    console.error('[Conv] 加载失败:', e)
  }
}

function switchConv(item) {
  // 通过事件总线或 storage 通知首页切换
  uni.setStorageSync('switchConversation', item.id)
  uni.navigateBack()
}

function formatTime(timeStr) {
  if (!timeStr) return ''
  const d = new Date(timeStr)
  const now = new Date()
  const diff = now - d
  
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前'
  if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前'
  
  return `${d.getMonth()+1}/${d.getDate()}`
}

async function createNew() {
  try {
    uni.showLoading({ title: '创建中...' })
    await createConversation('新对话')
    uni.hideLoading()
    uni.setStorageSync('switchConversation', null)
    uni.navigateBack()
  } catch (e) {
    uni.hideLoading()
    uni.showToast({ title: '创建失败', icon: 'none' })
  }
}

async function deleteConv(item) {
  const res = await uni.showModal({ title: '确认删除', content: `确定删除「${item.title}」吗？` })
  if (!res.confirm) return
  
  try {
    await delConv(item.id)
    await loadList()
    uni.showToast({ title: '已删除', icon: 'success' })
  } catch (e) {
    uni.showToast({ title: '删除失败', icon: 'none' })
  }
}
</script>

<style lang="scss" scoped>
.page {
  min-height: 100vh;
  background: #f7f7f8;
  padding-bottom: 140rpx;
}

.conv-list {
  padding: 20rpx 24rpx;
}

.conv-item {
  display: flex;
  align-items: center;
  gap: 20rpx;
  background: #fff;
  border-radius: 16rpx;
  padding: 28rpx 24rpx;
  margin-bottom: 16rpx;
  box-shadow: 0 2rpx 12rpx rgba(0,0,0,0.06);
  
  &:active { background: #fafbfc; }
  
  .conv-icon { font-size: 40rpx; flex-shrink: 0; }
  
  .conv-info {
    flex: 1;
    min-width: 0;
    
    .conv-title {
      font-size: 30rpx;
      font-weight: 500;
      color: #333;
      display: block;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    
    .conv-time {
      font-size: 24rpx;
      color: #999;
      margin-top: 6rpx;
      display: block;
    }
  }
  
  .conv-actions {
    .delete-btn {
      width: 56rpx;
      height: 56rpx;
      border-radius: 50%;
      background: #fef0f0;
      display: flex;
      align-items: center;
      justify-content: center;
      
      text { color: #f53f3f; font-size: 26rpx; }
      
      &:active { background: #fdece8; }
    }
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding-top: 200rpx;
  gap: 16rpx;
  
  .empty-icon { font-size: 80rpx; }
  .empty-text { font-size: 28rpx; color: #999; }
}

.new-btn {
  position: fixed;
  left: 32rpx;
  right: 32rpx;
  bottom: calc(40rpx + env(safe-area-inset-bottom));
  height: 96rpx;
  background: linear-gradient(135deg, #4d6bfe 0%, #6b85ff 100%);
  border-radius: 48rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  
  text {
    font-size: 30rpx;
    color: #fff;
    font-weight: 600;
  }
  
  &:active { opacity: 0.85; }
}
</style>
