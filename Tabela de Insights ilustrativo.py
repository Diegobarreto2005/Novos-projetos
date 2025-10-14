print("*" * 60)
msg = "Bem vindo a nossa loja"
print(msg.center(60))
print("*" * 60)
print("Temos esses produtos disponíveis:")

import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


conn = sqlite3.connect('exemplo.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS Produtos (
    id_venda INTEGER PRIMARY KEY AUTOINCREMENT,
    data_venda DATE,
    produto TEXT,
    categoria TEXT,
    valor_venda REAL
)
''')

novo_produto = [
    ('2023-01-01', 'Produto A', 'Eletrônicos', 1500.00),
    ('2023-01-05', 'Produto B', 'Roupas', 350.00),
    ('2023-02-10', 'Produto C', 'Eletrônicos', 1200.00),
    ('2023-03-15', 'Produto D', 'Livros', 200.00),
    ('2023-03-20', 'Produto E', 'Eletrônicos', 800.00),
    ('2023-04-02', 'Produto F', 'Roupas', 400.00),
    ('2023-05-05', 'Produto G', 'Livros', 150.00),
    ('2023-06-10', 'Produto H', 'Eletrônicos', 1000.00),
    ('2023-07-20', 'Produto I', 'Roupas', 600.00),
    ('2023-08-25', 'Produto J', 'Eletrônicos', 700.00),
    ('2023-09-30', 'Produto K', 'Livros', 300.00),
    ('2023-10-05', 'Produto L', 'Roupas', 450.00),
    ('2023-11-15', 'Produto M', 'Eletrônicos', 900.00),
    ('2023-12-20', 'Produto N', 'Livros', 250.00)
]

cursor.executemany(
    'INSERT INTO Produtos (data_venda, produto, categoria, valor_venda) VALUES (?, ?, ?, ?)',
    novo_produto
)
conn.commit()


cursor.execute("SELECT * FROM Produtos")
produtos = cursor.fetchall()


for p in produtos:
    print(p)


df_vendas = pd.read_sql_query("SELECT * FROM Produtos", conn)
conn.close()

print("*" * 60)
print("\nPrimeiras linhas do DataFrame:")
print(df_vendas.head())

print("\nResumo estatístico:")
print(df_vendas.describe())

print("\nContagem por categoria:")
print(df_vendas['categoria'].value_counts())


total_por_categoria = df_vendas.groupby('categoria')['valor_venda'].sum()
print("\nTotal vendido por categoria:")
print(total_por_categoria)


sns.set(style="whitegrid")


plt.figure(figsize=(8,5))
sns.barplot(x=total_por_categoria.index, y=total_por_categoria.values)
plt.title("Total vendido por categoria")
plt.ylabel("Valor total (R$)")
plt.xlabel("Categoria")
plt.show()


df_vendas['data_venda'] = pd.to_datetime(df_vendas['data_venda'])
df_vendas_sorted = df_vendas.sort_values('data_venda')

plt.figure(figsize=(10,5))
sns.lineplot(x='data_venda', y='valor_venda', data=df_vendas_sorted)
plt.title("Vendas ao longo do tempo")
plt.ylabel("Valor vendido (R$)")
plt.xlabel("Data")
plt.show()


print("\nInsights:")
print("- Categoria com maior faturamento:", total_por_categoria.idxmax())
print("- Tendência de vendas ao longo do ano pode ser observada no gráfico de linha.")