api_key="C01LXoYHTLUd1RV567d37MvqmWKet78l8zX9acVjSJs36L93Xdmgh2TFmR6YPoTf"
api_secret="7I0PJKkfar9pIaQgXTSECoqhKCSVry6poQ6vDLKynQ4p7iYun1XYmnAFKgKYBBQE"

# Importo los paquetes

from binance.client import Client
import pandas as pd
import numpy as np
import datetime
import plotly.graph_objs as go
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

######## LIQUIDITY POOLS

client = Client(api_key, api_secret)

def get_price(symbol,limit,end):
    
    if end==0:
        result=client.futures_klines(symbol=symbol,interval=Client.KLINE_INTERVAL_5MINUTE,limit=limit)
    else:
        end=int(1000*datetime.datetime.timestamp(end))
        result=client.futures_klines(symbol=symbol,interval=Client.KLINE_INTERVAL_5MINUTE,endTime=end,limit=limit)

    # Open time
    # Open
    # High
    # Low
    # Close
    # Volume (volumen en BTC)
    # Close time
    # Quote asset volume (volumen en USDT)
    # Number of trades
    # Taker buy base asset volume (the buyer is the taker and seller is the maker)
    # Taker buy quote asset volume
    # Can be ignored
    
    # The Maker is the person who puts an order in the orderbook. Taker is the one that 
    # matches an existing order (even when both are using Limit orders).
    
    Date=[]
    Open=[]
    High=[]
    Low=[]
    Close=[]
    Volume=[]
    QAV=[]
    NT=[]
    TBBAV=[]
    TBQAV=[]

    for i in range(0,len(result)):
        Date.append(datetime.datetime.fromtimestamp(result[i][0]/1000))
        Open.append(np.float(result[i][1]))
        High.append(np.float(result[i][2]))
        Low.append(np.float(result[i][3]))
        Close.append(np.float(result[i][4]))
        Volume.append(np.float(result[i][5]))
        QAV.append(np.float(result[i][7]))
        NT.append(np.float(result[i][8]))
        TBBAV.append(np.float(result[i][9]))
        TBQAV.append(np.float(result[i][10]))

    Price=pd.DataFrame()
    Price['Date']=Date
    Price['Open']=Open
    Price['High']=High
    Price['Low']=Low
    Price['Close']=Close
    Price['Volume']=Volume
    Price['Quote asset volume']=QAV
    Price['Number of trades']=NT
    Price['Taker buy base asset volume']=TBBAV
    Price['Taker buy quote asset volume']=TBQAV
    
    Price=Price.set_index('Date')
    
    return Price

