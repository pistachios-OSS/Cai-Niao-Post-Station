# file_recognizer.py
from typing import Dict, List
from pathlib import Path

# 映射中文名称
FILE_CATEGORIES = {
    "BCEA-LRA": {
        "files": [
            "BASIC CONDITIONS OF EMPLOYMENT ACT 1997.pdf",
            "NO.66 OF 1995 LABOUR RELATIONS ACT 1995.pdf"
        ],
        "category": "legal",
        "chinese_name": "法律法规"
    },
    "Employee Details": {
        "files": [
            "CG Botha Payroll Data.xlsx",
            "TCSA Payroll Data.xlsx",
            "TCSAS Payroll Data.xlsx"
        ],
        "category": "employee_data",
        "chinese_name": "员工数据"
    },
    "Employment Agreement": {
        "files": [
            "HR-Employee Performance Review Document - April 2024",
            "HR-Standard Agreement-2024-03"
        ],
        "category": "agreements",
        "chinese_name": "协议合同"
    },
    "Policies": {
        "files": [
            "Affiliation and Interconnectedness of Internal Entities within Tax Consulting SA.pdf",
            "Company Dress Code Policy 2024.pdf",
            "HR-Bursary-Agreement-and-Policy-2019.pdf",
            "HR-Drugs-Alcohol-Substance-Abuse-Policy-2019.pdf",
            "HR-Electronic-Communications-Information-Policy-V202103.pdf",
            "HR-Employee-Wellness-Policy-2019.pdf",
            "HR-Gift-Policy-2019-Finalised.pdf",
            "HR-Grievance Procedure Policy.pdf",
            "HR-Harassment-Policy-2023-02.pdf",
            "HR-HIV-Aids-Policy-2019.pdf",
            "HR-Private Arbitration Policy For Dispute Resolution.pdf",
            "HR-Remote Working Policy-V2025-05.pdf",
            "HR-Smoking-Policy-2019.pdf",
            "HR-Study-Leave-Policy.pdf",
            "HR-TCSA-6-Month-Bonus-Incentive-Policy-Termination-included-July 2020.pdf",
            "HR-Telephone-Etiquette-Policy.pdf",
            "HR-Unfair-Discrimination-Harrassment-Policy.pdf",
            "HR-Work-Performance-Appraisal-Policy.pdf",
            "Leave-Policy-2024-Master Template.pdf",
            "SOP-Invoice-Quote-Debt-Collection-2020-02-12.pdf"
        ],
        "category": "policies",
        "chinese_name": "政策文档"
    },
    "Rules": {
        "files": [
            "HR-Central Point Important Company Rules and Response Times-2025"
        ],
        "category": "rules",
        "chinese_name": "公司规章"
    },
    "Templates": {
        "files": [
            "Disciplinary Codes & Procedures-Annex B1-Written-Warning-Template-2021.docx",
            "Disciplinary Codes & Procedures-Annex B2-Final-Warning-Template-2021.docx",
            "Disciplinary Codes & Procedures-Annex E- Lodging of Appeal-2017-Finalised.docx",
            "Disciplinary Codes & Procedures-Annex F-Resignation-Form-2017-Finalised.docx",
            "Disciplinary Codes & Procedures-Annex-C-Notice-Of-Hearing-Template-2017-Finalised.docx",
            "Disciplinary Codes & Procedures-Annex-D-Disciplinary-Report- form-2017-Finalised.docx",
            "Disciplinary Codes & Procedures-Annex-G-Final-Settlement-Form-2017-Finalised.docx",
            "Disciplinary Codes & Procedures-Annex-H-Termination-Of-Employment-Form-2017-Finalised.docx"
        ],
        "category": "templates",
        "chinese_name": "模板文档"
    }
}

def get_file_category(file_name: str) -> Dict[str, str]:
    """
    根据文件名返回其分类信息。
    
    Args:
        file_name (str): 文件名（包括扩展名）
        
    Returns:
        Dict[str, str]: 包含分类名称、英文类别和中文名称，找不到则返回默认值
    """
    for folder, info in FILE_CATEGORIES.items():
        if file_name in info["files"]:
            return {
                "folder": folder,
                "category": info["category"],
                "chinese_name": info["chinese_name"]
            }
    return {
        "folder": "Unknown",
        "category": "unknown",
        "chinese_name": "未知"
    }

def get_files_in_category(category: str) -> List[str]:
    """
    返回指定分类下的所有文件名。
    
    Args:
        category (str): 文件分类（英文名称，如 'policies', 'legal'）
        
    Returns:
        List[str]: 该分类下的文件列表
    """
    for info in FILE_CATEGORIES.values():
        if info["category"] == category:
            return info["files"]
    return []

def scan_directory(directory: Path) -> Dict[str, List[str]]:
    """
    扫描目录，按分类整理文件。
    
    Args:
        directory (Path): 要扫描的目录路径
        
    Returns:
        Dict[str, List[str]]: 分类结果，包含每个分类及其文件列表
    """
    categorized_files = {info["category"]: [] for info in FILE_CATEGORIES.values()}
    categorized_files["unknown"] = []
    
    if not directory.exists():
        return categorized_files
    
    for file_path in directory.glob("*"):
        if file_path.is_file():
            category_info = get_file_category(file_path.name)
            categorized_files[category_info["category"]].append(file_path.name)
    
    return categorized_files

def validate_files(directory: Path) -> Dict[str, List[str]]:
    """
    验证目录中的文件是否与分类字典一致。
    
    Args:
        directory (Path): 要验证的目录路径
        
    Returns:
        Dict[str, List[str]]: 包含 'missing' 和 'extra' 文件列表
    """
    result = {"missing": [], "extra": []}
    
    if not directory.exists():
        return result
    
    directory_files = {file.name for file in directory.glob("*") if file.is_file()}
    
    # 获取分类字典中的所有文件
    expected_files = set()
    for info in FILE_CATEGORIES.values():
        expected_files.update(info["files"])
    
    # 检查缺失和多余的文件
    result["missing"] = list(expected_files - directory_files)
    result["extra"] = list(directory_files - expected_files)
    
    return result