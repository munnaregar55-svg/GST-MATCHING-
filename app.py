from flask import Flask, render_template, request
import pandas as pd

app = Flask(__name__)

# ===================== UTILITIES =====================

def read_file(file):
    try:
        if file.filename.endswith(".csv"):
            return pd.read_csv(file)

        df = pd.read_excel(file, header=None)

        for i in range(10):
            row = df.iloc[i].astype(str).str.lower()
            if any("gst" in str(x) for x in row):
                df.columns = df.iloc[i]
                df = df[i+1:]
                break

        return df.reset_index(drop=True)

    except Exception as e:
        print("Read Error:", e)
        return None


def clean(df):
    df.columns = df.columns.astype(str)
    df.columns = df.columns.str.strip().str.lower()
    return df


def safe_float(x):
    try:
        return float(x)
    except:
        return 0.0


def find_col(df, keywords):
    for col in df.columns:
        for key in keywords:
            if key in col:
                return col
    return None


# ===================== ROUTES =====================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/match", methods=["POST"])
def match():
    try:
        purchase = read_file(request.files["purchase"])
        portal = read_file(request.files["gstr2b"])

        if purchase is None or portal is None:
            return "Error reading file."

        purchase = clean(purchase)
        portal = clean(portal)

        # -------- BOOKS COLUMN MAP --------
        gst_p = find_col(purchase, ["gst"])
        inv_p = find_col(purchase, ["invoice", "bill", "doc"])
        party_p = find_col(purchase, ["party", "supplier", "vendor", "name"])
        amt_p = find_col(purchase, ["amount", "invoice value"])
        igst_p = find_col(purchase, ["igst"])
        cgst_p = find_col(purchase, ["cgst"])
        sgst_p = find_col(purchase, ["sgst"])
        rc_p = find_col(purchase, ["rc", "rcm", "reverse"])

        # -------- PORTAL COLUMN MAP --------
        gst_b = find_col(portal, ["gst"])
        inv_b = find_col(portal, ["invoice"])
        party_b = find_col(portal, ["recipient", "supplier", "party", "name"])
        amt_b = find_col(portal, ["invoice value", "amount"])
        igst_b = find_col(portal, ["igst"])
        cgst_b = find_col(portal, ["cgst"])
        sgst_b = find_col(portal, ["sgst"])

        if not gst_p or not inv_p:
            return "Books file missing GST or Invoice column."

        if not gst_b or not inv_b:
            return "Portal file missing GST or Invoice column."

        purchase["key"] = purchase[gst_p].astype(str) + purchase[inv_p].astype(str)
        portal["key"] = portal[gst_b].astype(str) + portal[inv_b].astype(str)

        mismatch = []
        not_in_2b = []
        not_in_books = []
        rc_data = []

        total_books_itc = 0
        total_portal_itc = 0

        total_rc = 0
        total_rc_igst = 0
        total_rc_cgst = 0
        total_rc_sgst = 0

        # ================= MATCH LOOP =================

        for _, row in purchase.iterrows():

            key = row["key"]

            igst_val = safe_float(row.get(igst_p, 0))
            cgst_val = safe_float(row.get(cgst_p, 0))
            sgst_val = safe_float(row.get(sgst_p, 0))

            books_itc = igst_val + cgst_val + sgst_val
            total_books_itc += books_itc

            # ===== RC CHECK WITH BREAKUP =====
            if rc_p:
                rc_val = str(row.get(rc_p, "")).strip().lower()
                if rc_val in ["yes", "y", "1", "true"]:

                    rc_total = igst_val + cgst_val + sgst_val

                    total_rc += rc_total
                    total_rc_igst += igst_val
                    total_rc_cgst += cgst_val
                    total_rc_sgst += sgst_val

                    rc_data.append({
                        "gst": row.get(gst_p, ""),
                        "party": row.get(party_p, ""),
                        "invoice": row.get(inv_p, ""),
                        "igst": round(igst_val, 2),
                        "cgst": round(cgst_val, 2),
                        "sgst": round(sgst_val, 2),
                        "total": round(rc_total, 2)
                    })

            # ===== MATCH CHECK =====
            if key in portal["key"].values:

                row2 = portal[portal["key"] == key].iloc[0]

                portal_itc = (
                    safe_float(row2.get(igst_b, 0)) +
                    safe_float(row2.get(cgst_b, 0)) +
                    safe_float(row2.get(sgst_b, 0))
                )

                total_portal_itc += portal_itc

                if round(books_itc, 2) != round(portal_itc, 2):
                    mismatch.append({
                        "gst": row.get(gst_p, ""),
                        "party": row.get(party_p, ""),
                        "invoice": row.get(inv_p, ""),
                        "books_itc": round(books_itc, 2),
                        "portal_itc": round(portal_itc, 2),
                        "difference": round(books_itc - portal_itc, 2)
                    })

            else:
                not_in_2b.append({
                    "gst": row.get(gst_p, ""),
                    "party": row.get(party_p, ""),
                    "invoice": row.get(inv_p, ""),
                    "amount": row.get(amt_p, 0)
                })

        # -------- NOT IN BOOKS --------
        for _, row in portal.iterrows():
            if row["key"] not in purchase["key"].values:
                not_in_books.append({
                    "gst": row.get(gst_b, ""),
                    "party": row.get(party_b, ""),
                    "invoice": row.get(inv_b, ""),
                    "amount": row.get(amt_b, 0)
                })

        return render_template(
            "result.html",
            mismatch=mismatch,
            not_in_2b=not_in_2b,
            not_in_books=not_in_books,
            rc_data=rc_data,
            total_books_itc=round(total_books_itc, 2),
            total_portal_itc=round(total_portal_itc, 2),
            diff=round(total_books_itc - total_portal_itc, 2),
            total_rc=round(total_rc, 2),
            total_rc_igst=round(total_rc_igst, 2),
            total_rc_cgst=round(total_rc_cgst, 2),
            total_rc_sgst=round(total_rc_sgst, 2)
        )

    except Exception as e:
        return f"System Error: {str(e)}"


if __name__ == "__main__":
    app.run(debug=True)
