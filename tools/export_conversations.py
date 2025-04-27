#!/usr/bin/env python3
"""
工具脚本：导出Redis中保存的对话记录用于评估

这个脚本用于从Redis中导出保存的对话记录，可以按日期范围、特定用户或特定渠道进行过滤，
并输出为JSON格式以便进行评估和分析。
"""
import sys
import os
import json
import argparse
import datetime
from typing import List, Dict, Any, Optional

# 将项目根目录添加到Python路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from app.services.state_service import redis_client, get_conversation, list_conversations

def parse_key(key: str) -> Dict[str, str]:
    """解析Redis键，提取用户ID和频道ID"""
    parts = key.split(":")
    if len(parts) >= 3 and parts[0] == "conversation":
        return {
            "user_id": parts[1],
            "channel_id": parts[2]
        }
    return {}

def filter_by_date(conversations: List[Dict], start_date: Optional[datetime.datetime] = None, 
                  end_date: Optional[datetime.datetime] = None) -> List[Dict]:
    """按日期范围过滤对话"""
    if not start_date and not end_date:
        return conversations
        
    filtered = []
    for conv in conversations:
        messages = conv.get("messages", [])
        # 使用第一条消息的时间戳确定对话开始时间
        if messages:
            first_msg_ts = float(messages[0].get("ts", 0))
            msg_date = datetime.datetime.fromtimestamp(first_msg_ts)
            
            if start_date and msg_date < start_date:
                continue
                
            if end_date and msg_date > end_date:
                continue
                
            filtered.append(conv)
    
    return filtered

def get_all_conversations(user_id: Optional[str] = None, channel_id: Optional[str] = None) -> List[Dict]:
    """获取所有对话记录，可按用户ID或频道ID过滤"""
    all_convs = []
    
    # 获取所有对话键
    all_keys = list_conversations()
    
    for key in all_keys:
        key_info = parse_key(key)
        
        # 如果指定了过滤条件但不匹配，则跳过
        if user_id and key_info.get("user_id") != user_id:
            continue
            
        if channel_id and key_info.get("channel_id") != channel_id:
            continue
            
        # 获取对话内容
        current_user_id = key_info.get("user_id")
        current_channel_id = key_info.get("channel_id")
        
        if current_user_id and current_channel_id:
            messages = get_conversation(current_user_id, current_channel_id)
            
            if messages:
                all_convs.append({
                    "user_id": current_user_id,
                    "channel_id": current_channel_id,
                    "messages": messages
                })
    
    return all_convs

def export_conversations(output_file: str, user_id: Optional[str] = None, 
                         channel_id: Optional[str] = None,
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None,
                         pretty_print: bool = False) -> None:
    """导出对话记录到JSON文件"""
    # 解析日期范围
    start_datetime = None
    end_datetime = None
    
    if start_date:
        start_datetime = datetime.datetime.fromisoformat(start_date)
        
    if end_date:
        end_datetime = datetime.datetime.fromisoformat(end_date)
    
    # 获取对话记录
    conversations = get_all_conversations(user_id, channel_id)
    
    # 按日期过滤
    if start_datetime or end_datetime:
        conversations = filter_by_date(conversations, start_datetime, end_datetime)
    
    # 输出到文件
    indent = 2 if pretty_print else None
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(conversations, f, ensure_ascii=False, indent=indent)
    
    print(f"已导出 {len(conversations)} 个对话到 {output_file}")
    
    # 输出每个对话的基本信息
    for i, conv in enumerate(conversations):
        user_id = conv.get("user_id")
        channel_id = conv.get("channel_id")
        message_count = len(conv.get("messages", []))
        
        # 获取对话的开始和结束时间
        start_time = None
        end_time = None
        messages = conv.get("messages", [])
        
        if messages:
            start_ts = float(messages[0].get("ts", 0))
            end_ts = float(messages[-1].get("ts", 0))
            
            start_time = datetime.datetime.fromtimestamp(start_ts).strftime("%Y-%m-%d %H:%M:%S")
            end_time = datetime.datetime.fromtimestamp(end_ts).strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"对话 {i+1}: 用户 {user_id}, 频道 {channel_id}, 消息数 {message_count}")
        print(f"  开始时间: {start_time}")
        print(f"  结束时间: {end_time}")
        print("-" * 50)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="导出Redis中保存的对话记录")
    parser.add_argument("-o", "--output", required=True, help="输出文件路径")
    parser.add_argument("-u", "--user", help="按用户ID过滤")
    parser.add_argument("-c", "--channel", help="按频道ID过滤")
    parser.add_argument("-s", "--start-date", help="开始日期 (YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS)")
    parser.add_argument("-e", "--end-date", help="结束日期 (YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS)")
    parser.add_argument("-p", "--pretty", action="store_true", help="美化JSON输出")
    
    args = parser.parse_args()
    
    if not redis_client:
        print("错误: 无法连接到Redis服务器")
        sys.exit(1)
    
    try:
        export_conversations(
            args.output,
            args.user,
            args.channel,
            args.start_date,
            args.end_date,
            args.pretty
        )
    except Exception as e:
        print(f"错误: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()