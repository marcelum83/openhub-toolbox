"""
OpenHub Automated Python Code Sanitizer & Self-Healer
Fixes common LLM hallucinations (bad graphics imports, missing metrics/clock, missing OpenHubModule wrapper, App().run() conflicts).
"""
import re
import ast

class CodeSanitizer:
    @staticmethod
    def sanitize(code: str) -> str:
        if not code or not isinstance(code, str):
            return code

        lines = code.splitlines()
        cleaned_lines = []

        # 1. Fix Hallucinated Sub-Package Imports in kivy.graphics
        graphics_classes = []
        for line in lines:
            # Check for: from kivy.graphics.xxx import Yyy
            m = re.match(r'^\s*from\s+kivy\.graphics\.\w+\s+import\s+(.+)$', line)
            if m:
                items = [item.strip() for item in m.group(1).split(',')]
                graphics_classes.extend(items)
                continue
            cleaned_lines.append(line)

        code = "\n".join(cleaned_lines)

        # Inject consolidated from kivy.graphics import ... if any were stripped
        if graphics_classes:
            unique_gfx = sorted(list(set(graphics_classes)))
            import_stmt = f"from kivy.graphics import {', '.join(unique_gfx)}"
            code = f"{import_stmt}\n{code}"

        # 2. Ensure Essential Missing Imports
        needed_imports = []
        if ("dp(" in code or "sp(" in code) and "from kivy.metrics import" not in code:
            needed_imports.append("from kivy.metrics import dp, sp")

        if "Clock." in code and "from kivy.clock import Clock" not in code:
            needed_imports.append("from kivy.clock import Clock")

        if "random." in code and "import random" not in code and "from random import" not in code:
            needed_imports.append("import random")

        if "math." in code and "import math" not in code and "from math import" not in code:
            needed_imports.append("import math")

        if "BoxLayout" in code and "from kivy.uix.boxlayout import BoxLayout" not in code:
            needed_imports.append("from kivy.uix.boxlayout import BoxLayout")

        if "Label" in code and "from kivy.uix.label import Label" not in code:
            needed_imports.append("from kivy.uix.label import Label")

        if "Button" in code and "from kivy.uix.button import Button" not in code:
            needed_imports.append("from kivy.uix.button import Button")

        if needed_imports:
            code = "\n".join(needed_imports) + "\n" + code

        # 3. Strip standalone if __name__ == '__main__': ...App().run()
        # To avoid secondary event loops inside embedded ScreenManager
        code = re.sub(r'if\s+__name__\s*==\s*[\'"]__main__[\'"]\s*:\s*\n(\s+.*\n?)*', '', code)

        # 4. Check for OpenHubModule definition; if missing, auto-wrap
        if "class OpenHubModule" not in code:
            # Check if there is an App subclass or Widget subclass
            try:
                tree = ast.parse(code)
                widget_classes = []
                app_classes = []
                for node in tree.body:
                    if isinstance(node, ast.ClassDef):
                        for base in node.bases:
                            base_id = getattr(base, 'id', '')
                            if base_id in ('Widget', 'BoxLayout', 'GridLayout', 'FloatLayout', 'RelativeLayout', 'AnchorLayout', 'Scatter'):
                                widget_classes.append(node.name)
                            elif base_id in ('App', 'MDApp'):
                                app_classes.append(node.name)

                if widget_classes:
                    # Alias the primary widget class to OpenHubModule
                    primary_cls = widget_classes[-1]
                    code += f"\n\n# OpenHub Container Alias\nOpenHubModule = {primary_cls}\n"
                elif app_classes:
                    # Provide wrapper that instantiates the App and extracts build()
                    app_cls = app_classes[-1]
                    wrapper_code = f"""

# OpenHub Auto-Generated Module Wrapper
class OpenHubModule(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        try:
            app = {app_cls}()
            class _DummyRoot:
                width = 800
                height = 1200
            app.root = _DummyRoot()
            if hasattr(app, 'build'):
                root_w = app.build()
                if root_w:
                    self.add_widget(root_w)
        except Exception as e:
            self.add_widget(Label(text=f"App Load Error: {{e}}"))
"""
                    code += wrapper_code
            except Exception:
                pass

        return code
