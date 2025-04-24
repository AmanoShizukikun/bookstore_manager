import sqlite3
import re
from typing import Optional, Tuple, List, Dict, Any


DB_NAME = "bookstore.db"
DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"

def connect_db() -> sqlite3.Connection:
    """建立並返回 SQLite 資料庫連線"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_db(conn: sqlite3.Connection) -> None:
    """檢查並建立資料表，插入初始資料"""
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sale'")
        if not cursor.fetchone():
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS member (
                    mid TEXT PRIMARY KEY,
                    mname TEXT NOT NULL,
                    mphone TEXT NOT NULL,
                    memail TEXT
                );

                CREATE TABLE IF NOT EXISTS book (
                    bid TEXT PRIMARY KEY,
                    btitle TEXT NOT NULL,
                    bprice INTEGER NOT NULL,
                    bstock INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sale (
                    sid INTEGER PRIMARY KEY AUTOINCREMENT,
                    sdate TEXT NOT NULL,
                    mid TEXT NOT NULL,
                    bid TEXT NOT NULL,
                    sqty INTEGER NOT NULL,
                    sdiscount INTEGER NOT NULL,
                    stotal INTEGER NOT NULL
                );

                INSERT INTO member VALUES ('M001', 'Alice', '0912-345678', 'alice@example.com');
                INSERT INTO member VALUES ('M002', 'Bob', '0923-456789', 'bob@example.com');
                INSERT INTO member VALUES ('M003', 'Cathy', '0934-567890', 'cathy@example.com');

                INSERT INTO book VALUES ('B001', 'Python Programming', 600, 50);
                INSERT INTO book VALUES ('B002', 'Data Science Basics', 800, 30);
                INSERT INTO book VALUES ('B003', 'Machine Learning Guide', 1200, 20);

                INSERT INTO sale (sdate, mid, bid, sqty, sdiscount, stotal) VALUES ('2024-01-15', 'M001', 'B001', 2, 100, 1100);
                INSERT INTO sale (sdate, mid, bid, sqty, sdiscount, stotal) VALUES ('2024-01-16', 'M002', 'B002', 1, 50, 750);
                INSERT INTO sale (sdate, mid, bid, sqty, sdiscount, stotal) VALUES ('2024-01-17', 'M001', 'B003', 3, 200, 3400);
                INSERT INTO sale (sdate, mid, bid, sqty, sdiscount, stotal) VALUES ('2024-01-18', 'M003', 'B001', 1, 0, 600);
            """)
            conn.commit()
    except sqlite3.Error as e:
        print(f"資料庫初始化錯誤：{e}")
        conn.rollback()

def validate_date(date: str) -> bool:
    """驗證日期格式是否為 YYYY-MM-DD"""
    return bool(re.match(DATE_PATTERN, date))

def check_member_exists(conn: sqlite3.Connection, mid: str) -> bool:
    """檢查會員編號是否存在"""
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM member WHERE mid = ?", (mid,))
    return cursor.fetchone() is not None

def check_book_exists(conn: sqlite3.Connection, bid: str) -> bool:
    """檢查書籍編號是否存在"""
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM book WHERE bid = ?", (bid,))
    return cursor.fetchone() is not None

def check_book_stock(conn: sqlite3.Connection, bid: str, qty: int) -> Tuple[bool, int]:
    """檢查書籍庫存是否足夠"""
    cursor = conn.cursor()
    cursor.execute("SELECT bstock FROM book WHERE bid = ?", (bid,))
    row = cursor.fetchone()
    if row and row['bstock'] >= qty:
        return True, row['bstock']
    return False, row['bstock'] if row else 0

def get_book_price(conn: sqlite3.Connection, bid: str) -> int:
    """取得書籍單價"""
    cursor = conn.cursor()
    cursor.execute("SELECT bprice FROM book WHERE bid = ?", (bid,))
    row = cursor.fetchone()
    return row['bprice'] if row else 0

def add_sale(conn: sqlite3.Connection) -> None:
    """新增銷售記錄"""
    cursor = conn.cursor()
    while True:
        sdate = input("請輸入銷售日期 (YYYY-MM-DD)：")
        if validate_date(sdate):
            break
        print("=> 錯誤：日期格式無效，請使用 YYYY-MM-DD 格式")
    mid = input("請輸入會員編號：")
    bid = input("請輸入書籍編號：")
    valid_ids = check_member_exists(conn, mid) and check_book_exists(conn, bid)
    sqty = None
    while sqty is None:
        try:
            sqty = int(input("請輸入購買數量："))
            if sqty <= 0:
                print("=> 錯誤：數量必須為正整數，請重新輸入")
                sqty = None
        except ValueError:
            print("=> 錯誤：數量或折扣必須為整數，請重新輸入")
    sdiscount = None
    while sdiscount is None:
        try:
            sdiscount = int(input("請輸入折扣金額："))
            if sdiscount < 0:
                print("=> 錯誤：折扣金額不能為負數，請重新輸入")
                sdiscount = None
        except ValueError:
            print("=> 錯誤：數量或折扣必須為整數，請重新輸入")
    if not valid_ids:
        print("=> 錯誤：會員編號或書籍編號無效")
        return
    stock_ok, current_stock = check_book_stock(conn, bid, sqty)
    if not stock_ok:
        print(f"=> 錯誤：書籍庫存不足 (現有庫存: {current_stock})")
        return
    bprice = get_book_price(conn, bid)
    stotal = bprice * sqty - sdiscount
    try:
        cursor.execute(
            "INSERT INTO sale (sdate, mid, bid, sqty, sdiscount, stotal) VALUES (?, ?, ?, ?, ?, ?)",
            (sdate, mid, bid, sqty, sdiscount, stotal)
        )
        cursor.execute(
            "UPDATE book SET bstock = bstock - ? WHERE bid = ?",
            (sqty, bid)
        )
        conn.commit()
        print(f"=> 銷售記錄已新增！(銷售總額: {stotal:,})")
    except sqlite3.Error as e:
        conn.rollback()
        print(f"=> 錯誤：{e}")