def LiquidityPool(interval,Price):

    def LiqPrice(leverage,entryPrice,position):
   
        MR=0.004
        
        if position=='long':
            LiqPrice=entryPrice*(1-(100/leverage/100-MR))
        elif position=='short':
            LiqPrice=entryPrice*(1+(100/leverage/100-MR))
            
        return LiqPrice
    
    MIN=interval
    max=int(np.ceil(LiqPrice(10,Price['Close'].max(),'short')/MIN))*MIN+MIN
    min=int(np.ceil(LiqPrice(10,Price['Close'].min(),'long')/MIN))*MIN-MIN
    bins=1+(max-min)/MIN
    b=np.linspace(min,max,int(bins))
    
    c=pd.DataFrame()
    c['Apalancamiento']=['x10L','x25L','x50L','x100L','x10S','x25S','x50S','x100S']
    c=c.set_index('Apalancamiento')
    
    lev=[10,25,50,100,10,25,50,100]
    
    for i in range(0,len(Price)):
        c[i]=0.0
    
    for i in range(0,c.shape[0]):
        for j in range(0,len(Price)):
            if i<=(c.shape[0]/2-1):
                c[j][i]=LiqPrice(lev[i],Price['Close'][j],'long')
            else:
                c[j][i]=LiqPrice(lev[i],Price['Close'][j],'short')
    
    ## Quito los pools que ya fueron liquidados
            
    for i in range(0,c.shape[0]):
        for j in range(0,len(Price)-1):
            if i<=(c.shape[0]/2-1): # Los longs
                if Price['Low'][j+1:len(Price)].min()<c[j][i]:
                    c[j][i]=0.0
            else: # Los short
                if Price['High'][j+1:len(Price)].max()>c[j][i]:
                    c[j][i]=0.0
    ##
    
    e=pd.DataFrame()
    e['Apalancamiento']=['x10L','x25L','x50L','x100L','x10S','x25S','x50S','x100S']
    e=e.set_index('Apalancamiento')
    
    for i in range(0,len(Price)):
        e[i]=0.0

    for i in range(0,e.shape[0]):
        for j in range(0,len(Price)):
        
            #https://www.binance.com/en/blog/421499824684900356/Leverage-and-Derivatives-Overview-of-Binance-Futures-in-2019
        
            if i==0:
                e[j][i]=0.1*Price['Volume'][j]*(Price['Taker buy base asset volume'][j]/Price['Volume'][j])
            elif i==1:
                e[j][i]=0.15*Price['Volume'][j]*(Price['Taker buy base asset volume'][j]/Price['Volume'][j])
            elif i==2:
                e[j][i]=0.1*Price['Volume'][j]*(Price['Taker buy base asset volume'][j]/Price['Volume'][j])
            elif i==3:
                e[j][i]=0.15*Price['Volume'][j]*(Price['Taker buy base asset volume'][j]/Price['Volume'][j])
            elif i==4:
                e[j][i]=0.1*Price['Volume'][j]*(1-Price['Taker buy base asset volume'][j]/Price['Volume'][j])
            elif i==5:
                e[j][i]=0.15*Price['Volume'][j]*(1-Price['Taker buy base asset volume'][j]/Price['Volume'][j])
            elif i==6:
                e[j][i]=0.1*Price['Volume'][j]*(1-Price['Taker buy base asset volume'][j]/Price['Volume'][j])
            elif i==7:
                e[j][i]=0.15*Price['Volume'][j]*(1-Price['Taker buy base asset volume'][j]/Price['Volume'][j])
       
    # Alternativa con groupby
         
    bins1=pd.cut(c.transpose()['x10L'],np.linspace(min, max, int(bins)))
    aux1=(c.transpose()['x10L']*e.transpose()['x10L']).groupby(bins1).sum()

    bins2=pd.cut(c.transpose()['x25L'],np.linspace(min, max, int(bins)))
    aux2=(c.transpose()['x25L']*e.transpose()['x25L']).groupby(bins2).sum()
    
    bins3=pd.cut(c.transpose()['x50L'],np.linspace(min, max, int(bins)))
    aux3=(c.transpose()['x50L']*e.transpose()['x50L']).groupby(bins3).sum()
    
    bins4=pd.cut(c.transpose()['x100L'],np.linspace(min, max, int(bins)))
    aux4=(c.transpose()['x100L']*e.transpose()['x100L']).groupby(bins4).sum()
    
    bins5=pd.cut(c.transpose()['x10S'],np.linspace(min, max, int(bins)))
    aux5=(c.transpose()['x10S']*e.transpose()['x10S']).groupby(bins5).sum()
    
    bins6=pd.cut(c.transpose()['x25S'],np.linspace(min, max, int(bins)))
    aux6=(c.transpose()['x25S']*e.transpose()['x25S']).groupby(bins6).sum()
    
    bins7=pd.cut(c.transpose()['x50S'],np.linspace(min, max, int(bins)))
    aux7=(c.transpose()['x50S']*e.transpose()['x50S']).groupby(bins7).sum()
    
    bins8=pd.cut(c.transpose()['x100S'],np.linspace(min, max, int(bins)))
    aux8=(c.transpose()['x100S']*e.transpose()['x100S']).groupby(bins8).sum()
    
    d=pd.DataFrame()
    d['All']=aux1+aux2+aux3+aux4+aux5+aux6+aux7+aux8
    d['x10']=aux1+aux5
    d['x25']=aux2+aux6
    d['x50']=aux3+aux7
    d['x100']=aux4+aux8
    #d['x10S']=aux5
    #d['x25S']=aux6
    #d['x50S']=aux7
    #d['x100S']=aux8
    d['index']=b[1:]
    d=d.set_index('index')  
    
    return d

RANGE=12*8
SIZE=288*5 # <=1500
MIN=10
LIM=5e6 # defino limite para achicar el tamano del grafico

PR=[]
D=[]
            
Price=get_price('BTCUSDT',limit=SIZE,end=0)

print(Price['Close'][-1])

# Si el size es mayor a 1500:
            
#Price1=get_price('BTCUSDT',limit=SIZE,end=Price.index[0]-datetime.timedelta(minutes=5))
#Price2=get_price('BTCUSDT',limit=SIZE,end=Price1.index[0]-datetime.timedelta(minutes=5))
#Price3=get_price('BTCUSDT',limit=SIZE,end=Price2.index[0]-datetime.timedelta(minutes=5))
#Price=pd.concat([Price3,Price2,Price1,Price])
#Price=pd.concat([Price1,Price])
            
for i in range(0,RANGE):
    if i==0:
        PR.append(Price.index[-1])
        d=LiquidityPool(MIN,Price)
        D.append(d)
        print(str(i+1)+'/'+str(int(RANGE)))
    else:
        PR.append(Price[:-i].index[-1])
        d=LiquidityPool(MIN,Price[:-i])
        D.append(d)
        print(str(i+1)+'/'+str(int(RANGE)))
            
