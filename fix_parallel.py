with open('app/llm/openai.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'Sequential vs Parallel: Sequence dependent tasks. Parallelize independent ones' in line:
        print(f"Found Parallel note on line {i+1}: {repr(line)}")
        lines[i] = (
            '            "- PARALLEL IS MANDATORY for multi-task queries: When user asks for 2+ independent things "\n'
            '            "(e.g. NDVI AND grounding, LULC AND caption), use ONE PARALLEL action -- NOT sequential steps.\\n"\n'
            '            "  PARALLEL example for NDVI+grounding: parallel_capabilities_json = "\n'
            '            \'[{\\"capability\\":\\"terramind_generate\\",\\"arguments\\":{\\"asset\\":\\"<id>\\",\\"modality\\":\\"RGB\\",\\"output_modalities\\":\\"NDVI\\",\\"include_png\\":true}},\'  "\n'
            '            \'{\\"capability\\":\\"ground_region\\",\\"arguments\\":{\\"asset\\":\\"<id>\\"}}]\'\\n"\n'
            '            "- Sequential ONLY when step B requires output from step A.\\n"\n'
        )
        print(f"Replaced with: {repr(lines[i])}")
        break

with open('app/llm/openai.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print("Done")
