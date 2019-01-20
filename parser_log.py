import requests
import time
import sqlite3
import sys
conn = sqlite3.connect("logs.db")
cursor = conn.cursor()
cursor.execute("""drop TABLE category_goods""")
cursor.execute("""drop TABLE goods""")
cursor.execute("""drop TABLE users""")
cursor.execute("""drop TABLE visits""")
cursor.execute("""drop TABLE cart_history""")
cursor.execute("""drop TABLE purchases""")
# Создание таблицы категорий продуктов 
cursor.execute("""CREATE TABLE category_goods
                  (id integer primary key, name text)
               """)
# Создание таблицы товаров
cursor.execute("""CREATE TABLE goods
                  (id integer primary key autoincrement, name text, category_id integer,
                   FOREIGN KEY (category_id) REFERENCES category_goods (id))
               """)
#Создание таблицы пользователей
cursor.execute("""CREATE TABLE users
                  (id integer primary key autoincrement, ip text unique, country text)
               """)
#Создание таблицы посещений
cursor.execute("""CREATE TABLE visits
                  (id integer primary key autoincrement, datetime datetime, category_id integer,
                   good_id integer, user_id integer,
                   FOREIGN KEY (category_id) REFERENCES category_goods (id),
                   FOREIGN KEY (good_id) REFERENCES goods (id),
                   FOREIGN KEY (user_id) REFERENCES users (id))
               """)
#Создание таблицы истории помещений товаров в корзину
cursor.execute("""CREATE TABLE cart_history
                  (id integer primary key, datetime datetime,
                   good_id integer, user_id integer, amount integer,
                   FOREIGN KEY (good_id) REFERENCES goods (id),
                   FOREIGN KEY (user_id) REFERENCES users (id))
               """)
# Создание таблицы покупок
cursor.execute("""CREATE TABLE purchases
                  (id integer primary key autoincrement, datetime datetime, status BOOLEAN default false, cart_id integer,
                  FOREIGN KEY (cart_id) REFERENCES cart_history (id))
               """)
def GetCountryFromIP(ip):
    result = requests.get("http://ip-api.com/json/"+ip+"?fields=country")
    return result.text.split(':')[1].replace('"','').replace("}",'')
	
def GetUser(ip):
    cursor.execute("""select id from users where ip =?""",[(ip)])
    result = cursor.fetchall()
    if len(result) == 0:
            return None
    else:
        return result[0][0]
		
def GetGood(name,category_id):
    cursor.execute("""select id from goods where name =? and category_id = ?""",[(name),(category_id)])
    result = cursor.fetchall()
    if len(result) == 0:
            return None
    else:
        return result[0][0]
		
def GetCategoryGood(name):
    cursor.execute("""select id from category_goods where name =?""",[(name)])
    result = cursor.fetchall()
    if len(result) == 0:
            return None
    else:
        return result[0][0]
		

def AddUser(ip):
    user_id = GetUser(ip)
    if user_id == None:
        try:
            country = GetCountryFromIP(ip)
        except Exception:
            country = None
        cursor.execute("""insert into users (ip,country) values(?,?)""",[(ip),(country)])
    return  GetUser(ip)
path_logs = sys.argv[1] 	
f = open(path_logs)
list_visits_site = []
list_visits_category = []
list_visits_good= []
list_carts = []
list_pay = []
list_success_pay = []
for line in f:
    log = {}
    elems = line.split()
    sections = elems[7].split('/')
    sections.remove('https:')
    while '' in sections:
        sections.remove('')
    log['datetime'] = elems[2] + ' ' + elems[3]
    log['ip'] = elems[6]
    if len(sections) == 3:
        log['category'] = sections[1]
        log['good'] = sections[2]
        list_visits_good.append(log)
    elif len(sections) == 2:
        if 'cart?' in sections[1]:
            params = sections[1].split('&')
            log['amount'] = params[1].split('=')[1]
            log['cart_id'] = params[2].split('=')[1]
            list_carts.append(log)
        elif 'pay?' in sections[1]:
            params = sections[1].split('&')
            log['cart_id'] = params[1].split('=')[1]
            list_pay.append(log)
        elif 'success_pay_' in sections[1]:
            log['cart_id'] = sections[1].split('success_pay_')[1]
            log['status'] = True
            list_success_pay.append(log)
        else:
            log['category'] = sections[1]
            list_visits_category.append(log)
    else:
        list_visits_site.append(log)
print(list_visits_site)
print(list_visits_category)
print(list_visits_good)
print(list_carts)
print(list_pay)
print(list_success_pay)
  


for d in list_visits_site:
        user_id = AddUser(d['ip'])
        cursor.execute("""insert into visits (datetime,category_id,good_id,user_id) values(?,?,?,?)""",[(d['datetime']),(None),(None),(user_id)])
        time.sleep(0.5)

for d in list_visits_category:
    user_id = AddUser(d['ip'])
    category_id = GetCategoryGood(d['category'])
    if category_id == None:
        cursor.execute("""insert into category_goods (name) values(?)""",[(d['category'])])
        category_id = GetCategoryGood(d['category'])
    cursor.execute("""insert into visits (datetime,category_id,good_id,user_id) values(?,?,?,?)""",[(d['datetime']),(category_id),(None),(user_id)])
    
for d in list_visits_good:
    user_id = GetUser(d['ip'])
    category_id = GetCategoryGood(d['category'])
    if category_id == None:
        cursor.execute("""insert into category_goods (name) values(?)""",[(d['category'])])
        category_id = GetCategoryGood(d['category'])
    good_id =GetGood(d['good'],category_id)
    if good_id == None:
            cursor.execute("""insert into goods ( name, category_id) values(?,?)""",[(d['good']),(category_id)])
            good_id =GetGood(d['good'],category_id)
    cursor.execute("""insert into visits (datetime,category_id,good_id,user_id) values(?,?,?,?)""",[(d['datetime']),(category_id),(good_id),(user_id)])
    
for d in list_carts:
        user_id = GetUser(d['ip'])
        cursor.execute("""select id from cart_history where id = ? """,[(d['cart_id'])])
        if len(cursor.fetchall()) == 0:
            cursor.execute("""select good_id from visits  where user_id = ? and datetime < ? ORDER BY datetime desc""",[(user_id),(d['datetime'])])
            good_id = cursor.fetchall()[0][0]
            cursor.execute("""insert into cart_history (id,datetime,good_id,user_id,amount) values(?,?,?,?,?)""",[(d['cart_id']),(d['datetime']),(good_id),(user_id),(d['amount'])])

for d in list_pay:
    cursor.execute("""insert into purchases (datetime,cart_id) values(?,?)""",[(d['datetime']),(d['cart_id'])])

for d in list_success_pay:
    cursor.execute("""update purchases set status = true where cart_id = ?""",[(d['cart_id'])])


cursor.close()
conn.commit()
conn.close()
	