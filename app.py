from flask import Flask, render_template, request, send_file
import pandas as pd
import os

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
RESULT_FOLDER = "results"

# Create folders safely
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)


# Clean column names
def clean_columns(df):

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "", regex=False)
    )

    return df


@app.route("/", methods=["GET", "POST"])
def index():

    if request.method == "POST":

        purchase_file = request.files["purchase"]
        gstr2b_file = request.files["gstr2b"]

        # Save uploaded files
        purchase_path = os.path.join(
            UPLOAD_FOLDER,
            "purchase.csv"
        )

        gstr2b_path = os.path.join(
            UPLOAD_FOLDER,
            "gstr2b.csv"
        )

        purchase_file.save(purchase_path)
        gstr2b_file.save(gstr2b_path)

        # Read CSV
        purchase_df = pd.read_csv(purchase_path)
        gstr2b_df = pd.read_csv(gstr2b_path)

        # Clean columns
        purchase_df = clean_columns(purchase_df)
        gstr2b_df = clean_columns(gstr2b_df)

        # Rename columns
        purchase_df.rename(columns={
            "partyname": "party",
            "taxableamount": "taxable",
            "igstamount": "igst",
            "cgstamount": "cgst",
            "sgstamount": "sgst"
        }, inplace=True)

        gstr2b_df.rename(columns={
            "partyname": "party",
            "taxableamount": "taxable",
            "igstamount": "igst",
            "cgstamount": "cgst",
            "sgstamount": "sgst"
        }, inplace=True)

        # Required columns
        cols = [
            "party",
            "taxable",
            "igst",
            "cgst",
            "sgst"
        ]

        purchase_df = purchase_df[cols]
        gstr2b_df = gstr2b_df[cols]

        # Match data
        merged = purchase_df.merge(
            gstr2b_df,
            on=cols,
            how="outer",
            indicator=True
        )

        # Status column
        merged["status"] = merged["_merge"].map({
            "both": "Matched",
            "left_only": "Only In Purchase",
            "right_only": "Only In 2B"
        })

        merged.drop(columns=["_merge"], inplace=True)

        # Save result
        result_path = os.path.join(
            RESULT_FOLDER,
            "GST_Matching_Result.xlsx"
        )

        merged.to_excel(
            result_path,
            index=False
        )

        # HTML table
        table = merged.to_html(
            index=False,
            classes="table"
        )

        return render_template(
            "result.html",
            table=table
        )

    return render_template("index.html")


@app.route("/download")
def download():

    path = os.path.join(
        RESULT_FOLDER,
        "GST_Matching_Result.xlsx"
    )

    return send_file(
        path,
        as_attachment=True
    )


if __name__ == "__main__":
    app.run(debug=True)
