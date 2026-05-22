from flask import Flask, render_template, request, send_file
import pandas as pd
import os

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
RESULT_FOLDER = "results"

# Folder create safely
if not os.path.isdir(UPLOAD_FOLDER):
    os.mkdir(UPLOAD_FOLDER)

if not os.path.isdir(RESULT_FOLDER):
    os.mkdir(RESULT_FOLDER)


# Column clean function
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

        # Save files
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
            "sgstamount": "sgst",
            "netamount": "net"
        }, inplace=True)

        gstr2b_df.rename(columns={
            "partyname": "party",
            "taxableamount": "taxable",
            "igstamount": "igst",
            "cgstamount": "cgst",
            "sgstamount": "sgst",
            "netamount": "net"
        }, inplace=True)

        # Match columns
        cols = [
            "party",
            "taxable",
            "igst",
            "cgst",
            "sgst"
        ]

        purchase_df = purchase_df[cols]
        gstr2b_df = gstr2b_df[cols]

        # Merge
        merged = purchase_df.merge(
            gstr2b_df,
            on=cols,
            how="outer",
            indicator=True
        )

        # Status
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
