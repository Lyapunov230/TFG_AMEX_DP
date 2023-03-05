#!/usr/bin/env python
# coding: utf-8

# # TFG: AMEX Default Prediction

# [ https://www.kaggle.com/competitions/amex-default-prediction/overview ]
# 
# [comment]: <> (Whether out at a restaurant or buying tickets to a concert, modern life counts on the convenience of a credit card to make daily purchases. It saves us from carrying large amounts of cash and also can advance a full purchase that can be paid over time. How do card issuers know we’ll pay back what we charge? That’s a complex problem with many existing solutions—and even more potential improvements, to be explored in this competition.
# 
# Credit default prediction is central to managing risk in a consumer lending business. Credit default prediction allows lenders to optimize lending decisions, which leads to a better customer experience and sound business economics. Current models exist to help manage risk. But it's possible to create better models that can outperform those currently in use.
# 
# American Express is a globally integrated payments company. The largest payment card issuer in the world, they provide customers with access to products, insights, and experiences that enrich lives and build business success.
# 
# __The objective is to predict the probability that a customer does not pay back their credit card balance amount in the future based on their monthly customer profile__. You’ll apply your machine learning skills to predict credit default. Specifically, you will leverage an industrial scale data set to build a machine learning model that challenges the current model in production. Training, validation, and testing datasets include time-series behavioral data and anonymized customer profile information. You're free to explore any technique to create the most powerful model, from creating features to using the data in a more organic way within a model.)

# **El objetivo de este proyecto es predecir la probabilidad de que un cliente  no pague el importe de su tarjeta de crédito en el futuro basado en su perfil mensual**. La variable objetivo es binaria y se calcula observando una ventana de actuación de 18 meses tras el último extracto de la tarjeta de crédito, y si el cliente no paga el importe adeudado en los 120 días posteriores a la fecha de su último extracto se considera un evento de impago.
# 
# El conjunto de datos contiene características de perfil agregadas para cada cliente en cada fecha de extracto. Las características están anonimizadas y normalizadas, y se clasifican en las siguientes categorías generales:
# 
# - __D_*__ = Delinquency variables (variables de delincuencia)
# - __S_*__ = Spend variables (variables de gasto)
# - __P_*__ = Payment variables (variables de pago)
# - __B_*__ = Balance variables (variables de balance)
# - __R_*__ = Risk variables (variables de riesgo)
# 
# siendo las siguientes características categóricas:
# 
# `['B_30', 'B_38', 'D_114', 'D_116', 'D_117', 'D_120', 'D_126', 'D_63', 'D_64', 'D_66', 'D_68']`.
# 
# El objetivo es, por tanto, predecir para cada `customer_ID` la probabilidad de un futuro impago (`target = 1`)
# 
# - Note that the negative class has been subsampled for this dataset at 5%, and thus receives a 20x weighting in the scoring metric.
# 
# Disponemos de las siguientes bases de datos:
# 
# - __train_data.csv__ - datos de entrenamiento con múltiples fechas de extractos por `customer_ID`
# - __train_labels.csv__ - etiqueta objetivo (`target` label) para cada `customer_ID`
# - __test_data.csv__ - datos de prueba; su objetivo es predecir la etiqueta objetivo para cada `customer_ID`
# - __sample_submission.csv__ - un archivo de presentación de muestra en el formato correcto

# ## **Análisis descriptivo de los datos**

# Comenzamos, a continuación, con el análisis descriptivo. Para ello, importamos en primer lugar algunas librerías básicas.

# In[1]:


#conda install -c conda-forge imbalanced-learn


# In[1]:


import pandas as pd 
import matplotlib as mpl  
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import imblearn
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import StratifiedKFold 
from sklearn.preprocessing import OrdinalEncoder
from sklearn.preprocessing import OneHotEncoder
from sklearn.preprocessing import StandardScaler
import lightgbm as lgb


import warnings
warnings.filterwarnings('ignore')


