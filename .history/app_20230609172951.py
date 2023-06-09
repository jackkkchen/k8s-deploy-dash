import dash                                # pip install dash
from dash import dcc
from dash import html
from dash.dependencies import Output, Input
import dash_bootstrap_components as dbc    # pip install dash-bootstrap-components
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from alpha_vantage.timeseries import TimeSeries # pip install alpha-vantage
#该api并不是实时数据，每五秒一次调用api来更新本地的csv文件，然后只拉取最大的两个日期，一个叫recenthigh 一个叫olderhigh，然后将会在两者间进行比较，

#参考https://github.com/RomelTorres/alpha_vantage 调用pandas
# ts = TimeSeries(key='0Q466LJ33OMBCN3O', output_format='pandas') # 'pandas' or 'json' or 'csv' 从api中提取pandas格式的时间序列
# data, meta_data = ts.get_intraday( # 这是我们从api中提取的地方，intraday就是当天的数据，
#     symbol='NVDA', # NVDA是我们拉取的公司股票
#     interval='1min', # 设置每一分钟拉动一次
#     outputsize='compact' # 数据输出大小默认为compact，可以减少数据大小，完整长度的话可以设置为full
#     )  
# df = data.copy()
# df=df.transpose() # 然后是转置，重命名，合并
# df.rename(index={"1. open":"open", "2. high":"high", "3. low":"low",
#                  "4. close":"close","5. volume":"volume"},inplace=True) # 替换掉数字
# df=df.reset_index().rename(columns={'index': 'indicator'}) # 替换index
# df = pd.melt(df,id_vars=['indicator'],var_name='date',value_name='rate')
# df = df[df['indicator']!='volume'] # 这里给主列重命名
# print(df.head()) 

# df.to_csv("data.csv", index=False) # 最后建议大家还是把上面打印的数据保存到本地，因为如果你构建dash之后，每次点击刷新网页，都会对你的api和应用程序产生负担。
# # 每人只能申请五个免费api，每分钟只能请求一次，所以我们调用一次api之后，存到本地，然后用dash从csv中拉取数据就能避免api使用过多。
# exit()

# 读取从API中下载的文件
dff = pd.read_csv('https://raw.githubusercontent.com/jackkkchen/k8s-deploy-dash/main/data.csv')
dff = dff[dff.indicator.isin(['high'])] #为了还原网站，只取high，也就是股票的最高点


app = dash.Dash(__name__, #启动并初始化dash，构建components
                external_stylesheets=[dbc.themes.BOOTSTRAP], #使用bootstrap主题
                meta_tags=[{'name': 'viewport',
                            'content': 'width=device-width, initial-scale=1.0'}]
                ) #这部分是不会变的，他能运行你的dash apps在移动端具有响应式布局，在你的手机上自适应排版

app.layout = dbc.Container([ # 使用dbc容器构建layout
    dbc.Row([ # 第一个组件，应该是会包含这整个仪表盘，之后的排版都是在此基础上
        dbc.Col([ # 第二个里面放小组件
            dbc.Card( 
                [
                    dbc.CardImg( #最上面要有个公司的logo 
                        src="./assets/Nvidia-logo.png", 
                        top=True, #放在顶部
                        style={"width": "6rem"}, #设置宽度
                    ),

                    dbc.CardBody([  #然后是主体部分，我们一共需要4行
                        dbc.Row([   #每一行都需要列组件，这里需要两个组件
                            dbc.Col([
                                html.P("CHANGE (1D)")
                            ]),

                            dbc.Col([
                                dcc.Graph(id='indicator-graph', figure={},
                                          config={'displayModeBar':False})
                            ])
                        ]),

                        dbc.Row([  #第二行，只需要一个组件，折线图的图像
                            dbc.Col([
                                dcc.Graph(id='daily-line', figure={},
                                          config={'displayModeBar':False})
                            ])
                        ]),

                        dbc.Row([  #第三行，需要两个组件，买和卖
                            dbc.Col([
                                dbc.Button("SELL"),
                            ]),

                            dbc.Col([   
                                dbc.Button("BUY")
                            ])
                        ]),

                        dbc.Row([   #第四行，需要两个组件 买卖数据
                            dbc.Col([
                                dbc.Label(id='low-price', children="308.9"),
                            ]),
                            dbc.Col([
                                dbc.Label(id='high-price', children="309.56"),
                            ])
                        ])
                    ]),
                ],
                style={"width": "24rem"}, # 仪表盘中卡片的宽度
                className="mt-3" # 边距的前三个空间单位
            )
        ], width=6) #整个仪表盘的宽度
    ], justify='center'), #整个仪表盘放在中间

    dcc.Interval(id='update', n_intervals=0, interval=1000*5) #间隔每五秒更新一次app
])
# 上面只是整体的布局，可以看到我们的图像都还是空的， 所以我们下面需要加入数据和绘图。比如这里，根据plotly给的案例，我们需要对比当天的开头和结尾，如果收盘价高于开盘价，则是上升比例

