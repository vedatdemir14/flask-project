from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from wtforms.validators import DataRequired,Length,Email,EqualTo
from passlib.hash import sha256_crypt
from functools import wraps
from flask_mysqldb import MySQL
#Giriş Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Kontrol Panelini Kullanabilmek İçin Giriş Yapmanız Gerekmektedir","danger")
            return redirect(url_for("login"))
    
    return decorated_function

#Kullanıcı Kayıt Formu

class RegisterForm(Form):
    name = StringField("İsim Soyisim",validators=[validators.Length(min = 4,max = 30)])
    username = StringField("Kullanıcı Adı",validators=[validators.Length(min = 5,max = 35)
    ])
    email = StringField("Email",validators=[validators.Email(message = "Lütfen Geçerli Bir Email Adresi Giriniz")])
    password = PasswordField("Şifre",validators=[
        validators.data_required(message = "Lütfen Bir Parola Belirleyiniz"),
        validators.EqualTo(fieldname="confirm",message="Parolanız Uyuşmuyor"),
    
    ])
    confirm = PasswordField("Şifre Doğrulama")

class LoginForm(Form):
    username = StringField("Kullanıcı Adı")
    password = PasswordField("Parola")


app = Flask(__name__)
app.secret_key = "blog"

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "blog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"


mysql = MySQL(app)


@app.route("/")
def index():
    
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/dashboard")
@login_required
def dashboard():
    cursor= mysql.connection.cursor()

    sorgu = "SELECT * FROM articles where author = %s"
    result = cursor.execute(sorgu,(session["username"],))

    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html",articles = articles)
    else: 
        return render_template("dashboard.html")

@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()

    sorgu = "SELECT * FROM articles"

    result = cursor.execute(sorgu)

    if result > 0:
        articles = cursor.fetchall()
        return render_template("articles.html",articles = articles)
    else:
        return render_template("articles.html")

#Kayıt Olma Bölümü
@app.route("/register",methods = ["GET","POST"])
def register():
    form = RegisterForm(request.form)

    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor()

        sorgu = "Insert into users(name,email,username,password) VALUES(%s,%s,%s,%s)"
        
        cursor.execute(sorgu,(name,email,username,password))
        mysql.connection.commit()

        cursor.close()

        flash("Kaydınız Başarıyla Tamamlandı.","success")

        return redirect(url_for("login"))

    else:
        return render_template("register.html",form= form)
    
@app.route("/login",methods = ["GET","POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST":
        username = form.username.data
        password_entered = form.password.data

        cursor = mysql.connection.cursor()

        sorgu = "SELECT * FROM users WHERE username = %s"
        result = cursor.execute(sorgu,(username,))

        if result > 0:
            data = cursor.fetchone()
            real_password = data["password"]
            if sha256_crypt.verify(password_entered,real_password):
                flash("Başarıyla Giriş Yapıldı","success")
                
                session["logged_in"] = True

                session["username"] = username
                return redirect(url_for("index"))
            else:
                flash("Parolanızı Yanlış Girdiniz","danger")
                return redirect(url_for("login"))

        else:
            flash("Böyle Bir Kullanıcı Bulunmamaktadır","danger")
            return redirect(url_for("login"))

    return render_template("login.html",form = form)

@app.route("/article/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()

    sorgu = "SELECT * FROM articles WHERE id =%s"
    result = cursor.execute(sorgu,(id,))

    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html",article = article)
    else:
        return render_template("article.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Hesaptan Çıkış Başarıyla Tamamlandı","success")
    return redirect(url_for("index"))
@app.route("/addarticle",methods = ["GET","POST"])
def addarticle():
    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        content= form.content.data
        
        cursor = mysql.connection.cursor()
        sorgu = "Insert into articles (title,author,content) VALUES(%s,%s,%s)"
        cursor.execute(sorgu,(title,session["username"],content))
        mysql.connection.commit()
        cursor.close()
        flash("Makaleniz Başarıyla Sisteme Eklenmiştir","success")
        return redirect(url_for("dashboard"))
    return render_template("addarticle.html",form = form)

@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()

    sorgu = "SELECT * FROM articles WHERE author = %s and id = %s"

    result = cursor.execute(sorgu,(session["username"],id))

    if result > 0 :
        sorgu2 = "DELETE FROM articles WHERE id = %s"
        cursor.execute(sorgu2,(id,))
        mysql.connection.commit()

        return redirect(url_for("dashboard"))

    else:
        flash("Böyle Bir Makale Bulunmamaktadır ya da Bu Makaleyi Silme Yetkiniz Bulunmamaktadır.","danger")
        return redirect(url_for("index"))

@app.route("/edit/<string:id>",methods = ["GET","POST"])
@login_required
def update(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()

        sorgu = "SELECT * FROM articles WHERE id= %s and author= %s"
        result = cursor.execute(sorgu,(id,session["username"]))

        if result == 0:

            flash("Böyle Bir Makale Bulunmamaktadır ya da Bu Makaleye Erişim Yetkiniz Bulunmamaktadır.","danger")
            return redirect(url_for("index"))

        else:
            article = cursor.fetchone()
            form = ArticleForm()

            form.title.data = article["title"]
            form.content.data = article ["content"]
            return render_template("update.html",form = form)    
    else:
        form = ArticleForm(request.form)
        
        newTitle = form.title.data
        newContent = form.content.data

        sorgu2 = "UPDATE articles SET title = %s,content = %s WHERE id=%s"
        
        cursor = mysql.connection.cursor()

        cursor.execute(sorgu2,(newTitle,newContent,id))

        mysql.connection.commit()

        flash("Makaleniz Başarıyla Güncellenmiştir","success")

        return redirect(url_for("dashboard"))
@app.route("/search",methods = ["GET","POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")

        cursor = mysql.connection.cursor()

        sorgu = "SELECT * FROM articles WHERE title like '%"+ keyword +"%' " 

        result = cursor.execute(sorgu)

        if result == 0:
            flash("Aradığınıza Benzer Makale Bulunamadı.","warning")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()

            return render_template("articles.html",articles = articles)   
@app.route("/user_profile_page",methods = ["GET","POST"])
@login_required
def userpage():
    if request.method == "POST":
        return redirect(url_for("index"))
    else:
        return render_template("user_profil_page.html")








#Makale Formu

class ArticleForm(Form):
    title = StringField("Makale Başlığı",validators= [validators.Length(min = 5,max = 100)])
    content = TextAreaField("Makale İçeriği",validators = [validators.Length(min = 10)])

if __name__ == "__main__":
    app.run(debug=True)