# A la hora de cargar los datasets, como son tan grandes (16 GB entrenamiento, 30 GB test), vamos a tener problemas de memoria y no vamos a lograr cargarlos. En Kaggle un par de usuarios han preprocesado la base original y han subido 2 alternativas para evitar los problemas de memoria:
# 
# - La primera (https://www.kaggle.com/datasets/munumbutt/amexfeather) cambia el formato de los datos, dejando de lado el _csv_ y transformándolos al formato _feather_ (más información sobre ese formato aquí: https://arrow.apache.org/docs/python/feather.html). Básicamente lo que hace es comprimir los datos. El problema es que los datos ahora están en 16 bits, por lo que se pierde algo de información (_Every float16 number between 1 and 2 is a multiple of 1/1024. These numbers have only three digits behind the decimal point!_).
# 
# - La segunda (https://www.kaggle.com/competitions/amex-default-prediction/discussion/328514) emplea una técnica similar y emplea el formato _parquet_. Además, elimina un ruido artificial de [0,0.01] que hay presente en todas las "float type columns". Transforma, cuando es posible todos los datos de tipo _float_ en datos de tipo _int_. No entiendo muy bien lo del ruido, pero parece que las mejores propuestas de código empiezan eliminándolo.

# In[2]:


# Cargamos los datos
#datos_train = pd.read_csv("train_data.csv", sep = ',')
#datos_train_labels = pd.read_csv("train_labels.csv", sep = ',')

# Hacemos una copia de los datos para que las modificaciones que hagamos no afecten al dataset original
#datos_train_original = datos_train.copy() 
#datos_train_labels_original = datos_train_labels.copy() 


# In[3]:


#from google.colab import drive

#drive.mount('/content/drive')  


# In[4]:


get_ipython().run_line_magic('run', '"funciones_auxiliares.ipynb"')
import funciones_auxiliares 


# In[5]:


#pip install pyarrow


# Esta versión utiliza [este dataset](https://www.kaggle.com/competitions/amex-default-prediction/discussion/328514) (la segunda opción listada anteriormente), el cual no solo disminuye el tamaño de la base sino que también elimina el ruido artificial presente en los datos, sin pérdida de información. Además, convierte los NA en -1 y, según el autor, no debería influir en los modelos.
# 
# 
# ```
#  This helps to reverse -1 to NA by just simply x[x==-1] = np.nan
# ```
# 
# El csv con los labels no está pero entiendo que hay que usar el original. Además, se ventila la variable target, aunque la variable target de train del csv original coincide con la variable target de train_labels.csv, por lo que podemos hacer un merge y recuperarla. 
# 
# > Más información acerca del ruido: https://www.kaggle.com/code/raddar/the-data-has-random-uniform-noise-added
# 

# In[6]:


train = pd.read_parquet('C:/Users/Jose/Documents/UNIVERSIDAD/TFG/amex-default-prediction/parquet_ds_integer_dtypes/train.parquet')
#train = train.groupby('customer_ID').tail(1).set_index('customer_ID')
#train[train==-1] = np.nan # revert -1 to na encoding as in the original dataset
train


# In[7]:


# Dimensión de los datos (train)
print("Tenemos %d observaciones y %d variables." % (train.shape[0], train.shape[1]))


# Como la base es tan grande, tenemos problemas de memoria. Una opción es separar en 2 notebooks distintos train y test.

# In[8]:


print(f'Esas 5531451 no corresponden cada una a un cliente, sino que cada cliente tiene varias observaciones que hacen referencia a la fecha de transacción. En concreto, tenemos este número de clientes: {train["customer_ID"].nunique()}')


# In[9]:


#test = pd.read_feather('/content/drive/MyDrive/TFG/feather_ds/test_data.ftr').set_index('customer_ID')
#test


# In[10]:


# Dimensión de los datos (test)
#print("Tenemos %d observaciones y %d variables." % (test.shape[0], test.shape[1]))


# In[9]:


train.describe()


# In[10]:


train.info(max_cols = 200, show_counts=True)


# In[11]:


print('Número de datos faltantes (missings):\n')
train.isnull().sum()


