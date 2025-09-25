from .hr_agent import HRKnowledgeBaseAgent

if __name__ == "__main__":
    agent = HRKnowledgeBaseAgent()

    query = """
    请帮我为员工张三生成一份B1模板的警告文档，
    违规原因是多次迟到，职位是工程师，员工ID是666，部门是研发部，经理是李四，违规详情是经常上班迟到早退。
    """
    result = agent.generate_answer(query)
    print(result)
