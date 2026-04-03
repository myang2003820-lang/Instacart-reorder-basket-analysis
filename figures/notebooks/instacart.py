import itertools

import pandas as pd
import sqlite3
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)
pd.set_option("display.float_format", "{:.2f}".format)
#import sql
conn = sqlite3.connect("instacart.db")
files = {
    "orders": "C:\\Users\\cs\\Desktop\\instacart\\orders.csv",
    "order_products_prior": "C:\\Users\\cs\\Desktop\\instacart\\order_products__prior.csv",
    "order_products_train":"C:\\Users\\cs\\Desktop\\instacart\\order_products__train.csv" ,
    "products": "C:\\Users\\cs\\Desktop\\instacart\\products.csv",
    "aisles": "C:\\Users\\cs\\Desktop\\instacart\\aisles.csv",
    "departments": "C:\\Users\\cs\\Desktop\\instacart\\departments.csv"
}
for table_name, file_name in files.items():
    print(f"Loading {table_name}...")
    df = pd.read_csv(file_name)
    df.to_sql(table_name, conn, if_exists="replace", index=False)
print("Done.")
#data understanding
Tables= pd.read_sql("SELECT name FROM sqlite_master WHERE type ='table';", conn)
for table in Tables["name"]:
    COLUMNS = pd.read_sql(f"SELECT * FROM {table} LIMIT 1;",conn)
    cnt=int(pd.read_sql(f"SELECT COUNT(*) FROM {table};",conn).iloc[0,0])
    print(f"{table}")
    print(COLUMNS)
    print((cnt,COLUMNS.shape[1]))
#check null
check_keycols = {
    "orders" : ["order_id","user_id","eval_set","days_since_prior_order"],
    "order_products_prior": ["order_id","product_id"],
    "order_products_train": ["order_id","product_id"],
    "products" : ["aisle_id","product_id","department_id"]
}
for table,cols in check_keycols.items():
    print(f"Checking {table}...")
    for col in cols:
        null_cnt= pd.read_sql(f"SELECT SUM(CASE WHEN {col} IS NULL THEN 1 ELSE 0 END) FROM {table};",conn).iloc[0,0]
        print(f"{col}: {null_cnt}")
#check distinct
check_unqiue_keys={
    "orders" : ["order_id","user_id"],
    "products": ["product_id"],
    "aisles" : ["aisle_id"],
    "departments" : ["department_id"]
}
for table,keys in check_unqiue_keys.items():
    print(f"Checking {table}...")
    for key in keys:
        df=pd.read_sql(f"SELECT COUNT(*) AS total_rows, COUNT(DISTINCT {key}) AS distinct_cnt{key} FROM {table};",conn)
        print(df)

detail_check = {
    "order_products_prior": ["order_id","product_id"],
    "order_products_train": ["order_id","product_id"]
}
for table, cols in detail_check.items():
    print(f"Checking {table}...")
    col1,col2 = cols
    df=pd.read_sql(f"SELECT COUNT(*) AS total_cnt_row, COUNT(DISTINCT {col1}||'-'||{col2}) AS distinct_pair_cnt FROM {table};",conn)
    print(df)