# Tenemos una variable de tipo fecha, otra tipo char (estas serían las 2 tipo objects, la fecha, `S_2` y los `customer_id`), 93 de tipo float, 86 de tipo integer 8bits y 9 16bits. A su vez, observamos que hay datos faltantes en algunas columnas, por lo que tendremos que abordarlos más adelante.

# In[13]:


#train_labels.csv - target label for each customer_ID (qué hago con esto?)

train_labels = pd.read_csv('train_labels.csv', low_memory=False)
train_labels


# In[14]:


#unimos train y labels usando el customer_ID
train_raw = train.merge(train_labels, left_on='customer_ID', right_on='customer_ID')
train_raw


# Veamos cómo se distribuye la variable `target` en el conjunto de entrenamiento

# In[15]:


target = train_raw.target.value_counts(normalize=False)
target.rename(index={1:'Default',0:'Paid'},inplace=True)
target


# In[16]:


target = train_raw.target.value_counts(normalize=True)
target.rename(index={1:'Default',0:'Paid'},inplace=True)
target


# In[17]:


import plotly.express as px
px.pie(target.index, values = target, names = target.index,  title='Target distribution') 


# De los 458913 `customer_ID`, 340085 (75,1 %) tienen `label` 0 (buen cliente, no *default*) y 118828 (24,9 %)  tienen `label` 1 (mal cliente, *default*). Los datos están desbalanceados.
# 
# Por la información previa proporcionada por AMEX sabemos que: 
# 
# "*The good customers have been subsampled by a factor of 20; this means that in reality there are 6.8 million good customers. 98 % of the customers are good; 2 % are bad*".

# Veamos también cuántos extractos de las tarjetas de crédito hay para cada cliente. Observamos que el 84.1% de los clientes tienen 13 extractos, mientras que el 15.9% tienen entre 1 y 12.

# In[18]:


train_ccs = train_raw.customer_ID.value_counts().value_counts().sort_index(ascending=False).rename('Extractos de la tarjeta de crédito por cliente')
px.pie(train_ccs, values = train_ccs, names = train_ccs.index, title = 'Extractos de la tarjeta de crédito por cliente')


# Acto seguido, sería interesante ver cómo se distribuyen los clientes en la línea temporal; es decir, cuándo se realizaron extractos bancarios, cuántos se realizaron y, lo más importante, cuánto tiempo mantuvieron activa su cuenta los clientes.

# In[20]:


#Quiero crear un gráfico con toda la línea temporal y que en el eje y esté el recuento del total de 
#extractos por día y en el eje x la línea temporal

#ERROR

#tmp = train_raw.S_2.groupby(train.customer_ID)
#fig = px.histogram(tmp, x="S_2")
#fig.show()
#del tmp


# Veamos cuánto permanecen los clientes en el banco en los datos de entrenamiento

# In[19]:


permanencia = train_raw.groupby(['customer_ID','target']).size().reset_index().rename(columns={0:'Permanencia'})
permanencia.head()


# In[25]:


fig = px.histogram(permanencia, x="Permanencia", barmode = 'group', color="target", title='Permanencia de los clientes en el banco según el target', nbins=20)
fig.show()


# In[21]:


fig, ax = plt.subplots(1,1, figsize=(15,5))
sns.histplot(x='Permanencia', data=permanencia, hue='target', stat='percent', multiple="dodge", bins=np.arange(0,14), ax=ax)
ax.bar_label(ax.containers[0], fmt='%.f%%')
ax.bar_label(ax.containers[1], fmt='%.f%%')
plt.show()


# El gráfico anterior muestra cuánto tiempo permanecen los clientes en el banco.  A partir de este gráfico es difícil ver cómo se distribuyen los objetivos de los clientes restantes, así que vamos a ampliarlo.

# In[22]:


