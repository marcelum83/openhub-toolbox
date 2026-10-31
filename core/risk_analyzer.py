import ast
import os

class RiskAnalyzer:
    """
    Statically analyzes Python code for potential security risks.
    """
    
    DANGEROUS_IMPORTS = {
        'os', 'subprocess', 'shutil', 'socket', 'pickle', 'requests', 'urllib',
        'http', 'pynput', 'pyautogui'
    }
    
    DANGEROUS_FUNCTIONS = {
        'eval', 'exec', 'open', 'remove', 'rmdir', 'system', 'popen', 'call'
    }

    def __init__(self):
        self.risk_points = 0
        self.findings = []

    def analyze(self, code):
        """
        Scans code and returns a risk report.
        """
        self.risk_points = 0
        self.findings = []
        
        try:
            tree = ast.parse(code)
        except Exception as e:
            return {"score": 10, "status": "Error", "reason": f"Syntax Error: {e}"}

        for node in ast.walk(tree):
            # Check Imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in self.DANGEROUS_IMPORTS:
                        self._add_finding("Import", alias.name, 2)
            
            elif isinstance(node, ast.ImportFrom):
                if node.module in self.DANGEROUS_IMPORTS:
                    self._add_finding("ImportFrom", node.module, 2)

            # Check Function Calls
            elif isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr
                
                if func_name in self.DANGEROUS_FUNCTIONS:
                    self._add_finding("Function", func_name, 3)

        # Categorize
        status = "Safe"
        if self.risk_points > 5: status = "Caution"
        if self.risk_points > 10: status = "High Risk"
        if self.risk_points > 20: status = "Dangerous"

        return {
            "score": self.risk_points,
            "status": status,
            "findings": self.findings
        }

    def _add_finding(self, category, item, points):
        self.risk_points += points
        self.findings.append(f"{category}: {item} (+{points})")

def get_risk_report(code):
    analyzer = RiskAnalyzer()
    return analyzer.analyze(code)
