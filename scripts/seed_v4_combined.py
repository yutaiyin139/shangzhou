# -*- coding: utf-8 -*-
"""
种子脚本 v4 合并版：根据 模型.docx 5 张图片精确提取的全部 98 个供应商
图片1: 20个 LLM 供应商
图片2: 20个 LLM/Embedding 供应商
图片3: 20个 LLM/Embedding 供应商
图片4: 20个 Embedding/Rerank 供应商
图片5: 18个 TTS/STT/LLM 供应商
总计: 98 个唯一供应商
"""
import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from config import get_db

# 从 seed_part1.py 和 seed_part2.py 导入
import importlib.util
spec1 = importlib.util.spec_from_file_location("seed_part1", os.path.join(os.path.dirname(__file__), 'seed_part1.py'))
m1 = importlib.util.module_from_spec(spec1)
spec1.loader.exec_module(m1)
P1 = m1.P

spec2 = importlib.util.spec_from_file_location("seed_part2", os.path.join(os.path.dirname(__file__), 'seed_part2.py'))
m2 = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(m2)
P2 = m2.P

P = P1 + P2

def main():
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("DELETE FROM model_provider_configs")
        cur.execute("DELETE FROM model_definitions")
        db.commit()
        print("[清理] 已删除旧供应商数据")

        inserted = 0
        for p in P:
            try:
                n, l, d, i, c, t, u, h = p
                cur.execute("""
                    INSERT INTO model_provider_configs
                    (provider_name, provider_label, description, icon, icon_background,
                     credential_type, default_base_url, supported_model_types,
                     help_url, help_text, is_built_in, status, install_count)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1, 1, 0)
                """, (n, l, d, i, c, "api_key", u, json.dumps(t, ensure_ascii=False), h, ""))
                # 插入默认模型
                for mt in t:
                    if mt == "llm":
                        cur.execute("""INSERT INTO model_definitions (provider_name, model_name, model_label, model_type, context_size, max_output_tokens, supports_vision, supports_function_calling, supports_streaming, status) VALUES (%s, %s, %s, 'llm', 4096, 2048, 0, 0, 1, 1)""", (n, "default", f"{l} Default"))
                    elif mt == "embedding":
                        cur.execute("""INSERT INTO model_definitions (provider_name, model_name, model_label, model_type, context_size, status) VALUES (%s, %s, %s, 'embedding', 8191, 1)""", (n, "default-embedding", f"{l} Embedding"))
                    elif mt == "rerank":
                        cur.execute("""INSERT INTO model_definitions (provider_name, model_name, model_label, model_type, status) VALUES (%s, %s, %s, 'rerank', 1)""", (n, "default-rerank", f"{l} Rerank"))
                    elif mt == "tts":
                        cur.execute("""INSERT INTO model_definitions (provider_name, model_name, model_label, model_type, status) VALUES (%s, %s, %s, 'tts', 1)""", (n, "default-tts", f"{l} TTS"))
                    elif mt == "stt":
                        cur.execute("""INSERT INTO model_definitions (provider_name, model_name, model_label, model_type, status) VALUES (%s, %s, %s, 'stt', 1)""", (n, "default-stt", f"{l} STT"))
                inserted += 1
            except Exception as e:
                print(f"[警告] 插入 {p[0]} 失败: {e}")

        db.commit()
        print(f"[完成] 成功插入 {inserted} 个供应商")
    finally:
        db.close()

if __name__ == "__main__":
    main()