fig, ax = plt.subplots(1,1, figsize=(15,5))
sns.histplot(x='Permanencia', data=permanencia, hue='target', stat='percent', multiple="dodge", bins=np.arange(0,14), ax=ax)
ax.bar_label(ax.containers[0], fmt='%.2f%%')
ax.bar_label(ax.containers[1], fmt='%.2f%%')
ax.set_xlim(0,12)
ax.set_ylim(0,1)
plt.show()


# Observamos que los clientes que están menos de un año en el banco son más propensos a la irse y no saldar su deuda. Esta información puede ser relevante en el futuro.

# ## TIPOS DE VARIABLES

# A continuación, vamos a agrupar las variables según su tipo. 
# 
# Recordemos, en primer lugar, que las siguientes variables eran categóricas:
# 
# `['B_30', 'B_38', 'D_114', 'D_116', 'D_117', 'D_120', 'D_126', 'D_63', 'D_64', 'D_66', 'D_68']`
# 
# Y `[S_2]` es una variable temporal.

# In[29]:


train_raw['S_2'] = pd.to_datetime(train_raw['S_2'])

print(f'La línea temporal de los datos de entrenamiento va desde {train_raw["S_2"].min()} hasta {train_raw["S_2"].max()}.')


# In[30]:


categorical_features = ['B_30', 'B_38', 'D_63', 'D_64', 'D_66', 'D_68', 'D_114', 'D_116', 'D_117', 'D_120', 'D_126']
train_raw[categorical_features] = train_raw[categorical_features].astype("category")
train_raw[categorical_features].dtypes


# In[31]:


#Veamos si tenemos datos faltantes en las variables categóricas
train_raw[categorical_features].isna().sum().div(len(train_raw)).sort_values(ascending=False)


# In[32]:


features = train.drop(['customer_ID', 'S_2'], axis = 1).columns.to_list()
numerical_features = [col for col in features if col not in categorical_features]
numerical_features


# In[33]:


train_raw[numerical_features].dtypes


# ### DISTRIBUCIÓN DE LAS VARIABLES

# Vamos a ver ahora cómo se distribuyen las variables, ya que podría sernos de utilidad en el futuro para agruparlas o calcular algunas características.
# 
# Vamos a calcularlas por grupos:
# 
# - __D_*__ = Delinquency variables (variables de delincuencia)
# - __S_*__ = Spend variables (variables de gasto)
# - __P_*__ = Payment variables (variables de pago)
# - __B_*__ = Balance variables (variables de balance)
# - __R_*__ = Risk variables (variables de riesgo)
# - __Variables discretas__

# In[34]:


#DISCRETAS

from plotly.subplots import make_subplots
import plotly.graph_objects as go

plt.figure(figsize=(16, 16))
for i, f in enumerate(categorical_features):
    plt.subplot(4, 3, i+1)
    temp = pd.DataFrame(train[f][train_raw.target == 0].value_counts(dropna=False, normalize=True).sort_index().rename('count'))
    temp.index.name = 'value'
    temp.reset_index(inplace=True)
    plt.bar(temp.index, temp['count'], alpha=0.5, label='target=0')
    temp = pd.DataFrame(train[f][train_raw.target == 1].value_counts(dropna=False, normalize=True).sort_index().rename('count'))
    temp.index.name = 'value'
    temp.reset_index(inplace=True)
    plt.bar(temp.index, temp['count'], alpha=0.5, label='target=1')
    plt.xlabel(f)
    plt.ylabel('frequency')
    plt.legend()
    plt.xticks(temp.index, temp.value)
plt.suptitle('Categorical features', fontsize=20, y=0.93)
plt.show()
del temp


# Observamos que como mucho las características presentan 8 categorías distintas, por lo que podríamos usar one-hot encoder. Además, la variable target no se distribuye de manera similar entre las variables, por lo que todas aportan algo de información sobre ella, ninguna es prescindible a priori.

# In[49]:


#DELINQUENCY

