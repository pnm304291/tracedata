import pandas as pd
import psycopg2
from datetime import datetime

# ====== Cấu hình kết nối PostgreSQL ======
PG_CONFIG = {
    "host": "192.168.238.248",
    "port": 5432,
    "dbname": "MES_AUTOMATION",
    "user": "mai_user1",
    "password": "123456",
}

# ====== Tham số truy vấn ======
UNIT = "LASER MARKING"
LIKE_TEXT = "L1NCP16306-004B"   # tương đương LIKE '%L1NCP16306-004B%'
DAYS_BACK = 7

# Lưu ý: đổi schema/table/column cho đúng với PostgreSQL của bạn
# Ví dụ: schema = mes_automation, table = log_sp
SCHEMA = "dbo"
TABLE = "Log_SP"

# Tên cột giả định theo câu SQL của bạn:
# - unit
# - timestampinsert
# - datetime (hoặc DateTime)
# - jsondata
ORDER_COL = "datetime"  # nếu bên bạn tên là "DateTime" có chữ hoa, xem phần note phía dưới


def main():
    conn = psycopg2.connect(**PG_CONFIG)

    # Query 1: 7 ngày gần nhất
    sql_1 = f"""
        SELECT *
        FROM {SCHEMA}.{TABLE}
        WHERE unit = %(unit)s
          AND timestampinsert >= (NOW() - INTERVAL '%(days)s days')
        ORDER BY {ORDER_COL} DESC
    """

    # psycopg2 không cho parameterize bên trong INTERVAL kiểu '%(days)s days' theo cách trên ở mọi trường hợp,
    # nên cách an toàn là dựng INTERVAL bằng make_interval:
    sql_1 = f"""
        SELECT *
        FROM {SCHEMA}.{TABLE}
        WHERE unit = %(unit)s
          AND timestampinsert >= (NOW() - make_interval(days => %(days)s))
        ORDER BY {ORDER_COL} DESC
    """

    # Query 2: LIKE '%text%'
    sql_2 = f"""
        SELECT *
        FROM {SCHEMA}.{TABLE}
        WHERE jsondata::text LIKE %(pattern)s
        ORDER BY {ORDER_COL} DESC
    """

    df1 = pd.read_sql(sql_1, conn, params={"unit": UNIT, "days": DAYS_BACK})
    df2 = pd.read_sql(sql_2, conn, params={"pattern": f"%{LIKE_TEXT}%"})

    out_file = "log_sp_export.xlsx"
    with pd.ExcelWriter(out_file, engine="openpyxl") as writer:
        df1.to_excel(writer, index=False, sheet_name="laser_marking_last7days")
        df2.to_excel(writer, index=False, sheet_name="json_like_search")

    conn.close()
    print(f"Done. Exported to: {out_file}")
    print(f"Rows sheet1={len(df1)}, sheet2={len(df2)}")


if __name__ == "__main__":
    main()
    