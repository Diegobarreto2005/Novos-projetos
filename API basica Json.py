
from flask import Flask, jsonify  

app = Flask(__name__)  

@app.route('/') 
def hello():
   
    data = {"Mensage": "Bem vindo"}  
    
    return jsonify(data)  


if __name__ == '__main__':
    app.run(debug=True)  