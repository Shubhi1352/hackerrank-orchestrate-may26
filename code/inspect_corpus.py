import os
import sys

data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')

total_files = 0
for company in ['claude', 'hackerrank', 'visa']:
    company_dir = os.path.join(data_dir, company)
    if not os.path.exists(company_dir):
        print(f"MISSING: {company_dir}")
        continue
    files = os.listdir(company_dir)
    total_files += len(files)
    # Show first 5 files + extensions summary
    extensions = {}
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        extensions[ext] = extensions.get(ext, 0) + 1
    print(f"\n[{company.upper()}] — {len(files)} files")
    print(f"  Extensions: {extensions}")
    print(f"  Sample files: {files[:5]}")
    # Show size of first file
    if files:
        first = os.path.join(company_dir, files[0])
        size = os.path.getsize(first)
        with open(first, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(500)
        print(f"  First file size: {size} bytes")
        print(f"  First 200 chars: {repr(content[:200])}")

print(f"\nTotal files: {total_files}")