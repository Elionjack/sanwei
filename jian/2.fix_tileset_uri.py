"""
修复 tileset.json 中的 uri 路径问题
将错误的 uri 如 "./Tile_-051_+050_L20_0000000.b3dm"
修正为正确的相对路径如 "Data/Tile_-051_+050/Tile_-051_+050_L20_0000000.b3dm"
"""
import json
import os
from pathlib import Path


def fix_tileset_json(tileset_path, output_path=None):
    """
    修复 tileset.json 中的 uri 路径

    Args:
        tileset_path: tileset.json 文件路径
        output_path: 修复后的输出路径，默认为覆盖原文件
    """
    tileset_path = Path(tileset_path)
    tileset_dir = tileset_path.parent

    # 1. 扫描所有 b3dm 文件，建立 filename -> 相对路径 的映射
    filename_to_path = {}
    data_dir = tileset_dir / "Data"

    if not data_dir.exists():
        print(f"错误: Data 目录不存在: {data_dir}")
        return False

    print("扫描 b3dm 文件...")
    b3dm_files = list(data_dir.rglob("*.b3dm"))
    print(f"共找到 {len(b3dm_files)} 个 b3dm 文件")

    for b3dm_file in b3dm_files:
        rel_path = b3dm_file.relative_to(tileset_dir)
        # 转换为正斜杠路径
        rel_path_str = str(rel_path).replace('\\', '/')
        filename_to_path[b3dm_file.name] = rel_path_str

    # 2. 递归遍历所有 tile，修复 uri
    fixed_count = [0]

    def fix_tiles(tiles):
        for tile in tiles:
            # 处理 content.uri
            if 'content' in tile and 'uri' in tile['content']:
                old_uri = tile['content']['uri']
                filename = os.path.basename(old_uri)

                if filename in filename_to_path:
                    new_uri = "./" + filename_to_path[filename]
                    if old_uri != new_uri:
                        tile['content']['uri'] = new_uri
                        fixed_count[0] += 1
                        print(f"  修复: {old_uri} -> {new_uri}")
                else:
                    print(f"  警告: 未找到文件 {filename}")

            # 处理 children
            if 'children' in tile:
                fix_tiles(tile['children'])

    # 3. 加载并修复 tileset.json
    print(f"\n加载 tileset.json...")
    with open(tileset_path, 'r', encoding='utf-8') as f:
        tileset = json.load(f)

    if 'root' in tileset:
        print("修复 uri 路径...")
        fix_tiles([tileset['root']])

    # 4. 保存
    if output_path is None:
        output_path = tileset_path
    else:
        output_path = Path(output_path)

    print(f"\n保存修复后的 tileset.json 到: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(tileset, f, indent=2, ensure_ascii=False)

    print(f"\n完成! 共修复 {fixed_count[0]} 个 uri")
    return True


if __name__ == "__main__":
    tileset_path = r"E:\learning\data\output\jian\tileset.json"

    fix_tileset_json(tileset_path)