cols=[col for col in train_raw.columns if (col.startswith(('D','T'))) & (col not in categorical_features[:-1])]
plot_df=train_raw[cols]
fig, ax = plt.subplots(18,5, figsize=(16,54))
fig.suptitle('Distribution of Delinquency Variables',fontsize=16)
row=0
col=[0,1,2,3,4]*18
for i, column in enumerate(plot_df.columns[:-1]):
    if (i!=0)&(i%5==0):
        row+=1
    sns.kdeplot(x=column, hue= train_raw.target, hue_order=[1,0], 
                label=['Default','Paid'], data=plot_df, 
                fill=True, linewidth=2, legend=False, ax=ax[row,col[i]])
    ax[row,col[i]].tick_params(left=False,bottom=False)
    ax[row,col[i]].set(title='\n\n{}'.format(column), xlabel='', ylabel=('Density' if i%5==0 else ''))
for i in range(2,5):
    ax[17,i].set_visible(False)
handles, _ = ax[0,0].get_legend_handles_labels() 
fig.legend(labels=['Default','Paid'], handles=reversed(handles), ncol=2, bbox_to_anchor=(0.18, 0.983))
sns.despine(bottom=True, trim=True)
plt.tight_layout(rect=[0, 0.2, 1, 0.99])

del plot_df


# In[51]:


#SPEND

cols=[col for col in train_raw.columns if (col.startswith(('S','T'))) & (col not in categorical_features[:-1])]
plot_df=train_raw[cols]
fig, ax = plt.subplots(5,5, figsize=(16,20))
fig.suptitle('Distribution of Delinquency Variables',fontsize=16)
row=0
col=[0,1,2,3,4]*5
for i, column in enumerate(plot_df.columns[:-1]):
    if (i!=0)&(i%5==0):
        row+=1
    sns.kdeplot(x=column, hue= train_raw.target, hue_order=[1,0], 
                label=['Default','Paid'], data=plot_df, 
                fill=True, linewidth=2, legend=False, ax=ax[row,col[i]])
    ax[row,col[i]].tick_params(left=False,bottom=False)
    ax[row,col[i]].set(title='\n\n{}'.format(column), xlabel='', ylabel=('Density' if i%5==0 else ''))
for i in range(1,5):
    ax[4,i].set_visible(False)
handles, _ = ax[0,0].get_legend_handles_labels() 
fig.legend(labels=['Default','Paid'], handles=reversed(handles), ncol=2, bbox_to_anchor=(0.18, 0.985))
sns.despine(bottom=True, trim=True)
plt.tight_layout(rect=[0, 0.2, 1, 0.99])

del plot_df


# In[52]:


#PAYMENT

cols=[col for col in train_raw.columns if (col.startswith(('P','T'))) & (col not in categorical_features[:-1])]
plot_df=train_raw[cols]
fig, ax = plt.subplots(1,3, figsize=(16,5))
fig.suptitle('Distribution of Delinquency Variables',fontsize=16)
row=0
col=[0,1,2,3,4]*5
for i, column in enumerate(plot_df.columns[:-1]):
    if (i!=0)&(i%5==0):
        row+=1
    sns.kdeplot(x=column, hue= train_raw.target, hue_order=[1,0], 
                label=['Default','Paid'], data=plot_df, 
                fill=True, linewidth=2, legend=False, ax=ax[row,col[i]])
    ax[row,col[i]].tick_params(left=False,bottom=False)
    ax[row,col[i]].set(title='\n\n{}'.format(column), xlabel='', ylabel=('Density' if i%5==0 else ''))
for i in range(1,5):
    ax[4,i].set_visible(False)
handles, _ = ax[0,0].get_legend_handles_labels() 
fig.legend(labels=['Default','Paid'], handles=reversed(handles), ncol=2, bbox_to_anchor=(0.18, 1))
sns.despine(bottom=True, trim=True)
plt.tight_layout(rect=[0, 0.2, 1, 0.99])

del plot_df


# In[ ]:


#BALANCE


# In[ ]:


#RISK


# ## **MISSINGS**

# Veamos a continuación el número de datos faltantes en cada variable.

# In[35]:


