from flask import Flask, render_template, request, send_file
import pandas as pd
import io

app = Flask(__name__)

# =========================
# READ EXCEL FILE
# =========================

def read_file(file):
    return pd.read_excel(file)

# =========================
# HOME PAGE
# =========================

@app.route("/")
def home():
    return render_template("index.html")

# =========================
# GST MATCHING
# =========================

@app.route("/match", methods=["POST"])
def match_files():

    file1 = request.files["file1"]
    file2 = request.files["file2"]

    df1 = read_file(file1)
    df2 = read_file(file2)

    # Remove extra spaces from headings
    df1.columns = df1.columns.str.strip()
    df2.columns = df2.columns.str.strip()

    # Required columns
    required_columns = [
        "GST No",
        "Bill No",
        "Net Amount",
        "Taxable Amount",
        "IGST",
        "SGST",
        "CGST"
    ]

    # Check headings
    for col in required_columns:
        if col not in df1.columns:
            return f"{col} not found in File 1"

        if col not in df2.columns:
            return f"{col} not found in File 2"

    # Optional columns
    if "Party Name" not in df1.columns:
        df1["Party Name"] = ""

    if "Party Name" not in df2.columns:
        df2["Party Name"] = ""

    # Create match key
    df1["match_key"] = (
        df1["GST No"].astype(str).str.strip() +
        "_" +
        df1["Bill No"].astype(str).str.strip()
    )

    df2["match_key"] = (
        df2["GST No"].astype(str).str.strip() +
        "_" +
        df2["Bill No"].astype(str).str.strip()
    )

    # Set index
    df2_indexed = df2.set_index("match_key")

    mismatch_data = []
    matched_data = []

    # =========================
    # MATCHING LOOP
    # =========================

    for _, row1 in df1.iterrows():

        key = row1["match_key"]

        if key in df2_indexed.index:

            row2 = df2_indexed.loc[key]

            status_list = []

            compare_columns = [
                "Net Amount",
                "Taxable Amount",
                "IGST",
                "SGST",
                "CGST"
            ]

            for col in compare_columns:

                val1 = float(row1[col]) if pd.notna(row1[col]) else 0
                val2 = float(row2[col]) if pd.notna(row2[col]) else 0

                diff = abs(val1 - val2)

                # Ignore difference upto ₹1
                if diff > 1:
                    status_list.append(f"{col} Mismatch")

            # If mismatch found
            if status_list:

                mismatch_data.append({
                    "GST No": row1["GST No"],
                    "Party Name": row1["Party Name"],
                    "Bill No": row1["Bill No"],

                    "File1 Net Amount": row1["Net Amount"],
                    "File2 Net Amount": row2["Net Amount"],

                    "File1 Taxable Amount": row1["Taxable Amount"],
                    "File2 Taxable Amount": row2["Taxable Amount"],

                    "File1 IGST": row1["IGST"],
                    "File2 IGST": row2["IGST"],

                    "File1 SGST": row1["SGST"],
                    "File2 SGST": row2["SGST"],

                    "File1 CGST": row1["CGST"],
                    "File2 CGST": row2["CGST"],

                    "Status": ", ".join(status_list)
                })

            else:

                matched_data.append({
                    "GST No": row1["GST No"],
                    "Party Name": row1["Party Name"],
                    "Bill No": row1["Bill No"],
                    "Status": "Exact Match"
                })

        else:

            mismatch_data.append({
                "GST No": row1["GST No"],
                "Party Name": row1["Party Name"],
                "Bill No": row1["Bill No"],
                "Status": "Missing Invoice"
            })

    # =========================
    # CREATE OUTPUT EXCEL
    # =========================

    mismatch_df = pd.DataFrame(mismatch_data)
    matched_df = pd.DataFrame(matched_data)

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        mismatch_df.to_excel(writer, sheet_name="Mismatch Report", index=False)
        matched_df.to_excel(writer, sheet_name="Matched Report", index=False)

    output.seek(0)

    return send_file(
        output,
        download_name="GST_Reconciliation_Report.xlsx",
        as_attachment=True
    )

# =========================
# RUN APP
# =========================

if __name__ == "__main__":
    app.run(debug=True)
