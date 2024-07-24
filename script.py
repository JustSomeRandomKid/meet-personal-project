from flask import Flask, render_template,request,redirect,url_for
from flask import session as login_session
import pyrebase
import math
import time
import random
import threading

firebaseConfig = {
  "apiKey": "AIzaSyCcR5GJdFK0ReMLbbP_R9NUwhs_bGY8i4A",
  "authDomain": "database-project-ed4f6.firebaseapp.com",
  "projectId": "database-project-ed4f6",
  "storageBucket": "database-project-ed4f6.appspot.com",
  "messagingSenderId": "1033675079496",
  "appId": "1:1033675079496:web:413ceac2a5e5b5951d3d7d",
  "databaseURL":"https://database-project-ed4f6-default-rtdb.europe-west1.firebasedatabase.app/"
}
firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()

app = Flask(__name__)
app.config['SECRET_KEY']="CS forever"

db =firebase.database()

current_user_event = threading.Event()
current_user_value = None

def updateBalance():
    db = firebase.database()
    global current_user_value
    if current_user_value!= None:
        stocks = db.child('stockInfo').get().val().keys()
        finalBalance = 0
        uid = current_user_value['localId']
        print(uid)
        liquidity = db.child('users').child(uid).child('liquidity').get().val()
        for stock in stocks:
            stockPrice = db.child('stockInfo').child(stock).child('prices').child('1').get().val()
            amountOfStock = db.child('users').child(uid).child('stocksOwned').child(stock).get().val()
            finalBalance += amountOfStock * stockPrice
        finalBalance = float(finalBalance)
        liquidity = float(liquidity)
        db.child('users').child(uid).child('balance').update({'balance': finalBalance + liquidity})

def updateStockPrice(stock,lastTodayBuys):
    db=firebase.database()
    todayBuys=int(db.child('stockInfo').child(stock).child('buysToday').get().val())
    totalPublicStocks=db.child('stockInfo').child(stock).child('totalStocks').get().val()
    currentPrice=db.child('stockInfo').child(stock).child('prices').child('1').get().val()
    stablizer=0.1*random.randint(1,15)*random.choice([-1,1])
    updatedPrice=currentPrice+((todayBuys-lastTodayBuys))+stablizer
    return updatedPrice
def run():
    with app.app_context():
        global current_user_value
        print(current_user_value) 
        with app.app_context():
            db = firebase.database()
            stocks = db.child('stockInfo').get().val().keys()
            while True:
                updateBalance()
                print(current_user_event)
                for stock in stocks:
                    lastTodayBuys = int(db.child('stockInfo').child(stock).child('buysToday').get().val())
                    time.sleep(1)
                    db = firebase.database()
                    db.child('stockInfo').child(stock).child('prices').update({'1': updateStockPrice(stock, lastTodayBuys)})

thread = threading.Thread(target=run)
thread.start()

    
@app.route('/signIn',methods=['GET','POST'])
def signIn():
    if request.method == 'GET':
        return render_template('signIn.html')
    email = request.form['email']
    password = request.form['password']
    try:
        global current_user_value
        user_record = auth.sign_in_with_email_and_password(email, password)
        login_session['user'] = user_record
        current_user_value = user_record
        current_user_event.set() 
    except Exception as e:
        print("Error:",e)
    return redirect(url_for('home'))
    
@app.route('/',methods=['GET','POST'])
@app.route('/home',methods=['GET','POST'])
def home():
    try:
        username=db.child('users').child(login_session['user']['localId']).child('username').get().val()
        stocksOwned = db.child('users').child(login_session['user']['localId']).child('stocksOwned').get().val()
        accountBalance=db.child('users').child(login_session['user']['localId']).child('balance').get().val()
        uid=login_session['user']['localId']
    except:
        username="Guest"
        stocksOwned={'no stocks data':'user is not signed in'}
        accountBalance='undefined'
        uid = ""
    return render_template('home.html',username=username,stocksOwned=stocksOwned,balance=accountBalance,uid=uid)

