from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL

app = Flask(__name__)

# MySQL configurations
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'admin'
app.config['MYSQL_DB'] = 'movingsuggestions'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
app.config['MYSQL_PORT'] = 3306


# Setting the Correct Socket Path
app.config['MYSQL_UNIX_SOCKET'] = '/Applications/MAMP/tmp/mysql/mysql.sock'

# Initialize MySQL
mysql = MySQL(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/success')
def success():
    return render_template('success.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':

        # registration data
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        # create MySQL connection and cursor
        conn = mysql.connection
        cur = conn.cursor()

        # insert user registration data into UserInfo table
        cur.execute("INSERT INTO movingsuggestions.userinfo(user_name, user_password, email_address) VALUES (%s, %s, %s)", (username, password, email))

        # commit the changes to the database
        conn.commit()

        # close cursor and database connection
        cur.close()
        conn.close()
        
        # redirecting to success page after registration
        return redirect(url_for('success'))

    return render_template('register.html')

@app.route('/sign_in', methods=['GET', 'POST'])
def sign_in():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # create MySQL connection and cursor
        conn = mysql.connection
        cur = conn.cursor()

        # fetch all users with the given username from the database
        cur.execute("SELECT * FROM movingsuggestions.userinfo WHERE user_name = %s", (username,))
        users_data = cur.fetchall()

        # close cursor and database connection
        cur.close()
        conn.close()

        # check if there are any users with the given username
        if users_data:
            # iterate through all users with the given username to check passwords
            for user_data in users_data:
                if user_data['user_password'] == password:
                    # Set the user's session to mark them as logged in
                    session['user_id'] = user_data['id']
                    session['username'] = user_data['user_name']
                    
                    # Redirecting to the main page after successful sign-in
                    return redirect(url_for('data'))
            
            return redirect(url_for('sign_in_error'))
        else:

            return redirect(url_for('sign_in_error'))

    return render_template('sign_in.html')

@app.route('/sign_in_error')
def sign_in_error():
    return render_template('sign_in_error.html')

@app.route('/data', methods=['GET', 'POST'])
def data():
    if request.method == 'POST':
        
        income = request.form['income']
        city = int(request.form['city'])
        savings = request.form['savings']
        rent = request.form['rent']
        groceries = request.form['groceries']
        restaurant = request.form['restaurant']
        travel = request.form['travel']
        user_id = session.get('user_id')
        
        try:
            income_float = float(income)
            conn = mysql.connection
            cur = mysql.connection.cursor()
            cur.execute('SELECT cost_of_living_index FROM movingsuggestions.cityindex WHERE city_id=%s',(city,))
            COL = cur.fetchall()[0].get('cost_of_living_index')
            try:
                cur.execute('INSERT INTO movingsuggestions.userinput(user_id, city_id, current_income, cost_of_living_index, savings_priority, rent_priority, groceries_priority, restaurant_priority, travel_priority) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)',(user_id, city, income, COL, savings, rent, groceries, restaurant, travel))
            except:
                cur.execute('UPDATE movingsuggestions.userinput SET city_id=%s, current_income=%s, cost_of_living_index=%s, savings_priority=%s, rent_priority=%s, groceries_priority=%s, restaurant_priority=%s, travel_priority=%s WHERE user_id=%s;',(city, income, COL, savings, rent, groceries, restaurant, travel, user_id))
            conn.commit()
            cur.close()
            conn.close()
        except ValueError:
            return "Invalid income value. Please enter a valid number."

        
        #return f"Data submitted successfully! Your income is: {income_float} You live in {city}"
        return redirect(url_for('suggestions'))

    
    try:
        cur = mysql.connection.cursor()
        cur.execute('SELECT city_id, city_name, country_name FROM movingsuggestions.CityInfo')
        city_names = [[(str(city.get('city_name'))+","+str(city.get('country_name'))), city.get('city_id')] for city in cur.fetchall()]
        cur.close()

        print(city_names)
    except Exception as e:
        city_names = []
        print(f"Error fetching city names: {e}")
    
    return render_template('data.html',city_names=city_names)

@app.route('/suggestions', methods=['GET', 'POST'])
def suggestions():
    user_id = session.get('user_id')
    print(user_id)
    if request.method == "POST":
        return f"Data submitted successfully! Your COL: You live in"
    else:
        conn = mysql.connection
        cur = mysql.connection.cursor()
        cur.execute('SELECT savings_priority, rent_priority, groceries_priority, restaurant_priority, travel_priority, city_id FROM movingsuggestions.userinput WHERE user_id = %s', (user_id,))
        priority = cur.fetchall()[0]
        priority['groceries_index'] = priority.pop('groceries_priority')
        priority['rent_index'] = priority.pop('rent_priority')
        priority['restaurant_price_index'] = priority.pop('restaurant_priority')
        priority['local_purchasing_power_index'] = priority.pop('travel_priority')
        priority['col_plus_rent_index'] = priority.pop('savings_priority')
        priority = sorted(priority.items(), key=lambda x:x[1])
        cur.execute('SELECT city_name, country_name FROM movingsuggestions.CityInfo WHERE city_id = %s', (priority[0][1],))
        city = cur.fetchone()
        city_name = str(city.get('city_name'))+","+str(city.get('country_name'))
        cur.execute('SELECT cost_of_living_index, current_income FROM movingsuggestions.userinput WHERE user_id = %s', (user_id,))
        user_info = cur.fetchone()
        COL = user_info.get('cost_of_living_index')
        current_income = user_info.get('current_income')
        sql = 'SELECT A.city_id, city_name, country_name, cost_of_living_index, rent_index, col_plus_rent_index, groceries_index, restaurant_price_index, local_purchasing_power_index FROM movingsuggestions.cityindex AS A JOIN movingsuggestions.cityinfo AS B ON A.city_id = B.city_id WHERE A.cost_of_living_index < {} ORDER BY {} DESC, {} DESC, {} DESC, {} DESC, {} DESC LIMIT 20'.format(COL, priority[0][0], priority[1][0], priority[2][0], priority[3][0], priority[4][0])
        print(sql)
        cur.execute(sql)
        suggestions = cur.fetchall()
        cur.execute('TRUNCATE TABLE suggestions')
        for suggestion in suggestions:
            new_col = suggestion['cost_of_living_index']
            diff_COL = ((COL-new_col)/COL)+1
            print(diff_COL)
            suggestion['adjusted_income'] = round((diff_COL*current_income), 2)
        priority = dict(priority)
        priority['Groceries'] = priority.pop('groceries_index')
        priority['Rent'] = priority.pop('rent_index')
        priority['Eating Out'] = priority.pop('restaurant_price_index')
        priority['Travel'] = priority.pop('local_purchasing_power_index')
        priority['Savings'] = priority.pop('col_plus_rent_index')
        priority.pop('city_id')
        print(priority)
        priority = sorted(priority.items(), key=lambda x:x[1])
        cur.close()
        return render_template("suggestions.html", suggestions=suggestions, city_name=city_name, priorities = priority)
    
@app.route('/update_priorities', methods=['GET', 'POST'])
def update_priorities():
    user_id = session.get('user_id')
    
    if request.method == 'POST':
        
        updated_savings = request.form.get('savings')
        updated_rent = request.form.get('rent')
        updated_groceries = request.form.get('groceries')
        updated_restaurant = request.form.get('restaurant')
        updated_travel = request.form.get('travel')
        
        conn = mysql.connection
        cur = conn.cursor()

        # update user's priority
        cur.execute('UPDATE movingsuggestions.userinput SET savings_priority=%s, rent_priority=%s, groceries_priority=%s, restaurant_priority=%s, travel_priority=%s WHERE user_id=%s', (updated_savings, updated_rent, updated_groceries, updated_restaurant, updated_travel, user_id))
        conn.commit()
        cur.close()
        conn.close()
        
        return redirect(url_for('suggestions'))
    
    return render_template('update_priorities.html')


if __name__ == '__main__':
    app.debug = True
    app.secret_key = 'costofliving'

    app.run()

