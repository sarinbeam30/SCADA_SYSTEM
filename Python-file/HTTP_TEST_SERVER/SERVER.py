import flask
from flask import request, jsonify

app = flask.Flask(__name__)
app.config["DEBUG"] = True


@app.route('/getDATA', methods=['GET','POST'])
def get_the_data():
	if request.method == 'POST':
		data = request.form.to_dict(flat=False)
		print(request.data)
		print(jsonify(data))
		return jsonify(data)
	
	else:
		resp = jsonify(success=True)
		return resp		

app.run(host='0.0.0.0', port=5678)