@app.route('/signUp',methods=['GET','POST'])
def signUp():
    if request.method == 'GET':
        return render_template('signUp.html')
    email = request.form['email']
    password = request.form['password']
    username= request.form['username']
    balance = 10000
    try:
        user_record = auth.create_user_with_email_and_password(email,password)
        db.child('users').child(login_session['user']['localId']).set({'username':username,'balance':balance,'liquidity':balance,'stocksOwned':{}})
        login_session['user'] = user_record
        auth.current_user = user_record
    except Exception as e:
        print("Error:",e)

    return redirect(url_for('home'))



@app.route('/signOut')
def signOut():
    auth.current_user = None
    login_session['user']=None
    return redirect(url_for('home'))


@app.route('/trade',methods=['GET','POST'])
def trade():
    if login_session['user'] is not None:
        if request.method=='GET':
            balance=db.child('users').child(login_session['user']['localId']).child('balance').get().val()
            liquidity = db.child('users').child(login_session['user']['localId']).child('liquidity').get().val()
            try:
                uid=login_session['user']['localId']
            except:
                uid=""
            return render_template('trade.html',balance=balance,liquidity=liquidity,uid=uid)
        return redirect(url_for('tradeStockPage',request.form['stock']))
    return redirect(url_for('home'),)

@app.route('/stock/<stock>')
def tradeStockPage(stock):
    currentPrice = db.child('stockInfo').child(stock).child('prices').child('1').get().val()
    #display and create graph...
    return render_template('stock.html',stock=stock,currentPrice=currentPrice)

@app.route('/stock/<stock>/buy',methods=['GET','POST'])
def buyAStock(stock):
    stockPrice = db.child('stockInfo').child(stock).child('prices').child('1').get().val()
    liquidity = db.child('users').child(login_session['user']['localId']).child('liquidity').get().val()
    try:
        stocksOwned = db.child('users').child(login_session['user']['localId']).child('stocksOwned').get().val()
    except:
        stocksOwned=""
    try:
        stockInProfolio = int(db.child('users').child(login_session['user']['localId']).child('stocksOwned').child(stock).get().val())
    except:
        stockInProfolio=""
    if liquidity > stockPrice:
        db.child('users').child(login_session['user']['localId']).child('liquidity').set(liquidity-stockPrice) # pay for the stock
        todayBuys=int(db.child('stockInfo').child(stock).child('buysToday').get().val())
        db.child('stockInfo').child(stock).child('buysToday').set(todayBuys+1) # update amount of buyers today
        if stock in stocksOwned:
            db.child('users').child(login_session['user']['localId']).child('stocksOwned').child(stock).set(stockInProfolio+1) # add stock to profolio
        else:
            db.child('users').child(login_session['user']['localId']).child('stocksOwned').child(stock).set(1) # add stock to profolio
        return render_template('success.html',action="bought",stock=stock)
    return redirect(url_for('tradeStockPage',stock=stock))


@app.route('/stock/<stock>/sell',methods=['GET','POST'])
def sellAStock(stock):
    stockPrice = db.child('stockInfo').child(stock).child('prices').child('1').get().val()
    liquidity = db.child('users').child(login_session['user']['localId']).child('liquidity').get().val()
    stocksOwned = db.child('users').child(login_session['user']['localId']).child('stocksOwned').get().val()
    try:
        stockInProfolio = int(db.child('users').child(login_session['user']['localId']).child('stocksOwned').child(stock).get().val())
    except:
        stockInProfolio=""
    if stock in stocksOwned and stockInProfolio>=1:
        db.child('users').child(login_session['user']['localId']).child('liquidity').set(liquidity+stockPrice) # get money for the stock
        todayBuys=int(db.child('stockInfo').child(stock).child('buysToday').get().val())
        db.child('stockInfo').child(stock).child('buysToday').set(todayBuys-1) # update amount of buyers today
        db.child('users').child(login_session['user']['localId']).child('stocksOwned').child(stock).set(stockInProfolio-1) # remove stock from profolio
        return render_template('success.html',action="sold",stock=stock)
    return redirect(url_for('tradeStockPage',stock=stock))


if __name__ == '__main__':
    app.run(debug=True)