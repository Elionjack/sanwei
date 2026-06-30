import struct
import os
from pathlib import Path


class B3dmGenerator:
    def __init__(self):
        self.magic = b'b3dm'
        self.version = 1

    def wrap_glb(self, glb_path, output_path):
        if not os.path.exists(glb_path):
            raise FileNotFoundError(f"GLB file not found: {glb_path}")

        with open(glb_path, 'rb') as f:
            glb_data = f.read()

        glb_size = len(glb_data)

        feature_table_json = b''
        feature_table_binary = b''
        batch_table_json = b''
        batch_table_binary = b''

        ft_json_len = len(feature_table_json)
        ft_bin_len = len(feature_table_binary)
        bt_json_len = len(batch_table_json)
        bt_bin_len = len(batch_table_binary)

        header_size = 28
        total_size = header_size + ft_json_len + ft_bin_len + bt_json_len + bt_bin_len + glb_size

        b3dm_data = bytearray()
        b3dm_data.extend(self.magic)
        b3dm_data.extend(struct.pack('<I', self.version))
        b3dm_data.extend(struct.pack('<I', total_size))
        b3dm_data.extend(struct.pack('<I', ft_json_len))
        b3dm_data.extend(struct.pack('<I', ft_bin_len))
        b3dm_data.extend(struct.pack('<I', bt_json_len))
        b3dm_data.extend(struct.pack('<I', bt_bin_len))

        b3dm_data.extend(feature_table_json)
        b3dm_data.extend(feature_table_binary)
        b3dm_data.extend(batch_table_json)
        b3dm_data.extend(batch_table_binary)
        b3dm_data.extend(glb_data)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'wb') as f:
            f.write(b3dm_data)

        return True

    def batch_convert(self, glb_dir, output_dir):
        glb_path = Path(glb_dir)
        output_path = Path(output_dir)

        glb_files = list(glb_path.rglob("*.glb"))

        success_count = 0
        fail_count = 0

        for glb_file in glb_files:
            relative_path = glb_file.relative_to(glb_path)
            b3dm_path = output_path / relative_path.with_suffix(".b3dm")

            print(f"Converting {glb_file} -> {b3dm_path}")

            try:
                self.wrap_glb(str(glb_file), str(b3dm_path))
                success_count += 1
            except Exception as e:
                print(f"Error converting {glb_file}: {str(e)}")
                fail_count += 1

        print(f"\nB3DM conversion complete. Success: {success_count}, Fail: {fail_count}")
        return success_count, fail_count

    def add_batch_table(self, glb_path, output_path, batch_ids):
        if not os.path.exists(glb_path):
            raise FileNotFoundError(f"GLB file not found: {glb_path}")

        with open(glb_path, 'rb') as f:
            glb_data = f.read()

        import json
        feature_table_json = json.dumps({
            "BATCH_LENGTH": len(batch_ids)
        }).encode('utf-8')

        feature_table_binary = bytes()
        batch_table_json = json.dumps({
            "batchId": batch_ids
        }).encode('utf-8')

        ft_json_padded = self._pad_to_4_bytes(feature_table_json)
        ft_bin_padded = self._pad_to_4_bytes(feature_table_binary)
        bt_json_padded = self._pad_to_4_bytes(batch_table_json)

        ft_json_len = len(ft_json_padded)
        ft_bin_len = len(ft_bin_padded)
        bt_json_len = len(bt_json_padded)
        bt_bin_len = 0

        header_size = 28
        total_size = header_size + ft_json_len + ft_bin_len + bt_json_len + bt_bin_len + len(glb_data)

        b3dm_data = bytearray()
        b3dm_data.extend(self.magic)
        b3dm_data.extend(struct.pack('<I', self.version))
        b3dm_data.extend(struct.pack('<I', total_size))
        b3dm_data.extend(struct.pack('<I', ft_json_len))
        b3dm_data.extend(struct.pack('<I', ft_bin_len))
        b3dm_data.extend(struct.pack('<I', bt_json_len))
        b3dm_data.extend(struct.pack('<I', bt_bin_len))

        b3dm_data.extend(ft_json_padded)
        b3dm_data.extend(ft_bin_padded)
        b3dm_data.extend(bt_json_padded)
        b3dm_data.extend(glb_data)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'wb') as f:
            f.write(b3dm_data)

        return True

    def _pad_to_4_bytes(self, data):
        padding = (4 - len(data) % 4) % 4
        return data + b'\x00' * padding

    def verify_b3dm(self, b3dm_path):
        if not os.path.exists(b3dm_path):
            return False

        with open(b3dm_path, 'rb') as f:
            data = f.read()

        if len(data) < 28:
            return False

        magic = data[0:4]
        version = struct.unpack('<I', data[4:8])[0]

        if magic != self.magic or version != self.version:
            return False

        return True