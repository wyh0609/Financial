<template>
  <div class="sidebar">
    <div class="sidebar-header">
      <div class="sidebar-brand">
        <span class="brand-icon">💹</span>
        <span class="brand-name">ChatFinance</span>
      </div>
      <button class="new-chat-btn" @click="$emit('new-chat')">
        <span>+</span>
        <span>新建对话</span>
      </button>
    </div>
    <div class="conversation-list">
      <div v-for="conv in conversations" :key="conv.id"
           :class="['conversation-item', { active: currentConversationId === conv.id }]"
           @click="$emit('switch-chat', conv.id)">
        <span class="icon">💬</span>
        <span class="title">{{ conv.title }}</span>
        <button class="delete-btn" @click.stop="$emit('delete-chat', conv.id)">✕</button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  conversations: { type: Array, default: () => [] },
  currentConversationId: { type: String, default: null },
})

defineEmits(['new-chat', 'switch-chat', 'delete-chat'])
</script>

<style scoped>
.sidebar {
  width: 260px;
  background: #1e1e2e;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  border-right: none;
}

.sidebar-header {
  padding: 20px 16px 12px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  padding: 0 4px;
}

.sidebar-brand .brand-icon {
  font-size: 22px;
}

.sidebar-brand .brand-name {
  font-size: 17px;
  font-weight: 700;
  color: #e0e0e0;
  letter-spacing: -0.3px;
}

.new-chat-btn {
  width: 100%;
  padding: 10px;
  background: rgba(255,255,255,0.06);
  color: #c0c0d0;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 10px;
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: all 0.2s;
}

.new-chat-btn:hover {
  background: rgba(255,255,255,0.12);
  color: #fff;
  border-color: rgba(255,255,255,0.18);
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.conversation-list::-webkit-scrollbar {
  width: 4px;
}

.conversation-list::-webkit-scrollbar-thumb {
  background: rgba(255,255,255,0.15);
  border-radius: 2px;
}

.conversation-item {
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 2px;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.15s;
  position: relative;
}

.conversation-item:hover {
  background: rgba(255,255,255,0.08);
}

.conversation-item.active {
  background: rgba(77, 107, 254, 0.2);
  border-left: 3px solid #4d6bfe;
}

.conversation-item .icon {
  font-size: 14px;
  flex-shrink: 0;
  opacity: 0.6;
}

.conversation-item .title {
  flex: 1;
  font-size: 13px;
  color: #b0b0c0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.conversation-item.active .title {
  color: #e0e0f0;
}

.conversation-item .delete-btn {
  opacity: 0;
  background: none;
  border: none;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
  color: rgba(255,255,255,0.3);
  font-size: 12px;
}

.conversation-item:hover .delete-btn {
  opacity: 1;
}

.conversation-item .delete-btn:hover {
  background: rgba(217, 48, 37, 0.25);
  color: #ff6b6b;
}
</style>