def print_sale_report(conn: sqlite3.Connection) -> None:
    """查詢並顯示所有銷售報表"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.sid, s.sdate, m.mname, b.btitle, b.bprice, s.sqty, s.sdiscount, s.stotal
        FROM sale s
        JOIN member m ON s.mid = m.mid
        JOIN book b ON s.bid = b.bid
        ORDER BY s.sid
    """)
    sales = cursor.fetchall()
    print("\n==================== 銷售報表 ====================")
    for i, sale in enumerate(sales, 1):
        print(f"銷售 #{i}")
        print(f"銷售編號: {sale['sid']}")
        print(f"銷售日期: {sale['sdate']}")
        print(f"會員姓名: {sale['mname']}")
        print(f"書籍標題: {sale['btitle']}")
        print("--------------------------------------------------")
        print("單價\t數量\t折扣\t小計")
        print("--------------------------------------------------")
        print(f"{sale['bprice']:,}\t{sale['sqty']}\t{sale['sdiscount']:,}\t{sale['stotal']:,}")
        print("--------------------------------------------------")
        print(f"銷售總額: {sale['stotal']:,}")
        print("==================================================")
        print()

def get_sales_list(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """取得銷售記錄列表"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.sid, s.sdate, m.mname
        FROM sale s
        JOIN member m ON s.mid = m.mid
        ORDER BY s.sid
    """)
    return [dict(row) for row in cursor.fetchall()]

def display_sales_list(sales: List[Dict[str, Any]]) -> None:
    """顯示銷售記錄列表"""
    print("\n======== 銷售記錄列表 ========")
    for i, sale in enumerate(sales, 1):
        print(f"{i}. 銷售編號: {sale['sid']} - 會員: {sale['mname']} - 日期: {sale['sdate']}")
    print("================================")

def update_sale(conn: sqlite3.Connection) -> None:
    """更新銷售記錄"""
    cursor = conn.cursor()
    sales = get_sales_list(conn)
    if not sales:
        print("=> 目前沒有銷售記錄")
        return
    display_sales_list(sales)
    while True:
        choice = input("請選擇要更新的銷售編號 (輸入數字或按 Enter 取消): ")
        if not choice:
            return
        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(sales):
                print("=> 錯誤：請輸入有效的數字")
                continue
            sid = sales[idx]['sid']
            cursor.execute("""
                SELECT s.*, b.bprice
                FROM sale s
                JOIN book b ON s.bid = b.bid
                WHERE s.sid = ?
            """, (sid,))
            sale = cursor.fetchone()
            while True:
                try:
                    new_discount = int(input("請輸入新的折扣金額："))
                    if new_discount < 0:
                        print("=> 錯誤：折扣金額不能為負數，請重新輸入")
                        continue
                    break
                except ValueError:
                    print("=> 錯誤：折扣金額必須為整數，請重新輸入")
            new_total = sale['bprice'] * sale['sqty'] - new_discount
            cursor.execute(
                "UPDATE sale SET sdiscount = ?, stotal = ? WHERE sid = ?",
                (new_discount, new_total, sid)
            )
            conn.commit()
            print(f"=> 銷售編號 {sid} 已更新！(銷售總額: {new_total:,})")
            break
        except ValueError:
            print("=> 錯誤：請輸入有效的數字")
        except sqlite3.Error as e:
            conn.rollback()
            print(f"=> 錯誤：{e}")
            break

def delete_sale(conn: sqlite3.Connection) -> None:
    """刪除銷售記錄"""
    cursor = conn.cursor()
    sales = get_sales_list(conn)
    if not sales:
        print("=> 目前沒有銷售記錄")
        return
    display_sales_list(sales)
    while True:
        choice = input("請選擇要刪除的銷售編號 (輸入數字或按 Enter 取消): ")
        if not choice:
            return
        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(sales):
                print("=> 錯誤：請輸入有效的數字")
                continue
            sid = sales[idx]['sid']
            cursor.execute("DELETE FROM sale WHERE sid = ?", (sid,))
            conn.commit()
            print(f"=> 銷售編號 {sid} 已刪除")
            break
        except ValueError:
            print("=> 錯誤：請輸入有效的數字")

def show_menu() -> str:
    """顯示選單並取得使用者選擇"""
    print("***************選單***************")
    print("1. 新增銷售記錄")
    print("2. 顯示銷售報表")
    print("3. 更新銷售記錄")
    print("4. 刪除銷售記錄")
    print("5. 離開")
    print("**********************************")
    return input("請選擇操作項目(Enter 離開)：")

def main() -> None:
    """程式主流程"""
    with connect_db() as conn:
        initialize_db(conn)
        while True:
            choice = show_menu()
            if not choice:
                break
            if choice == "1":
                add_sale(conn)
            elif choice == "2":
                print_sale_report(conn)
            elif choice == "3":
                update_sale(conn)
            elif choice == "4":
                delete_sale(conn)
            elif choice == "5":
                break
            else:
                print("=> 請輸入有效的選項（1-5）")

if __name__ == "__main__":
    main()