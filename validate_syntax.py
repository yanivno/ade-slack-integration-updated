#!/usr/bin/env python3
"""
Validates that function_app.py has correct syntax and can be loaded.
This simulates what Azure Functions runtime does.
"""
import sys
import ast

def validate_syntax(filepath):
    """Validate Python syntax without importing dependencies."""
    try:
        with open(filepath, 'r') as f:
            code = f.read()
        
        # Parse the AST to check syntax
        tree = ast.parse(code, filepath)
        
        # Find the app instance and decorators
        app_found = False
        functions_found = []
        
        for node in ast.walk(tree):
            # Look for: app = func.FunctionApp()
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == 'app':
                        app_found = True
            
            # Look for decorated functions
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        if isinstance(decorator.func, ast.Attribute):
                            if decorator.func.attr in ['timer_trigger', 'function_name']:
                                functions_found.append({
                                    'name': node.name,
                                    'decorator': decorator.func.attr,
                                    'line': node.lineno
                                })
        
        print("✅ Syntax validation passed")
        print(f"✅ Found app instance: {app_found}")
        print(f"✅ Found {len(functions_found)} decorated function(s):")
        for func in functions_found:
            print(f"   - {func['name']} (@{func['decorator']}) at line {func['line']}")
        
        return True
        
    except SyntaxError as e:
        print(f"❌ Syntax Error: {e}")
        print(f"   File: {e.filename}")
        print(f"   Line: {e.lineno}")
        print(f"   Text: {e.text}")
        return False
    except Exception as e:
        print(f"❌ Validation Error: {e}")
        return False

if __name__ == '__main__':
    filepath = 'function_app.py'
    success = validate_syntax(filepath)
    sys.exit(0 if success else 1)