# Indicator Graph  #创建回调，
@app.callback(
    Output('indicator-graph', 'figure'), #indicator将返回的图像，回调到上面dcc.Graph的卡片中； figure 返回下面fig的图像
    Input('update', 'n_intervals') # 这个n_intervals 对应下面的回调函数中的这个参数，timer，指的是n个间隔，因为他为零我们上面设置了，
) 
 
def update_graph(timer):  # 所以当我们加载app的时候，他会为0，过了五秒之后进行刷新，然后下面这里会变为1，再过五秒变为2
    dff_rv = dff.iloc[::-1] #倒转时间顺序
    day_start = dff_rv[dff_rv['date'] == dff_rv['date'].min()]['rate'].values[0] # 取出日期最小也就是开盘价数据
    day_end = dff_rv[dff_rv['date'] == dff_rv['date'].max()]['rate'].values[0] # 取出日期最大也就是收盘价数据

    fig = go.Figure(go.Indicator( #构建指标
        mode="delta", #显示百分百
        value=day_end, # 取收盘价
        delta={'reference': day_start, 'relative': True, 'valueformat':'.2%'})) #用收盘价对比开盘价，得出当天百分百，设为小数点后两位
    fig.update_traces(delta_font={'size':12}) #设置百分比的字体大小
    fig.update_layout(height=30, width=70) #设置百分比高宽

    if day_end >= day_start:  #对比正负 设置红绿
        fig.update_traces(delta_increasing_color='red')
    elif day_end < day_start:
        fig.update_traces(delta_decreasing_color='green')

    return fig  #返回正确图像

# Line Graph---------------------------------------------------------------
@app.callback(
    Output('daily-line', 'figure'),
    Input('update', 'n_intervals')
)
def update_graph(timer):
    dff_rv = dff.iloc[::-1]  # 同样调转时间顺序，不然的话就是从刚结束时间到开始时间
    fig = px.line(dff_rv, x='date', y='rate',
                   range_y=[dff_rv['rate'].min(), dff_rv['rate'].max()],  #限制y轴范围和120高度
                   height=120).update_layout(margin=dict(t=0, r=0, l=0, b=20),  #参考plotly中Figure Reference>layout 找到 margin参数 这是设置图像高宽度的
                                             paper_bgcolor='rgba(0,0,0,0)', #设置整体的背景颜色为白色，默认为灰色
                                             plot_bgcolor='rgba(0,0,0,0)', #设置图像的背景颜色为白色，默认为灰色
                                             yaxis=dict(
                                             title=None,
                                             showgrid=False, #是否设置网格线
                                             showticklabels=False #是否设置刻度标签
                                             ),
                                             xaxis=dict(
                                             title=None,
                                             showgrid=False, 
                                             showticklabels=False
                                             ))
#过滤数据，创建开始和结束日期
    day_start = dff_rv[dff_rv['date'] == dff_rv['date'].min()]['rate'].values[0]
    day_end = dff_rv[dff_rv['date'] == dff_rv['date'].max()]['rate'].values[0]
#对比大小，上涨为红色
    if day_end >= day_start:
        return fig.update_traces(fill='tozeroy',line={'color':'red'}) # fill将该区域设置为纯色填充，查看plotly中 scatter（trace等同于line chart）文档
    elif day_end < day_start:
        return fig.update_traces(fill='tozeroy',
                             line={'color': 'green'})

# Below the buttons--------------------------------------------------------
@app.callback(
    Output('high-price', 'children'),
    Output('high-price', 'className'),
    Input('update', 'n_intervals')
)
def update_graph(timer):
    if timer ==0:
        dff_filtered = dff.iloc[[21,22]]
        print(dff_filtered)
    elif timer == 1:
        dff_filtered = dff.iloc[[20,21]]
        print(dff_filtered)
    elif timer == 2:
        dff_filtered = dff.iloc[[19,20]]
        print(dff_filtered)
    elif timer == 3:
        dff_filtered = dff.iloc[[18,19]]
        print(dff_filtered)
    elif timer == 4:
        dff_filtered = dff.iloc[[17,18]]
        print(dff_filtered)
    elif timer == 5:
        dff_filtered = dff.iloc[[16,17]]
        print(dff_filtered)
    elif timer > 5:
        return dash.no_update

    recent_high = dff_filtered['rate'].iloc[0]
    older_high = dff_filtered['rate'].iloc[1]
    # print(recent_high, older_high)

    if recent_high > older_high:
        return recent_high, "mt-2 bg-danger text-white p-1 border border-primary border-top-0"
    elif recent_high == older_high:
        return recent_high, "mt-2 bg-white p-1 border border-primary border-top-0"
    elif recent_high < older_high:
        return recent_high, "mt-2 bg-success text-white p-1 border border-primary border-top-0"

 
if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0',port=8000,use_reloader=False)