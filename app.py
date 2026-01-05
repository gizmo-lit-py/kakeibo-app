from flask import Flask, render_template, redirect, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, login_required, logout_user, current_user

from werkzeug.security import generate_password_hash, check_password_hash
import os

from datetime import datetime
import pytz

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///kakeibo.db'
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_secret-key')
db = SQLAlchemy(app)


login_manager = LoginManager() 
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/")
def index():
    return render_template('base.html')

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if User.query.filter_by(username=username).first():
            return 'そのユーザーは使われています'
        
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        return redirect("/")
    return render_template('register.html')


@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect("/")
        return 'ユーザー名かパスワードが違います'
    return render_template('login.html')


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")

@app.route("/add", methods=['GET', 'POST'])
@login_required
def add():
    if request.method == "POST":
        amount = request.form.get('amount')
        t_type = request.form.get('kind')
        category = request.form.get('category')
        memo = request.form.get('memo')

        if not amount:
            return '金額を入力してください'
        
        try:
            amount_int = int(amount)
        except (TypeError, ValueError):
            return '金額を数字で入力してください'
        
        if amount_int <= 0:
            return '金額は１以上にしてください'
        
        if t_type not in ['income', 'expense']:
            return '種類が不正です'
        
        transaction = Transaction(
            amount=amount_int,
            kind=t_type,
            category=category,
            memo=memo,
            user_id=current_user.id
        )

        db.session.add(transaction)
        db.session.commit()

        return redirect("/transactions")
    return render_template("add.html")
        
        
@app.route("/transactions")
@login_required
def transactions():
    txs = (
        Transaction.query
        .filter_by(user_id=current_user.id)
        .order_by(Transaction.date.desc())
        .all()
    )

    income_total = 0
    expense_total = 0

    for t in txs:
        if t.kind == 'income':
            income_total += t.amount
        elif t.kind == 'expense':
            expense_total += t.amount

    balance = income_total - expense_total

    return render_template(
        'transactions.html', 
         transactions=txs,
        income_total=income_total,
        expense_total=expense_total,
        balance=balance
        )

@app.route("/delete/<int:tx_id>", methods=['POST'])
@login_required
def  delete(tx_id):
    t = Transaction.query.get_or_404(tx_id)

    if t.user_id !=current_user.id:
        return '権限がありません', 403
    
    db.session.delete(t)
    db.session.commit()

    return redirect("/transactions")



def now_jst():
    return datetime.now(pytz.timezone('Asia/Tokyo'))

@app.route("/edit/<int:tx_id>", methods=["GET", "POST"])
@login_required
def edit(tx_id):
    t = Transaction.query.get_or_404(tx_id)

    if t.user_id != current_user.id:
        return "権限がありません", 403

    if request.method == "POST":
        amount = request.form.get("amount")
        kind = request.form.get("kind")
        category = request.form.get("category")
        memo = request.form.get("memo")

        try:
            amount_int = int(amount)
        except (TypeError, ValueError):
            return "金額を数字で入力してください"

        if amount_int <= 0:
            return "金額は１以上にしてください"

        if kind not in ["income", "expense"]:
            return "種類が不正です"

        t.amount = amount_int
        t.kind = kind
        t.category = category
        t.memo = memo

        db.session.commit()
        return redirect("/transactions")

    
    return render_template("edit.html", t=t)




class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=now_jst)


    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Integer, nullable=False)
    kind = db.Column(db.String(10), nullable=False)
    category = db.Column(db.String(50))
    memo = db.Column(db.String(200))
    date = db.Column(db.DateTime, nullable=False, default=now_jst)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    
    
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        app.run(debug=True, port=5001)

    


    

