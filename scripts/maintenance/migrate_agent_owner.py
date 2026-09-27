# -*- coding: utf-8 -*-
"""agents.owner 归属迁移：INT(指向已删除的旧 users.id) -> VARCHAR(36)(dify_accounts.id)。

为什么必须一次做完：
    agents.owner 是 INT，存的是已删除的旧 users.id（本机实测 1/2/3），无法反查到账号；
    而登录 token 的身份是 dify_accounts.id（UUID）。查询侧 WHERE owner = %s 与写入侧共用
    同一个值，所以「只改身份来源」会让非管理员新建时往 INT 列写 UUID（报错或写成 0），
    「只改列类型」会让所有列表匹配不上而清空。列类型 + 回填 + 身份来源必须同一轮完成。

用法：
    python scripts/maintenance/migrate_agent_owner.py            # 只体检，不写库
    python scripts/maintenance/migrate_agent_owner.py --apply    # 执行迁移
    python scripts/maintenance/migrate_agent_owner.py --apply --backup

决策已定（2026-09）：owner 1/2/3 全部归给主账号。理由是归到主账号只会"多看到自己的东西"，
而标成无主在按 token 过滤后会让这些智能体从列表消失，属于数据看起来丢了。
主账号按"拥有最多 dify_apps 的 created_by"判定，判不出时退回 name='yutaiyin' 的账号 id。
"""
import argparse
import os
import sys

# 本文件在 scripts/maintenance/ 下，要退三级到仓库根再进 backend
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND = os.path.join(ROOT, 'backend')
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)


def pick_primary(cur):
    """主账号：拥有最多应用创建记录的 created_by；判不出再用 yutaiyin。"""
    cur.execute(r"SELECT created_by FROM dify_apps WHERE created_by IS NOT NULL AND created_by <> '' "
                r'GROUP BY created_by ORDER BY COUNT(1) DESC LIMIT 1')
    row = cur.fetchone()
    if row:
        return row['created_by'], '按 dify_apps.created_by 出现次数最多'
    cur.execute(r"SELECT id FROM dify_accounts WHERE name = 'yutaiyin' LIMIT 1")
    row = cur.fetchone()
    return (row['id'] if row else None), '退回 name=yutaiyin 的账号'


def column_type(cur):
    cur.execute(r"SELECT DATA_TYPE AS t FROM information_schema.columns WHERE table_schema = DATABASE() "
                r"AND table_name = 'agents' AND column_name = 'owner'")
    row = cur.fetchone()
    return row['t'].lower() if row else None


def report(cur, label):
    cur.execute(r'SELECT owner, COUNT(1) AS n FROM agents GROUP BY owner ORDER BY owner')
    print('  [%s] owner 分布 = %s' % (label, [(r['owner'], r['n']) for r in cur.fetchall()]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='真正写库；缺省只做体检')
    ap.add_argument('--backup', action='store_true', help='迁移前把 owner 现值打印留档')
    args = ap.parse_args()

    from config import get_db
    db = get_db()
    try:
        cur = db.cursor()
        dt = column_type(cur)
        primary, why = pick_primary(cur)
        print('当前 owner 列类型 = %s' % dt)
        print('目标主账号 = %s（依据：%s）' % (primary, why))
        if not primary:
            print('!! 找不到主账号，终止（不写库）')
            return 1
        report(cur, '迁移前')
        if args.backup:
            cur.execute('SELECT id, name, owner FROM agents ORDER BY id')
            for r in cur.fetchall():
                print('  BACKUP id=%s owner=%s name=%s' % (r['id'], r['owner'], r['name']))

        if dt == 'int':
            if not args.apply:
                print('DRY-RUN：将执行 ALTER owner -> VARCHAR(36)，并把 1/2/3 回填为 %s' % primary)
            else:
                # INT 转 VARCHAR 会把 1/2/3 变成 '1'/'2'/'3'，随后统一归到主账号
                cur.execute('ALTER TABLE agents MODIFY COLUMN owner VARCHAR(36) NOT NULL DEFAULT %s', (primary,))
                cur.execute('UPDATE agents SET owner = %s WHERE owner NOT IN (SELECT id FROM dify_accounts)', (primary,))
                db.commit()
                print('已迁移列类型并回填')
        elif dt == 'varchar':
            print('列已是 VARCHAR，跳过 ALTER')
            if args.apply:
                cur.execute('UPDATE agents SET owner = %s WHERE owner NOT IN (SELECT id FROM dify_accounts)', (primary,))
                db.commit()
        else:
            print('!! 未预期的列类型 %r，终止' % dt)
            return 1

        report(cur, '迁移后')
        # 自查：不应再有对不上账号的 owner
        cur.execute('SELECT COUNT(1) AS n FROM agents WHERE owner NOT IN (SELECT id FROM dify_accounts)')
        print('  仍无主的智能体数 = %s' % cur.fetchone()['n'])
        print('OK%s' % ('（已写库）' if args.apply else '（DRY-RUN，未写库）'))
        return 0
    except Exception as e:
        db.rollback()
        print('!! 失败已回滚: %r' % e)
        return 1
    finally:
        db.close()


if __name__ == '__main__':
    sys.exit(main())