###############################################################################################################
query = """
SELECT 
o.order_id, 
o.user_id, 
o.eval_set, 
o.order_number,
o.order_dow,
o.order_hour_of_day,
o.days_since_prior_order,
op.product_id,
op.add_to_cart_order,
op.reordered,
p.product_name,
p.product_id,
p.aisle_id,
p.department_id,
a.aisle,
d.department
FROM orders o
LEFT JOIN order_products_prior op ON o.order_id = op.order_id
LEFT JOIN products p ON op.product_id = p.product_id
LEFT JOIN aisles a ON p.aisle_id = a.aisle_id
LEFT JOIN departments d ON p.department_id = d.department_id
WHERE o.eval_set = 'prior';
"""
Data_table = pd.read_sql(query,conn)
############################Customer Behavior######################
#order distribution by day of weeks
days= """
SELECT order_dow AS days,
count(*) AS Frequency
FROM orders
GROUP BY order_dow
ORDER BY order_dow;
"""
hours = """
SELECT order_hour_of_day as hours,
count(*) AS Frequency
FROM orders
GROUP BY order_hour_of_day
ORDER BY order_hour_of_day;
"""
frequency_days = pd.read_sql(days,conn)
frequency_hours = pd.read_sql(hours,conn)
import matplotlib.pyplot as plt
plt.figure(figsize=(10,10))
plt.bar(frequency_days["days"],frequency_days["Frequency"])
plt.title("Order Distribution by day of week")
plt.ylabel("Frequency")
plt.xlabel("Days")
plt.show()
plt.figure(figsize=(10,10))
plt.bar(frequency_hours["hours"],frequency_hours["Frequency"])
plt.title("Order Distribution by hour of a Day")
plt.ylabel("Frequency")
plt.xlabel("Hours")
plt.show()
hot_departments= (Data_table.groupby("department")
                  .size()
                  .reset_index(name="puchased_cnt")
                  .sort_values("puchased_cnt", ascending=False)
                  .head(10))
hot_aisles=(Data_table.groupby("aisle")
            .size()
            .reset_index(name="puchased_cnt")
            .sort_values("puchased_cnt", ascending=False)
            .head(20))
print(hot_departments)
print(hot_aisles)
hot_reordered_aisle=(Data_table.groupby("aisle")["reordered"]
               .agg(["count","mean"])
               .reset_index()
               .rename(columns={"count":"purchased_cnt","mean":"reordered_rate"})
               .sort_values("reordered_rate", ascending=False)
               .head(10)
)
hot_reordered_department=(Data_table.groupby("department")["reordered"]
               .agg(["count","mean"])
               .reset_index()
               .rename(columns={"count":"purchased_cnt","mean":"reordered_rate"})
               .sort_values("reordered_rate", ascending=False)
               .head(10)
)
print("Top 1O reordered_rate aisle",hot_reordered_aisle)
print("Top 1O reordered_rate department",hot_reordered_department)
basket_size = (
    Data_table.groupby("order_id")
    .size()
    .reset_index(name="basket_size")
)

print(basket_size["basket_size"].describe())
plt.figure(figsize=(8,5))
plt.hist(basket_size["basket_size"], bins=30)
plt.title("Basket Size Distribution")
plt.xlabel("Number of Products per Order")
plt.ylabel("Number of Orders")
plt.show()
import itertools
from collections import Counter
combination_aisles=(Data_table.groupby("order_id")["aisle"]
.apply(lambda x : sorted(set(x)))
)
pair_counter = Counter()
for aisle in combination_aisles:
    for pair in itertools.combinations(aisle, 2):
        pair_counter[pair]+=1
top10_combinations_aisles = pair_counter.most_common(10)
top10_combinations_aisles = pd.DataFrame(
    top10_combinations_aisles,
    columns=["aisle_pair", "pair_count"]
)
top10_combinations_aisles[["aisle_1", "aisle_2"]] = pd.DataFrame(
    top10_combinations_aisles["aisle_pair"].tolist(),
    index=top10_combinations_aisles.index
)
top10_combinations_aisles = top10_combinations_aisles[
    ["aisle_1", "aisle_2", "pair_count"]
]
print(top10_combinations_aisles)
frequency_days.to_csv("frequency_days.csv", index=False)
frequency_hours.to_csv("frequency_hours.csv", index=False)
basket_dist_filtered = basket_size[basket_size["basket_size"] <= 40]
basket_dist_filtered.to_csv("basket_size_distribution_for_powerbi.csv", index=False)
hot_reordered_aisle.to_csv("top_reordered_aisles.csv", index=False)
top10_combinations_aisles.to_csv("top_copurchased_aisle_pairs.csv", index=False)
conn.close()