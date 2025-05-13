from app.services.knowledge_service import KnowledgeService
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)

# 初始化知识服务
ks = KnowledgeService(local_kb_directory="./local_kb_docs/")

# 测试查询
test_queries = [
    "如何设置VPN?",
    "我忘记密码了，怎么重置?",
    "什么是公司的网络安全政策?",  # 这是一个可能在知识库中没有的问题
    "如何处理垃圾邮件",  # 对应"How to Deal with Spam"
    "获取Mac OS X更新", # 对应"Where can I obtain updates and new releases for Mac OS X"
    # 添加与您的ServiceNow文章相关的中文查询
]

# 运行测试
for query in test_queries:
    print(f"\n\n=== 测试查询: {query} ===")
    answer = ks.get_answer_from_kb(query)
    print(f"回答: {answer}")
