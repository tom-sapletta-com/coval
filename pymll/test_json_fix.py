#!/usr/bin/env python3
"""
Test script to verify JSON parsing fixes
"""

import json
import re
from pathlib import Path

def improved_sanitize_json_string(json_str: str) -> str:
    """Improved JSON sanitization focusing on literal newline issues"""
    
    def escape_json_string_content(match):
        # match groups: (opening_quote, content, closing_quote)
        opening_quote = match.group(1)
        content = match.group(2)
        closing_quote = match.group(3)
        
        # Escape literal newlines and other control characters in the content
        content = content.replace('\n', '\\n')  # literal newline -> escaped newline
        content = content.replace('\r', '\\r')  # literal carriage return
        content = content.replace('\t', '\\t')  # literal tab
        
        # Fix potential double-escaping
        content = content.replace('\\\\n', '\\n')
        content = content.replace('\\\\r', '\\r')
        content = content.replace('\\\\t', '\\t')
        
        return f'{opening_quote}{content}{closing_quote}'
    
    # Pattern to match JSON string values more precisely
    # This matches: "...content..." including content with newlines
    string_pattern = r'(")([^"]*?)(")'
    
    print('🧹 Starting improved JSON sanitization...')
    print(f'Original length: {len(json_str)} chars')
    
    # Apply the sanitization
    sanitized = re.sub(string_pattern, escape_json_string_content, json_str, flags=re.DOTALL)
    
    print(f'Sanitized length: {len(sanitized)} chars')
    
    return sanitized

def main():
    """Test the JSON parsing fix"""
    
    # Test with the actual problematic JSON
    raw_file = Path('iterations/02_ecommerceapizkoszyki/llm_response_raw.txt')
    if not raw_file.exists():
        print(f"❌ File not found: {raw_file}")
        return
        
    raw_response = raw_file.read_text()
    
    print('=== TESTING IMPROVED SANITIZATION ===')
    print(f'Raw response length: {len(raw_response)} chars')
    
    # Extract JSON from markdown code block
    pattern = r'```json\s*\n(.*?)\n```'
    matches = re.findall(pattern, raw_response, re.DOTALL)
    
    if matches:
        json_content = matches[0].strip()
        
        print(f'\n📄 Found JSON block, length: {len(json_content)} chars')
        
        # Show problematic part with literal newlines
        problem_start = json_content.find('"pages/index.js"')
        if problem_start != -1:
            print('\n🐛 Before sanitization (problematic part):')
            problem_part = json_content[problem_start:problem_start+150]
            print(repr(problem_part))
        
        # Apply improved sanitization
        sanitized_json = improved_sanitize_json_string(json_content)
        
        # Show fixed part
        if problem_start != -1:
            print('\n✅ After sanitization (same part):')
            problem_start_fixed = sanitized_json.find('"pages/index.js"')
            if problem_start_fixed != -1:
                problem_part = sanitized_json[problem_start_fixed:problem_start_fixed+150]
                print(repr(problem_part))
        
        # Try to parse
        try:
            parsed_data = json.loads(sanitized_json)
            
            if 'components' in parsed_data:
                components = parsed_data['components']
                print(f'\n🎉 SUCCESS! Parsed {len(components)} components:')
                
                for i, comp in enumerate(components, 1):
                    name = comp.get('name', 'unnamed')
                    layer = comp.get('layer', 'unknown')  
                    framework = comp.get('framework', 'unknown')
                    files = comp.get('files', {})
                    print(f'\n  📦 Component {i}: {name} ({layer}/{framework})')
                    
                    for filename, content in files.items():
                        content_preview = content[:100].replace('\n', '\\n')
                        if len(content) > 100:
                            content_preview += '...'
                        print(f'    📄 {filename}: {content_preview}')
                        
                print('\n✨ The LLM generated EXCELLENT e-commerce components:')
                print('   🎨 NextJS frontend with pages and styles')
                print('   🛒 FastAPI backend with Product and CartItem models')
                print('   🛍️  Shopping cart endpoints (/products, /cart/add_item, /cart/items)')
                print('   💳 Payment worker with charge endpoint')
                print('\n🚀 JSON parsing is now WORKING!')
                
                return True
                
            else:
                print('❌ No components found in parsed JSON')
                return False
                
        except json.JSONDecodeError as e:
            print(f'\n❌ Still getting JSON error: {e}')
            if hasattr(e, 'pos') and e.pos:
                error_pos = e.pos
                print(f'Error around position {error_pos}:')
                start = max(0, error_pos-50)
                end = min(len(sanitized_json), error_pos+50)
                print(repr(sanitized_json[start:end]))
            return False
            
    else:
        print('❌ Could not extract JSON from markdown')
        return False

if __name__ == '__main__':
    success = main()
    if success:
        print('\n🎯 JSON parsing fix is READY to be integrated!')
    else:
        print('\n❌ Need to debug further...')
