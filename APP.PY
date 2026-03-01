from flask import Flask, render_template, request
import pandas as pd

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/match', methods=['POST'])
def match():

    purchase_file = request.files['purchase']
    gstr_file = request.files['gstr2b']

    purchase_df = pd.read_csv(purchase_file)
    gstr_df = pd.read_csv(gstr_file)

    # Matching on GSTIN + Invoice No
    purchase_df['key'] = purchase_df['GSTIN'].astype(str) + purchase_df['Invoice No'].astype(str)
    gstr_df['key'] = gstr_df['GSTIN'].astype(str) + gstr_df['Invoice No'].astype(str)

    matched = purchase_df[purchase_df['key'].isin(gstr_df['key'])]
    not_in_2b = purchase_df[~purchase_df['key'].isin(gstr_df['key'])]
    not_in_books = gstr_df[~gstr_df['key'].isin(purchase_df['key'])]

    return render_template(
        'result.html',
        matched=len(matched),
        not_in_2b=len(not_in_2b),
        not_in_books=len(not_in_books),
        not_in_2b_data=not_in_2b.to_dict(orient='records'),
        not_in_books_data=not_in_books.to_dict(orient='records')
    )

if __name__ == '__main__':
    app.run(debug=True)