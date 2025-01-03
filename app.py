from flask import Flask, request, jsonify, render_template
import pandas as pd

app = Flask(__name__)

# Base de données (fichier CSV)
DATA_FILE = "data.csv"

# Colonnes obligatoires
REQUIRED_COLUMNS = [
    "group_name", "subgroup_name", "subsubgroup_name", "food_name",
    "kcal", "proteins", "carbs", "carbs_sugar", "fats",
    "fats_saturated", "fibers", "salt", "new_name", "deleted"
]

def load_data():
    """
    Charger les données et ajouter les colonnes manquantes si nécessaire.
    """
    try:
        df = pd.read_csv(DATA_FILE)
        # Vérifie et ajoute les colonnes manquantes si besoin
        for col in REQUIRED_COLUMNS:
            if col not in df.columns:
                if col == "deleted":
                    df[col] = False
                else:
                    df[col] = None
        save_data(df)
        return df
    except FileNotFoundError:
        # Crée un CSV vide si nécessaire
        df = pd.DataFrame(columns=REQUIRED_COLUMNS)
        df["deleted"] = False
        save_data(df)
        return df

def save_data(df):
    """Sauvegarde le DataFrame dans le CSV."""
    df.to_csv(DATA_FILE, index=False)

@app.route("/")
def index():
    """Affiche la page principale."""
    return render_template("index.html")

@app.route("/all", methods=["GET"])
def all_data():
    """Récupérer toutes les données, en mettant les supprimées en bas."""
    df = load_data()
    df = df.sort_values(by="deleted", ascending=True)
    stats = {
        "total": len(df),
        "active": len(df[df["deleted"] == False]),
        "deleted": len(df[df["deleted"] == True])
    }
    return jsonify({"data": df.to_json(orient="records"), "stats": stats}), 200

@app.route("/search", methods=["GET"])
def search():
    """Recherche par mot-clé dans food_name, avec deleted en bas."""
    query = request.args.get("query", "").strip().lower()
    df = load_data()

    if not query:
        df = df.sort_values(by="deleted", ascending=True)
        stats = {
            "total": len(df),
            "active": len(df[df["deleted"] == False]),
            "deleted": len(df[df["deleted"] == True])
        }
        return jsonify({"data": df.to_json(orient="records"), "stats": stats}), 200

    results = df[df["food_name"].str.contains(query, case=False, na=False)]
    results = results.sort_values(by="deleted", ascending=True)

    stats = {
        "results": len(results),
        "total": len(df),
        "active": len(df[df["deleted"] == False]),
        "deleted": len(df[df["deleted"] == True])
    }
    return jsonify({"data": results.to_json(orient="records"), "stats": stats}), 200

@app.route("/update", methods=["POST"])
def update_data():
    """Met à jour un aliment (new_name, restore) en fonction du food_name."""
    data = request.json
    food_name = data.get("food_name")
    new_name = data.get("new_name", None)
    restore = data.get("restore", False)

    if not food_name:
        return jsonify({"error": "food_name est requis."}), 400

    df = load_data()
    indices = df.index[df["food_name"] == food_name].tolist()
    if not indices:
        return jsonify({"error": "Aucune ligne ne correspond à ce food_name."}), 404

    row_id = indices[0]
    if new_name is not None:
        df.loc[row_id, "new_name"] = new_name
    if restore:
        df.loc[row_id, "deleted"] = False

    save_data(df)
    return jsonify({"updated": df.iloc[row_id].to_dict()}), 200

@app.route("/delete", methods=["POST"])
def delete():
    """Marque un aliment comme supprimé (deleted=True)."""
    try:
        data = request.json
        food_name = data.get("food_name")
        if not food_name:
            return jsonify({"error": "food_name est requis pour supprimer."}), 400

        df = load_data()
        indices = df.index[df["food_name"] == food_name].tolist()
        if not indices:
            return jsonify({"error": "Aucune ligne ne correspond à ce food_name."}), 404

        row_id = indices[0]
        df.loc[row_id, "deleted"] = True
        save_data(df)
        return jsonify({"deleted": df.iloc[row_id].to_dict()}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
