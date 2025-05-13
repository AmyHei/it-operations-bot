import re
text = "What's the status of my ticket INC0010001?"
pattern = re.compile(r'\b(?:INC|REQ|TASK|RITM)\d{5,}\b', re.IGNORECASE)
matches = []
for match in pattern.finditer(text):
    matches.append(match.group(0))
print(matches)  # 应输出 ['INC0010001']
