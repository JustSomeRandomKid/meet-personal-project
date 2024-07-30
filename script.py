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
        finalBalance = 0
        uid = current_user_value['localId']
        try:
            stocks = db.child('users').child(uid).child('stocksOwned').get().val().keys()
        except Exception as e:
            stocks={}
            print(e)
        liquidity = db.child('users').child(uid).child('liquidity').child('liquidity').get().val()
        for stock in stocks:
            stockPrice = db.child('stockInfo').child(stock).child('prices').child('1').get().val()
            amountOfStock = db.child('users').child(uid).child('stocksOwned').child(stock).get().val()
            finalBalance += amountOfStock * stockPrice
        finalBalance = float(finalBalance)
        liquidity = float(liquidity)
        db.child('users').child(uid).child('balance').update({'balance': finalBalance + liquidity})

def updateStockPrice(stock,lastTodayBuys):
    db=firebase.database()
    todayBuys=int(db.child('stockInfo').child(stock).child('buysToday').child('buysToday').get().val())
    totalPublicStocks=db.child('stockInfo').child(stock).child('totalStocks').child('totalStocks').get().val()
    currentPrice=db.child('stockInfo').child(stock).child('prices').child('1').get().val()
    stablizer=0.1*random.randint(1,15)*random.choice([-1,1])
    updatedPrice=currentPrice+((todayBuys-lastTodayBuys))+stablizer
    return updatedPrice
def run():
    with app.app_context():
        global current_user_value
        with app.app_context():
            db = firebase.database()
            stocks = db.child('stockInfo').get().val().keys()
            while True:
                updateBalance()
                for stock in stocks:
                    lastTodayBuys = int(db.child('stockInfo').child(stock).child('buysToday').child('buysToday').get().val())
                    time.sleep(0.5)
                    db = firebase.database()
                    db.child('stockInfo').child(stock).child('prices').update({'1': updateStockPrice(stock, lastTodayBuys)})

thread = threading.Thread(target=run)
thread.start()

@app.route('/try')
def trying():
    return render_template('try.html')

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
    global current_user_value
    try:
        stocksOwned = db.child('users').child(login_session['user']['localId']).child('stocksOwned').get().val()
        accountBalance=db.child('users').child(login_session['user']['localId']).child('balance').child('balance').get().val()
        uid=login_session['user']['localId']
        username=db.child('users').child(login_session['user']['localId']).child('username').get().val()
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
        login_session['user'] = user_record
        current_user_value = user_record
        current_user_event.set() 
        db.child('users').child(login_session['user']['localId']).set({'username':username,'balance':{"balance":balance},'liquidity':{"liquidity":balance},'stocksOwned':{}})
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
            liquidity = db.child('users').child(login_session['user']['localId']).child('liquidity').child('liquidity').get().val()
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
    priceHistory = db.child('stockInfo').child(stock).child('prices').get().val()
    return render_template('stock.html',stock=stock,currentPrice=currentPrice,price_history=priceHistory)

@app.route('/stock/<stock>/buy', methods=['POST'])
def buyAStock(stock):
    quantity = int(request.form['quantity'])
    stockPrice = db.child('stockInfo').child(stock).child('prices').child('1').get().val()
    liquidity = db.child('users').child(login_session['user']['localId']).child('liquidity').child('liquidity').get().val()
    totalPublicStocks = db.child('stockInfo').child(stock).child('totalStocks').child('totalStocks').get().val()

    if liquidity >= stockPrice * quantity and totalPublicStocks >= quantity:
        new_liquidity = liquidity - stockPrice * quantity
        db.child('users').child(login_session['user']['localId']).child('liquidity').update({'liquidity': new_liquidity})

        try:
            stockInPortfolio = int(db.child('users').child(login_session['user']['localId']).child('stocksOwned').child(stock).get().val())
        except:
            stockInPortfolio = 0

        db.child('users').child(login_session['user']['localId']).child('stocksOwned').update({stock: stockInPortfolio + quantity})
        db.child('stockInfo').child(stock).child('totalStocks').update({'totalStocks': totalPublicStocks - quantity})

        # Increment buysToday by the quantity of stocks bought
        todayBuys = int(db.child('stockInfo').child(stock).child('buysToday').child('buysToday').get().val())
        new_buys_today = todayBuys + quantity
        db.child('stockInfo').child(stock).child('buysToday').update({'buysToday': new_buys_today})

        return "Success"
    return "Failed"


@app.route('/stock/<stock>/sell', methods=['POST'])
def sellAStock(stock):
    quantity = int(request.form['quantity'])
    stockPrice = db.child('stockInfo').child(stock).child('prices').child('1').get().val()
    liquidity = db.child('users').child(login_session['user']['localId']).child('liquidity').child('liquidity').get().val()
    
    try:
        stockInPortfolio = int(db.child('users').child(login_session['user']['localId']).child('stocksOwned').child(stock).get().val())
    except:
        stockInPortfolio = 0
    
    if stockInPortfolio >= quantity:
        new_liquidity = liquidity + stockPrice * quantity
        db.child('users').child(login_session['user']['localId']).child('liquidity').update({'liquidity': new_liquidity})
        db.child('users').child(login_session['user']['localId']).child('stocksOwned').update({stock: stockInPortfolio - quantity})
        
        totalPublicStocks = db.child('stockInfo').child(stock).child('totalStocks').child('totalStocks').get().val()
        db.child('stockInfo').child(stock).child('totalStocks').update({'totalStocks': totalPublicStocks + quantity})
        
        # Decrement buysToday by the quantity of stocks sold
        todayBuys = int(db.child('stockInfo').child(stock).child('buysToday').child('buysToday').get().val())
        new_buys_today = max(todayBuys - quantity, 0)
        db.child('stockInfo').child(stock).child('buysToday').update({'buysToday': new_buys_today})
        
        return "Success"
    return "Failed"

if __name__ == '__main__':
    app.run(debug=True)