# Veamos la cantidad y porcentaje de datos faltantes tenemos en cada variable
pd_series_null_columns = train_raw.isnull().sum().sort_values(ascending=False)
pd_series_null_rows = train_raw.isnull().sum(axis=1).sort_values(ascending=False)


pd_null_columnas = pd.DataFrame(pd_series_null_columns, columns=['nulos_columnas'])     
pd_null_filas = pd.DataFrame(pd_series_null_rows, columns=['nulos_filas'])  
pd_null_filas['target'] = train_raw['target'].copy()
pd_null_columnas['porcentaje_columnas'] = pd_null_columnas['nulos_columnas']/train_raw.shape[0]
pd_null_filas['porcentaje_filas']= pd_null_filas['nulos_filas']/train_raw.shape[1]

pd_null_columnas


# In[36]:


#Código sacado del notebook: https://www.kaggle.com/code/datark1/american-express-eda/notebook#-3.1-Missing-data-

tmp = train_raw.isna().sum().div(len(train_raw)).mul(100).sort_values(ascending=False)

plt.style.use('Solarize_Light2')
fig, ax = plt.subplots(2,1, figsize=(25,10))
sns.barplot(x=tmp[:100].index, y=tmp[:100].values, ax=ax[0])
sns.barplot(x=tmp[100:].index, y=tmp[100:].values, ax=ax[1])
ax[0].set_ylabel("Percentage [%]"), ax[1].set_ylabel("Percentage [%]")
ax[0].tick_params(axis='x', rotation=90); ax[1].tick_params(axis='x', rotation=90)
plt.suptitle("Amount of missing data")
plt.tight_layout()
plt.show()


# In[33]:


#null=round((train_raw.isna().sum()/train_raw.shape[0]*100),2).sort_values(ascending=False).astype(str)+('%')
#null=null.to_frame().rename(columns={0:'Missing %'})
#null.head(30)


# Vemos que hay muchas variables con una cantidad de datos nulos considerablemente alta. A priori podríamos pensar en imputar los missings con la media o la mediana según corresponda, pero no con tantos valores faltantes no es buena idea (y lo desaconsejan en los notebooks que he ido leyendo en kaggle). Hay que buscar otras alternativas.

# Los algoritmos basados en árboles de decisión que a priori vamos a utilizar son capaces de trabajar y hacer predicciones con ellos (si acabamos empleando otros algoritmos o redes neuronales sí que tendremos que imputarlos). No obstante, hay algunas variables cuyo porcentaje de valores nulos es tan alto que vamos a eliminarlas. En particular, vamos a eliminar las variables que tengan más de un 80% de observaciones faltantes.

# In[37]:


threshold = 0.8
list_vars_not_null = list(pd_null_columnas[pd_null_columnas['porcentaje_columnas'] < threshold].index)
list_var_null = list(pd_null_columnas[pd_null_columnas['porcentaje_columnas'] > threshold].index)
train_data = train_raw.loc[:, list_vars_not_null]
train_data.shape


# In[38]:


list_var_null


# In[39]:


print('Hemos eliminado, por tanto, las sigientes variables: \n \n'
      ,  list_var_null)


# ## **CORRELACIONES**

# Veamos a continuaición la matriz de correlación. Si algunas variables están altamente correladas, podemos eliminarlas ya que aportan la misma información.

# In[40]:


# code adapted from: https://www.kaggle.com/code/kellibelcher/amex-default-prediction-eda-lgbm-baseline
def correl_matrix(initial_letter, variable_group, fig_size_1, fig_size_2):
  cols_to_show = [c for c in train_data.columns if (c.startswith(initial_letter))]
  corr = train_data[cols_to_show].corr()
  mask=np.triu(np.ones_like(corr))[1:,:-1]
  corr=corr.iloc[1:,:-1].copy()

  fig, ax = plt.subplots(figsize=(fig_size_1, fig_size_2))   
  sns.heatmap(corr, mask=mask, vmin=-1, vmax=1, center=0, annot=True, fmt='.2f', 
              cmap='coolwarm', annot_kws={'fontsize':10,'fontweight':'bold'}, cbar=False)
  ax.tick_params(left=False,bottom=False)
  ax.set_xticklabels(ax.get_xticklabels(), rotation=45, horizontalalignment='right',fontsize=12)
  ax.set_yticklabels(ax.get_yticklabels(), fontsize=12)
  plt.title('Correlations between ' + variable_group + ' variables', fontsize=16)
  plt.show()


