import os


from flask import (Flask, flash, render_template,
                   redirect, request, session, url_for)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from datetime import datetime
import calendar
from werkzeug.security import generate_password_hash, check_password_hash


if os.path.exists('env.py'):
    import env


app = Flask(__name__)


app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")


mongo = PyMongo(app)


@app.route("/")
@app.route("/index.html")
def homepage():
    return render_template("index.html")


@app.route("/ingredients.html")
def ingredients():
    ingredients = mongo.db.ingredients.find()
    documents = list(ingredients)
    now = datetime.now()
    current_month = now.strftime("%m")
    this_month = calendar.month_name[int(current_month)]
    if this_month == "December":
        next_month = "January"
    else:
        next_month = calendar.month_name[(int(current_month)) + 1]
        months = mongo.db.months.find()
    for x in months:
        if x.get(this_month):
            current_ingredients = x.get(this_month)
        elif x.get(next_month):
            next_month_ingredients = x.get(next_month)

    return render_template('ingredients.html', ingredients=ingredients, documents=documents, this_month=this_month, next_month=next_month, current_ingredients=current_ingredients, months=months, next_month_ingredients=next_month_ingredients)


@app.route("/recipes.html")
def recipes():
    recipes = mongo.db.recipes.find()
    return render_template('recipes.html', recipes=recipes)


@app.route("/search", methods=["GET", "POST"])
def search():
    query = request.form.get("query")
    recipes = list(mongo.db.recipes.find({"$text": {"$search": query}}))
    return render_template("recipes.html", recipes=recipes)


@app.route("/ingredient_recipes", methods=["POST"])
def getingredientrecipes():
    if request.method == 'POST':
        if request.form['currentmonthbutton']:
            selected_ingredient = request.form["currentmonthbutton"]
            recipes = list(mongo.db.recipes.find(
                {"$text": {"$search": selected_ingredient}}))
            return render_template("recipes.html", recipes=recipes, selected_ingredient=selected_ingredient)


@app.route("/fullrecipe/<recipe>",  methods=["GET", "POST"])
def fullrecipe(recipe):
    test = request.form["fullrecipebtn"]
    session['recipe'] = test
    recipe = mongo.db.recipes.find_one({"recipe_name": test})
    return render_template("fullrecipe.html", test=test, recipe=recipe)

@app.route("/fullrecipe/saverecipe/<recipe>",  methods=["GET", "POST"])

def saverecipe(recipe):
    
    if session['current_user']:
        recipe_id = request.form['saverecipebtn']
        recipe = session.get('recipe')
        username = mongo.db.users.find_one(
            {"email": session["current_user"]})['email']
        if mongo.db.users.find_one({"favourite_recipes":recipe_id}):
            flash ('Recipe already saved')
            return redirect(url_for('homepage')) 
        else:     
            mongo.db.users.update({'email':username},{"$push": {"favourite_recipes":recipe_id}})
            flash ("Recipe saved!")
            return redirect(url_for('homepage')) 
        
          
    

@app.route("/myrecipes/<username>", methods=["GET", "POST"])
def myrecipes(username):
    email = mongo.db.users.find_one(
        {"email": session["current_user"]})['email']
    
    username = mongo.db.users.find_one(
        {"email": session["current_user"]})['username']
    

    # get user's saved recipes
    user_recipes = mongo.db.users.find_one({"email": session["current_user"]})[
        'favourite_recipes']

    def getrecipebyId(recipeID):
        return mongo.db.recipes.find_one({"_id": ObjectId(recipeID)})
    
    user_recipe_list = []
    for x in user_recipes:
       user_recipe_list.append(getrecipebyId(x))
    # get user's authored recipes
    authored_recipes = mongo.db.recipes.find(
        {"recipe_author": session["current_user"]})

    if session['current_user']:
        return render_template("myrecipes.html", username=username, user_recipes=user_recipes, user_recipe_list=user_recipe_list, authored_recipes=authored_recipes)




@app.route("/uploadrecipe.html", methods = ['GET', "POST"])
def uploadrecipe():
    username = mongo.db.users.find_one(
        {"email": session["current_user"]})['email']
    if request.method == "POST":
        recipe= {
            "recipe_name": request.form.get('recipe-name'),
            "recipe_description": request.form.get('recipe-description'),
            "seasonal_ingredient": request.form.get('seasonal-ingredient'),
            "recipe_ingredients": request.form.get('ingredients').splitlines(),
            "method": request.form.get('method').splitlines(),
            "recipe_category": request.form.get('dish-category'),
            "cuisine": request.form.get('cuisine'),
            "recipe_author": username,
            "rating":4
        }
        mongo.db.recipes.insert_one(recipe)
        flash ("Recipe added")      
        
        return redirect(url_for('homepage'))

    return render_template('uploadrecipe.html')




@app.route("/register.html", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        
        existing_user = mongo.db.users.find_one(
            {"email": request.form.get("email").lower()})

        if existing_user:
            flash("Email already in use")
            return redirect(url_for("register"))
        if request.form.get('password') != request.form.get('confirm-password'):
            flash("Passwords do not match")
            return redirect(url_for('register'))
        new_user = {
            "username":request.form.get("username").lower(),
            "email": request.form.get("email").lower(),
            "password": generate_password_hash(request.form.get("password")),
            "favourite_recipes":[]
        }
        mongo.db.users.insert_one(new_user)

        flash("Successfully registered!")
        session["current_user"] = request.form.get("email").lower()
        return redirect(url_for("homepage"))
        
     

    return render_template("register.html")

@app.route("/login.html", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        existing_user = mongo.db.users.find_one(
            {"email": request.form.get("email").lower()})
        if existing_user:
            if check_password_hash(
                    existing_user["password"], request.form.get("password")):   
                        session["current_user"] = request.form.get("email").lower() 
                        flash ("Successfully Logged In!")
                        return redirect(url_for('homepage'))
            else:
                flash("Incorrect email or password") 
                return redirect(url_for('login'))   
        else:
            flash("Incorrect Username and/or Password")
            return redirect(url_for("login"))
    return render_template("login.html")        

@app.route("/logout")

def logout():

    flash("You have been logged out")
    session.pop("current_user")
    return redirect(url_for("login"))



if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)
