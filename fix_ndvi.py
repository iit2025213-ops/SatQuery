with open('app/llm/openai.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and replace lines 598-599 (0-indexed: 597-598)
for i, line in enumerate(lines):
    if 'NOTE: NDVI requires multispectral bands' in line:
        print(f"Found NDVI note on line {i+1}: {repr(line)}")
        lines[i] = (
            '            "TerraMind CAN generate NDVI from ANY image including plain RGB PNG -- '
            'no multispectral bands required. '
            'Use terramind_generate with modality=RGB and output_modalities=NDVI and include_png=true.\\n"\n'
        )
        print(f"Replaced with: {repr(lines[i])}")
        break

with open('app/llm/openai.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print("Done")