# In[41]:


#Spend Variables
SPEND_COR = correl_matrix('S', 'Spend', 15, 15)
SPEND_COR


# In[42]:


def drop_correl(initial_letter):
    cols_to_show = [c for c in train_data.columns if (c.startswith(initial_letter))]
    corr = train_data[cols_to_show].corr()
# Select upper triangle of correlation matrix
    upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(np.bool))

# Find features with correlation greater than 0.95
    to_drop = [column for column in upper.columns if any(upper[column] > 0.90)]

# Drop features 
    train_data.drop(to_drop, axis=1, inplace=True)
    
    print(to_drop)
    
drop_correl('S')


# In[43]:


correl_matrix('D', 'Delinquency', 48, 48)


# In[44]:


drop_correl('D')


# In[45]:


correl_matrix('P', 'Payment', 7, 5)


# In[46]:


drop_correl('P')


# In[47]:


correl_matrix('B', 'Balance', 24, 22)


# In[48]:


drop_correl('B')


# In[49]:


correl_matrix('R', 'Risk', 24, 18)


# In[50]:


drop_correl('R')


# ## MÉTRICA (PROPORCIONADA POR AMEX)

# La métrica a emplear, __*M*__, es la media del coeficiente de Gini normalizado, __*G*__, y el ratio de incumplimiento (default) capturado al 4%, __*D*__:
# 
# __*M = 0.5 · (G + D)*__
# 
# La tasa de incumplimiento capturada al 4% es el porcentaje de incumplimientos (defaults) capturados dentro del 4% de las predicciones mejor clasificadas, y representa una estadística de sensibilidad/exhaustividad (Sensitivity/Recall).
# 
# Para ambas submétricas, __*G*__ y __*D*__, los valores de no incumplimiento reciben un peso de 20 para ajustar el submuestreo.

# In[51]:


def amex_metric(y_true: pd.DataFrame, y_pred: pd.DataFrame) -> float:

    def top_four_percent_captured(y_true: pd.DataFrame, y_pred: pd.DataFrame) -> float:
        df = (pd.concat([y_true, y_pred], axis='columns')
              .sort_values('prediction', ascending=False))
        df['weight'] = df['target'].apply(lambda x: 20 if x==0 else 1)
        four_pct_cutoff = int(0.04 * df['weight'].sum())
        df['weight_cumsum'] = df['weight'].cumsum()
        df_cutoff = df.loc[df['weight_cumsum'] <= four_pct_cutoff]
        return (df_cutoff['target'] == 1).sum() / (df['target'] == 1).sum()
        
    def weighted_gini(y_true: pd.DataFrame, y_pred: pd.DataFrame) -> float:
        df = (pd.concat([y_true, y_pred], axis='columns')
              .sort_values('prediction', ascending=False))
        df['weight'] = df['target'].apply(lambda x: 20 if x==0 else 1)
        df['random'] = (df['weight'] / df['weight'].sum()).cumsum()
        total_pos = (df['target'] * df['weight']).sum()
        df['cum_pos_found'] = (df['target'] * df['weight']).cumsum()
        df['lorentz'] = df['cum_pos_found'] / total_pos
        df['gini'] = (df['lorentz'] - df['random']) * df['weight']
        return df['gini'].sum()

    def normalized_weighted_gini(y_true: pd.DataFrame, y_pred: pd.DataFrame) -> float:
        y_true_pred = y_true.rename(columns={'target': 'prediction'})
        return weighted_gini(y_true, y_pred) / weighted_gini(y_true, y_true_pred)

    g = normalized_weighted_gini(y_true, y_pred)
    d = top_four_percent_captured(y_true, y_pred)

    return 0.5 * (g + d)


