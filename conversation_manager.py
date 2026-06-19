# -*- coding: utf-8 -*-
import os
import json
import uuid
from datetime import datetime

# 对话存储目录
CONVERSATION_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "win")

# 确保目录存在
os.makedirs(CONVERSATION_DIR, exist_ok=True)


class ConversationManager:
    """对话管理器：支持多对话窗口，保存对话历史"""
    
    def __init__(self):
        self.conversations = {}  # 内存中的对话缓存
        self._load_all_conversations()
    
    def _get_file_path(self, conversation_id):
        """获取对话文件的完整路径"""
        return os.path.join(CONVERSATION_DIR, f"{conversation_id}.json")
    
    def _load_all_conversations(self):
        """加载所有已保存的对话"""
        if not os.path.exists(CONVERSATION_DIR):
            return
        
        for filename in os.listdir(CONVERSATION_DIR):
            if filename.endswith('.json'):
                conversation_id = filename[:-5]  # 去掉 .json
                file_path = os.path.join(CONVERSATION_DIR, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self.conversations[conversation_id] = data
                except Exception as e:
                    print(f"[对话管理] 加载对话失败 {conversation_id}: {e}", flush=True)
    
    def create_conversation(self, title="新对话"):
        """创建新对话"""
        conversation_id = str(uuid.uuid4())[:8]  # 生成短ID
        conversation = {
            "id": conversation_id,
            "title": title,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "messages": []  # 对话消息列表
        }
        self.conversations[conversation_id] = conversation
        self._save_conversation(conversation_id)
        return conversation_id
    
    def get_conversation(self, conversation_id):
        """获取指定对话"""
        return self.conversations.get(conversation_id)
    
    def get_all_conversations(self):
        """获取所有对话列表（按更新时间倒序）"""
        conversations = list(self.conversations.values())
        conversations.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return conversations
    
    def add_message(self, conversation_id, role, content, extra_data=None):
        """向对话中添加消息"""
        if conversation_id not in self.conversations:
            return False
        
        message = {
            "role": role,  # "user" 或 "bot"
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        # 添加额外数据（如思考过程、文件等）
        if extra_data:
            message.update(extra_data)
        
        self.conversations[conversation_id]["messages"].append(message)
        self.conversations[conversation_id]["updated_at"] = datetime.now().isoformat()
        
        # 更新标题（如果是第一条用户消息）
        if role == "user" and len(self.conversations[conversation_id]["messages"]) == 1:
            # 使用第一条消息的前20个字符作为标题
            title = content[:20] + "..." if len(content) > 20 else content
            self.conversations[conversation_id]["title"] = title
        
        self._save_conversation(conversation_id)
        return True
    
    def get_messages(self, conversation_id, limit=None):
        """获取对话的消息列表"""
        conversation = self.conversations.get(conversation_id)
        if not conversation:
            return []
        
        messages = conversation.get("messages", [])
        if limit:
            return messages[-limit:]
        return messages
    
    def get_context_for_llm(self, conversation_id, max_messages=5):
        """获取用于LLM上下文的最近消息（格式化）"""
        messages = self.get_messages(conversation_id, limit=max_messages)
        context = []
        
        for msg in messages:
            if msg["role"] == "user":
                context.append(f"用户: {msg['content']}")
            else:
                context.append(f"助手: {msg['content']}")
        
        return "\n".join(context)
    
    def delete_conversation(self, conversation_id):
        """删除对话"""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
        
        # 删除文件
        file_path = self._get_file_path(conversation_id)
        if os.path.exists(file_path):
            os.remove(file_path)
        return True
    
    def update_title(self, conversation_id, title):
        """更新对话标题"""
        if conversation_id not in self.conversations:
            return False
        
        self.conversations[conversation_id]["title"] = title
        self.conversations[conversation_id]["updated_at"] = datetime.now().isoformat()
        self._save_conversation(conversation_id)
        return True
    
    def _save_conversation(self, conversation_id):
        """保存对话到文件"""
        if conversation_id not in self.conversations:
            return
        
        file_path = self._get_file_path(conversation_id)
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.conversations[conversation_id], f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[对话管理] 保存对话失败 {conversation_id}: {e}", flush=True)


# 全局对话管理器实例
conversation_manager = ConversationManager()
