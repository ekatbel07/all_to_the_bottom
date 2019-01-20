import pandas as pd
from bokeh.plotting import curdoc, figure
from bokeh.sampledata.autompg import autompg_clean as df
from bokeh.palettes import Category20c
from bokeh.transform import cumsum
from bokeh.models import  CustomJS, ColumnDataSource
from bokeh.palettes import Spectral6
from bokeh.transform import factor_cmap
from bokeh.embed import components,json_item
from bokeh.resources import CDN
from bottle import route, run, template
from bokeh.models.widgets import Select, DatePicker, Div
from bokeh.models.sources import AjaxDataSource
from bokeh.layouts import widgetbox, layout
import json 
import sqlite3
from itertools import islice
from math import pi

# pip install bokeh
# pip install bottle

conn = sqlite3.connect("logs.db",check_same_thread=False)

# Посетители из какой страны совершают больше всего действий на сайте?
def Report1():

    cursor = conn.cursor()
    cursor.execute("""select u.country, count(*) from users u, visits v where u.id = v.user_id group by country order by 2 desc""")
    
    result = {}
    for i in cursor.fetchall():
        result[i[0]] = i[1]
    cursor.execute("""select u.country, count(*) from users u, cart_history c where u.id = c.user_id group by u.country order by 2 desc""")
    for i in cursor.fetchall():
        result[i[0]] += i[1]
    cursor.execute("""select u.country, count(*) from users u, cart_history c, purchases p where u.id = c.user_id and p.cart_id = c.id group by u.country order by 2 desc""")
    for i in cursor.fetchall():
        result[i[0]] += i[1]
    cursor.execute("""select country, count(*) from users group by country order by 2 desc""")
    for i in cursor.fetchall():
        result[i[0]] /= i[1]
    del result[None]
    n_items = list(islice(result.items(), 12))
    result = {}
    for i in n_items:
        result[i[0]] = i[1]
    return result
	
def GetTimesOfDay(time):
    if time >= "00:00:00" and  time < "05:00:00":
        return 'Ночь'
    elif time >= "05:00:00" and  time < "12:00:00":
        return 'Утро'
    elif time >= "12:00:00" and  time < "18:00:00":
        return 'День'
    elif time >= "18:00:00" and  time <= "23:59:59":
        return 'Вечер' #В какое время суток чаще всего просматривают определенную категорию товаров?
#с 00:00:00  по 05:00:00 - ночь
#с 05:00:00  по 12:00:00 - утро
#с 12:00:00  по 18:00:00 - день
#с 18:00:00  по 00:00:00 - вечер
def Report2(category_name):
    cursor1 = conn.cursor()
    cursor1.execute("""select id from category_goods where name = ?  """,[(category_name)])
    cursor1.execute("""select time(datetime) from visits where category_id = ?  """,[(cursor1.fetchall()[0][0])])
    result = {}
    for i in cursor1.fetchall():
        times = GetTimesOfDay(i[0])
        if times not in result:
            result[times] = 1
        else:
            result[times] += 1
        
    return result
	
#Сколько брошенных (не оплаченных) корзин имеется за определенный период?
def Report3(date_start,date_finish):
    cursor3=conn.cursor()
    cursor3.execute("""select id from cart_history where not exists (select * from purchases where cart_history.id = purchases.cart_id and datetime between ? and ? ) and datetime between ? and ? """,[(date_start),(date_finish),(date_start),(date_finish)])
    return len(cursor3.fetchall())

def GetPlot1():
    x = Report1()

    data = pd.Series(x).reset_index(name='value').rename(columns={'index':'country'})
    data['angle'] = data['value']/data['value'].sum() * 2*pi
    data['color'] = Category20c[len(x)]

    p = figure(plot_height=400, title="Посетители из какой страны совершают больше всего действий на сайте", toolbar_location=None,
               tools="hover", tooltips="@country: @value", x_range=(-0.5, 1.0))

    p.wedge(x=0, y=1, radius=0.4,
            start_angle=cumsum('angle', include_zero=True), end_angle=cumsum('angle'),
            line_color="white", fill_color='color', legend='country', source=data)

    p.axis.axis_label=None
    p.axis.visible=False
    p.grid.grid_line_color = None
    
    return p
	