# ## CODIFICACIÓN Y ESTANDARIZACIÓN DE VARIABLES

# In[79]:


#list_var_cat, other = funciones_auxiliares.dame_variables_categoricas(dataset=train_data)
#train_data[list_var_cat] = train_data[list_var_cat].astype("category")
#list_var_continuous = list(train_data.select_dtypes('float').columns)
#train_data[list_var_continuous] = train_data[list_var_continuous].astype(float)
#train_data.dtypes


# In[53]:


test_data = pd.read_parquet('C:/Users/Jose/Documents/UNIVERSIDAD/TFG/amex-default-prediction/parquet_ds_integer_dtypes/test.parquet')
test_data


# In[55]:


test_data['S_2'] = pd.to_datetime(test_data['S_2'])


# Vamos a eliminar en test las variables que hemos eliminado del conjunto de entrenamiento.

# In[82]:


test_data.drop(['D_88','D_110','B_39','D_73','B_42','D_134','B_29','D_132','D_76','D_42','D_142','S_7', 'S_24',
               'D_62', 'D_118', 'D_103', 'D_143', 'D_139', 'D_137', 'D_136', 'D_135', 'D_74', 'D_75',
               'B_33', 'B_14', 'B_11', 'B_1', 'B_23'], axis=1)


# # MODELOS

# In[65]:


# In[ ]: Vamos a definir una función para que genere semillas aleatorias
import random  
import os
seed = 42
def seed_everything(seed):
    random.seed(seed)
    np.random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)


# Codifiquemos en primer lugar las variables categóricas. Como no sabemos realmente qué representa cada característica ni cómo está ordenada, no podemos asumir un orden entre los valores de las características; es decir, no podemos saber si 1 es menor que 3, porque no disponemos de información suficiente acerca de las características. Es por ello que, en un principio, utilizar `OrdinalEncoder`no parece buena idea, ya que no sabemos el orden. Por ello, nos decantamos por `OneHotEncoder`.

# In[84]:


enc = LabelEncoder()
for i in categorical_features:
    train_data[i] = enc.fit_transform(train_data[i])
    test_data[i] = enc.fit_transform(test_data[i])

#enc = OneHotEncoder() #Llamamos al modelo
#enc.fit(train_data[categorical_features]) # Ajustamos
#train_data[categorical_features] = enc.transform(train_data[categorical_features]) #Transformamos
#train_data[categorical_features] = train_data[categorical_features].astype(int)


# In[85]:


datos2 = train_data.copy()

# Separamos variables dependientes e independiente

X_train = datos2.drop(['target'],axis=1)
y_train = datos2['target']

train_id = X_train['customer_ID']
X_train = X_train.drop(columns = ['customer_ID', 'S_2'])
test_id = test_data['customer_ID']
X_test = test_data.drop(columns = ['customer_ID', 'S_2'])


# ### Escalado y normalización de los datos. Remuestreo de los datos para equilibrar las clases.

# In[ ]:


from sklearn import preprocessing

# Escalamos (con los datos de train)
scaler = preprocessing.StandardScaler().fit(X_train)

X_train_scaled = pd.DataFrame(scaler.transform(X_train), columns = X_train.columns, index = X_train.index)
X_test_scaled = pd.DataFrame(scaler.transform(X_test), columns = X_test.columns, index = X_test.index)


# In[ ]:


y_train.nunique()


# In[ ]:


y_train.isnull().sum()


# In[ ]:


from imblearn.under_sampling import RandomUnderSampler

under_sampler = RandomUnderSampler(random_state=seed)
X_train_res, y_train_res = under_sampler.fit_resample(X_train_scaled, y_train)


# In[ ]:

#lgbm = LGBMClassifier(n_estimators=1000, random_state=seed, n_jobs=-1, class_weight='balanced')
#lgbm.fit(X_train_res, y_train_res)
#y_pred = lgbm.predict_proba(X_test_scaled)[:,1]
#y_pred




