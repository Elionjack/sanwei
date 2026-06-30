from osgb23dtiles import osgb_to_b3dm_3dtiles
import os
import time
from pathlib import Path


def main():
    input_osgb_dir = r"E:\learning\data\1"
    output_3dtiles_dir = r"E:\learning\data\output\jian"

    input_path = Path(input_osgb_dir)
    output_path = Path(output_3dtiles_dir)

    if not input_path.exists():
        print(f"错误: 输入目录不存在: {input_osgb_dir}")
        return 1

    if not input_path.is_dir():
        print(f"错误: 输入路径不是目录: {input_osgb_dir}")
        return 1

    output_path.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("OSGB → 3D Tiles 转换器 (osgb23dtiles)")
    print("=" * 60)
    print(f"输入目录: {input_osgb_dir}")
    print(f"输出目录: {output_3dtiles_dir}")
    print("=" * 60)

    osg_bin_path = r"E:\learning\data\OpenSceneGraph-3.6.5-VC2022-64-2025-04\bin"
    osg_plugin_path = os.path.join(osg_bin_path, "osgPlugins-3.6.5")

    if os.path.exists(osg_plugin_path):
        os.environ["OSG_PLUGIN_PATH"] = osg_plugin_path
        os.environ["PATH"] = osg_bin_path + os.pathsep + os.environ["PATH"]
        print(f"\n已设置 OSG 插件路径: {osg_plugin_path}")
        print(f"已添加 OSG bin 到 PATH")
    else:
        print(f"\n警告: 未找到 OSG 插件目录: {osg_plugin_path}")
        print("可能导致 OSGB 文件读取失败")

    start_time = time.time()

    try:
        print("\n开始转换...")
        osgb_to_b3dm_3dtiles(input_osgb_dir, output_3dtiles_dir)

        end_time = time.time()
        elapsed_time = end_time - start_time

        hours = int(elapsed_time // 3600)
        minutes = int((elapsed_time % 3600) // 60)
        seconds = int(elapsed_time % 60)

        print("\n" + "=" * 60)
        print("转换完成！")
        print(f"耗时: {hours}小时 {minutes}分钟 {seconds}秒")
        print(f"输出目录: {output_3dtiles_dir}")
        print("=" * 60)

        tileset_path = output_path / "tileset.json"
        if tileset_path.exists():
            print(f"\n✓ tileset.json 已生成")

        tiles_dir = output_path / "tiles"
        if tiles_dir.exists():
            b3dm_count = len(list(tiles_dir.rglob("*.b3dm")))
            print(f"✓ B3DM 文件数量: {b3dm_count}")

        return 0

    except Exception as e:
        end_time = time.time()
        elapsed_time = end_time - start_time

        print(f"\n✗ 转换失败！")
        print(f"错误信息: {str(e)}")
        print(f"失败前耗时: {elapsed_time:.2f} 秒")
        print("=" * 60)

        import traceback
        traceback.print_exc()

        return 1


if __name__ == "__main__":
    exit(main())