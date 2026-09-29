import inspect
import re
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from app.main import app

route_param_issues = []
all_path_params = []

def extract_routes(route_list):
    routes = []
    for r in route_list:
        if hasattr(r, "routes"):
            routes.extend(extract_routes(r.routes))
        elif hasattr(r, "path") and hasattr(r, "endpoint"):
            routes.append(r)
    return routes

all_routes = extract_routes(app.routes)
for route in all_routes:
    path = route.path
    placeholders = re.findall(r'\{([a-zA-Z0-9_]+)\}', path)
    if not placeholders:
        continue
    sig = inspect.signature(route.endpoint)
    params = sig.parameters
    methods = list(getattr(route, 'methods', []))
    for placeholder in placeholders:
        if placeholder not in params:
            route_param_issues.append((path, placeholder, methods, list(params.keys())))
        else:
            p_obj = params[placeholder]
            all_path_params.append({
                'path': path,
                'methods': methods,
                'param_name': placeholder,
                'annotation': str(p_obj.annotation),
                'default': str(p_obj.default),
            })

print(f"Total routes inspected: {len(all_routes)}")
print(f"Total path parameter occurrences: {len(all_path_params)}")
print(f"Routes with undeclared path placeholders: {len(route_param_issues)}")
for path, placeholder, methods, params in route_param_issues:
    print(f"  Path: {path} [{methods}] -> Missing '{placeholder}' in signature! Declared: {params}")