Price=Price[-len(PR):]      

######## DASH

########### Initiate the app
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server
app.title=tabtitle

########### Set up the layout
app.layout = html.Div([
html.Div([
    html.Label('Leverage:'),
    dcc.Dropdown(
        id="leverage",
        options=[
            {'label': 'x10', 'value': 'x10'},
            {'label': 'x25', 'value':'x25'},
            {'label': 'x50', 'value': 'x50'},
            {'label': 'x100', 'value': 'x100'}
        ],
        value=['x10','x25','x50','x100'],
        placeholder="Select one or multiple leverages",
        multi=True,
        clearable=False,
    ),
    html.Label('Filter (M): '),
    dcc.Input(
        id="Filter",
        placeholder='Enter a value...',
        type='number',
        value=20
    ),  
],
style={'width': '49%', 'display': 'inline-block'}
),

html.Div(
    dcc.Graph(
        id='graph',
    style={'width': '100%', 'display': 'inline-block'}
)),

])

@app.callback(
    Output("graph", "figure"), 
    [Input("leverage", "value"),Input("Filter", "value")])

def plot(leverage,Filter):
    
    Filter = Filter * 1e6
    
    layout=go.Layout(
    title=go.layout.Title(text='Liquidity Pools BTC (lookback: '+str(int(SIZE/12))+' hs) - Last update: '+str((Price.index[-1]).strftime("%d-%m-%y %H:%M:%S"))),
    xaxis=go.layout.XAxis(
        side="bottom",
        title="Date"),
    yaxis=go.layout.YAxis(
        tickformat='digits',
        hoverformat='.2f',
        side="left",
        title="Price",
        showgrid=True),
    xaxis2=go.layout.XAxis(
        side="top",
        range=[len(PR),0],
        overlaying="x"))
            
    fig = go.Figure(layout=layout)
    fig.add_trace(go.Candlestick(x=Price.index,
                        open=Price['Open'],
                        high=Price['High'],
                        low=Price['Low'],
                        close=Price['Close'],xaxis="x",yaxis="y",name='Price'))
    fig.update_layout(xaxis_rangeslider_visible=False)
                  
    max1=[]
            
    for i in range(0,len(PR)):
        max1.append(max(D[i][leverage].sum(axis=1)))
       
    for i in range(0,len(PR)):
        text=[f'Price: {round(y,2)}' for y in D[i][leverage].sum(axis=1)[D[i][leverage].sum(axis=1) >= Filter].index]
        text1=[f'<br>Pool x10: {round(yval/1e6,2)} M' for yval in D[i]['x10'][D[i][leverage].sum(axis=1)[D[i][leverage].sum(axis=1) >= Filter].index]]
        text2=[f'<br>Pool x25: {round(yval/1e6,2)} M' for yval in D[i]['x25'][D[i][leverage].sum(axis=1)[D[i][leverage].sum(axis=1) >= Filter].index]]
        text3=[f'<br>Pool x50: {round(yval/1e6,2)} M' for yval in D[i]['x50'][D[i][leverage].sum(axis=1)[D[i][leverage].sum(axis=1) >= Filter].index]]
        text4=[f'<br>Pool x100: {round(yval/1e6,2)} M' for yval in D[i]['x100'][D[i][leverage].sum(axis=1)[D[i][leverage].sum(axis=1) >= Filter].index]]
        res1 = [i + j for i, j in zip(text, text1)]
        res2 = [k + l for k, l in zip(text2, text3)]
        res3 = [m + n for m, n in zip(res1, res2)]
        res = [o + p for o, p in zip(res3, text4)]
        
        fig.add_trace(go.Bar(y=D[i][leverage].sum(axis=1)[D[i][leverage].sum(axis=1) >= Filter].index,x=np.ones(len(D[i][leverage].sum(axis=1)[D[i][leverage].sum(axis=1) >= Filter]))*1,orientation='h',text=res,hoverinfo='text',opacity=0.5,xaxis="x2",yaxis="y",base=(i-0.5),marker=dict(color=D[i][leverage].sum(axis=1)[D[i][leverage].sum(axis=1) >= Filter]/max(max1),colorscale=[[0,'blue'],[0.25,'cyan'],[0.5,'green'],[0.75,'yellow'],[1,'red']],line=dict(color=D[i][leverage].sum(axis=1)[D[i][leverage].sum(axis=1) >= Filter]/max(max1),colorscale=[[0,'blue'],[0.25,'cyan'],[0.5,'green'],[0.75,'yellow'],[1,'red']],width=0.5))))
               
    fig.update_layout(barmode='stack')
    fig.update_yaxes(nticks=30)
    fig.update_layout(template='plotly_dark')
    fig.update_layout(showlegend=False)
    
    return fig

if __name__ == '__main__':
    app.run_server()