def GetPlot2(name):

    print(name)
    data = Report2(name)
    time_of_days = ['Ночь', 'Утро', 'День', 'Вечер']
    counts = [data['Ночь'],data['Утро'],data['День'],data['Вечер']]
    source = ColumnDataSource(data=dict(time_of_days=time_of_days, counts=counts))

    p = figure(x_range=time_of_days, plot_height=400, toolbar_location=None, title="В какое время суток чаще всего просматривают выбранную категорию товаров")
    p.vbar(x='time_of_days', top='counts', width=0.9, source=source, legend="time_of_days",
           line_color='white', fill_color=factor_cmap('time_of_days', palette=Spectral6, factors=time_of_days))

    p.xgrid.grid_line_color = None
    p.y_range.start = 0
    p.y_range.end = 1500
    p.legend.orientation = "vertical"
    p.legend.location = "top_right"
    
    return p


def create_figure():
    xs = df[x.value].values
    ys = df[y.value].values
    x_title = x.value.title()
    y_title = y.value.title()

    kw = dict()
    if x.value in discrete:
        kw['x_range'] = sorted(set(xs))
    if y.value in discrete:
        kw['y_range'] = sorted(set(ys))
    kw['title'] = "%s vs %s" % (x_title, y_title)

    p = figure(plot_height=600, plot_width=800, tools='pan,box_zoom,hover,reset', **kw)
    p.xaxis.axis_label = x_title
    p.yaxis.axis_label = y_title

    if x.value in discrete:
        p.xaxis.major_label_orientation = pd.np.pi / 4

    sz = 9
    if size.value != 'None':
        if len(set(df[size.value])) > N_SIZES:
            groups = pd.qcut(df[size.value].values, N_SIZES, duplicates='drop')
        else:
            groups = pd.Categorical(df[size.value])
        sz = [SIZES[xx] for xx in groups.codes]

    c = "#31AADE"
    if color.value != 'None':
        if len(set(df[color.value])) > N_SIZES:
            groups = pd.qcut(df[color.value].values, N_COLORS, duplicates='drop')
        else:
            groups = pd.Categorical(df[color.value])
        c = [COLORS[xx] for xx in groups.codes]

    p.circle(x=xs, y=ys, color=c, size=sz, line_color="white", alpha=0.6, hover_color='white', hover_alpha=0.5)

    return p


def update(attr, old, new):
	layout.children[1].children[0] = GetPlot2(new)
	layout.children[1].children[1] = GetPlot1()
	
	
def update_date_start(attr, old, new):
	layout.children[3] = Div(text = 'Количество брошенных корзин за выбранный период: ' + str(Report3(date_start.value,date_finish.value)))

def update_date_finish(attr, old, new):
	layout.children[3] = Div(text = 'Количество брошенных корзин за выбранный период: ' + str(Report3(date_start.value,date_finish.value)))
current_category = Select(title='Выберите категорию продукта:', value='fresh_fish', options= ["fresh_fish", "canned_food", "semi_manufactures", "caviar","frozen_fish"])
current_category.on_change('value', update)

date_start = DatePicker(title = 'Начало периода', value = '2018-08-01')
date_finish = DatePicker(title = 'Конец периода',value = '2018-08-14')
date_start.on_change('value', update_date_start)
date_finish.on_change('value', update_date_finish)
count_carts = Div(text = 'Количество брошенных корзин за выбранный период: ' + str(Report3(date_start.value,date_finish.value)))
#controls = widgetbox([current_category], width=300)
layout = layout([current_category, [GetPlot2("fresh_fish"), GetPlot1()],[date_start,date_finish],count_carts])

curdoc().add_root(layout)
curdoc().title = "Dashboard"