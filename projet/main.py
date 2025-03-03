import os
import json
import requests
import sys
import time
from inference.direct import direct_inference
from inference.deductive import deductive_inference
from inference.inductive import inductive_inference


# Définir RELATIONS_FILE relatif au dossier contenant main.py
script_dir = os.path.dirname(os.path.abspath(__file__))
RELATIONS_FILE = os.path.join(script_dir, 'data', 'relations.json')
def load_relations():
    """Charge les types de relations depuis un fichier JSON indexé, ou via l'API si le fichier n'existe pas."""
    directory = os.path.dirname(RELATIONS_FILE)
    if not os.path.exists(directory):
        os.makedirs(directory)
    
    if not os.path.exists(RELATIONS_FILE):
        response = requests.get("https://jdm-api.demo.lirmm.fr/v0/relations_types")
        if response.status_code == 200:
            data = response.json()
            # Construire un dictionnaire indexé par id, name et gpname
            relations_index = {}
            for rel in data:
                relations_index[str(rel["id"])] = rel
                relations_index[rel["name"]] = rel
                relations_index[rel["gpname"]] = rel
            with open(RELATIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(relations_index, f, ensure_ascii=False, indent=2)
            print("Relations enregistrées dans", RELATIONS_FILE)
            return relations_index
        else:
            print("Erreur lors de la récupération des types de relations.")
            return {}
    else:
        with open(RELATIONS_FILE, 'r', encoding='utf-8') as f:
            relations_index = json.load(f)
        return relations_index


# Charger les relations au démarrage
relations_data = load_relations()

# Construire un dictionnaire pour la recherche rapide par id, name ou gpname
relations_dict = {rel["id"]: rel for rel in relations_data}
relations_dict.update({rel["name"]: rel for rel in relations_data})
relations_dict.update({rel["gpname"]: rel for rel in relations_data})

def run_inference(node_a, relation, node_b):
    # Vérifier si la relation est valide en utilisant le JSON local
    if relation not in relations_dict:
        print(f"Erreur: Relation '{relation}' non trouvée.")
        return

    direct_results = direct_inference(node_a, relation, node_b)
    
    # Si un résultat direct est trouvé et son poids est négatif, on arrête l'inférence
    if direct_results and direct_results[0][1] < 0:
        print("No.")
        return
    start_time = time.time()
    deductive_results = deductive_inference(node_a, relation, node_b)
    deductive_time = time.time() - start_time

    start_time = time.time()
    inductive_results = inductive_inference(node_a, relation, node_b)
    inductive_time = time.time() - start_time

    print(f"deductive time: {deductive_time:.2f} seconds, inductive time: {inductive_time:.2f} seconds")

    results = deductive_results + inductive_results

    if not results:
        print("Aucun résultat déductif disponible.")
        return

        # Trier les résultats par score décroissant
    results.sort(key=lambda x: x['score'], reverse=True)
    print("=== Affichage complet ===")
    for i, res in enumerate(results, 1):
        formatted = f"{res['node_a']} {res['first_relation']} {res['intermediate_node']} & {res['intermediate_node']} {res['second_relation']} {res['node_b']}"
        print(f"{i} | {formatted} | {res['score']:.2f}")

    print("\n=== Top 10 ===")
    for i, res in enumerate(results[:10], 1):
        formatted = f"{res['node_a']} {res['first_relation']} {res['intermediate_node']} & {res['intermediate_node']} {res['second_relation']} {res['node_b']}"
        print(f"{i} | {formatted} | {res['score']:.2f}")

if __name__ == "__main__":
    print("Enter queries in the format: nodeA relation nodeB")
    print("Type 'exit' to quit.")
    
    while True:
        user_input = input("→ ").strip()
        
        if user_input.lower() == 'exit':
            break
        
        parts = user_input.split()
        if len(parts) != 3:
            print("Invalid format. Use: nodeA relation nodeB")
            continue
        
        nodeA, relation, nodeB = parts
        run_inference(nodeA, relation, nodeB)
